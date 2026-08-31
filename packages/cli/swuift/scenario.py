"""Packaged scenario manifests for Python SWUIFT runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from .timezones import validate_timezone

SCENARIO_IDS = ("marshall",)


def default_manifest_path(scenario_id: str) -> Path:
    scenario = scenario_id.lower()
    if scenario not in SCENARIO_IDS:
        raise ValueError(f"Unknown scenario {scenario_id!r}; expected one of {SCENARIO_IDS}.")
    return Path(str(files("swuift").joinpath("resources", "scenarios", f"{scenario}.json")))


@dataclass(frozen=True)
class ScenarioManifest:
    path: Path
    payload: dict[str, Any]

    @property
    def scenario_id(self) -> str:
        return str(self.payload["scenario_id"])

    @property
    def display_name(self) -> str:
        return str(self.payload["display_name"])

    @property
    def config(self) -> dict[str, Any]:
        return dict(self.payload["config"])

    @property
    def inputs(self) -> dict[str, Any]:
        return dict(self.payload["inputs"])

    def resolve_data_root(self, root: str | Path) -> Path:
        base = Path(root).expanduser().resolve()
        nested = base / self.scenario_id
        if nested.is_dir():
            return nested
        # An explicit per-fire override may have any directory name, but it
        # must already contain this scenario's complete required file set.
        if all((base / name).is_file() for name in self.required_input_files()):
            return base
        # Keep failures scoped to the requested fire instead of falling back to
        # a base directory that may contain another scenario's data.
        return nested

    def required_input_files(self) -> list[str]:
        inputs = self.inputs
        files = {
            inputs["defaults"]["file"],
            inputs["bundle"]["file"],
            inputs["domains"]["file"],
            inputs["known_ignition"]["file"],
            inputs["wind"]["speed_file"],
            inputs["wind"]["direction_file"],
        }
        hardening = inputs["hardening"]
        if hardening.get("file"):
            files.add(hardening["file"])
        if inputs["wind"].get("combined_file"):
            files.add(inputs["wind"]["combined_file"])
        return sorted(str(name) for name in files)

    def validate_data_files(self, root: str | Path) -> Path:
        data_root = self.resolve_data_root(root)
        missing = [data_root / name for name in self.required_input_files() if not (data_root / name).is_file()]
        if missing:
            rendered = "\n".join(f"  {path}" for path in missing)
            raise FileNotFoundError(
                f"Missing {self.display_name} scenario inputs under {data_root}:\n{rendered}"
            )
        return data_root


def _validate_payload(payload: dict[str, Any], path: Path) -> None:
    required = {"schema_version", "scenario_id", "display_name", "inputs", "config"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"{path}: missing manifest keys: {', '.join(missing)}")
    scenario = str(payload["scenario_id"]).lower()
    if scenario not in SCENARIO_IDS:
        raise ValueError(f"{path}: unsupported scenario_id {scenario!r}")
    cfg = payload["config"]
    for field in (
        "grid_size", "t_start", "t_end", "timezone", "expected_steps", "hardening_profile",
        "rng_profile", "rad_ig_thresh", "rad_decay",
    ):
        if field not in cfg:
            raise ValueError(f"{path}: config.{field} is required")
    if cfg["hardening_profile"] not in {"matlab_active", "matlab_inert"}:
        raise ValueError(f"{path}: invalid hardening_profile")
    if cfg["rng_profile"] not in {"seeded", "matlab_unseeded"}:
        raise ValueError(f"{path}: invalid rng_profile")
    if cfg["rng_profile"] == "seeded" and cfg.get("seed_spread") is None:
        raise ValueError(f"{path}: seeded RNG profile requires seed_spread")
    validate_timezone(str(cfg["timezone"]))


def load_scenario_manifest(
    scenario_or_path: str | Path,
) -> ScenarioManifest:
    candidate = Path(scenario_or_path)
    path = candidate if candidate.suffix.lower() == ".json" or candidate.exists() else default_manifest_path(str(scenario_or_path))
    path = path.expanduser().resolve()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: manifest root must be an object")
    _validate_payload(payload, path)
    return ScenarioManifest(path=path, payload=payload)


def build_scenario_job(
    manifest: ScenarioManifest,
    *,
    data_root: str | Path,
    output_dir: str,
    lazy_wind: bool = True,
    frame_dpi: int = 150,
    dump_every: int = 0,
    dump_csv: bool = False,
    out_frames: bool = False,
    out_video: bool = False,
    out_gif: bool = False,
    out_ig_plots: bool = True,
    checkpoint_every: int = 20,
    forensic_full: bool = False,
):
    """Translate a scenario manifest into the existing explicit JobSpec."""
    import numpy as np

    from .data_loader import load_default_values
    from .job import JobSpec, parse_datetime, validate_output_dir

    root = manifest.validate_data_files(data_root)
    inputs = manifest.inputs
    cfg = manifest.config
    defaults = load_default_values(str(root))

    def scalar(name: str, fallback: float) -> float:
        if name not in defaults:
            return fallback
        return float(np.asarray(defaults[name]).squeeze())

    hardening = inputs["hardening"]
    bundle = root / inputs["bundle"]["file"]
    hardening_path = root / hardening.get("file", inputs["bundle"]["file"])
    return JobSpec(
        name=f"{manifest.scenario_id}_python",
        fire_prog=str(root / inputs["known_ignition"]["file"]),
        domains=str(root / inputs["domains"]["file"]),
        landcover=str(bundle),
        homes=str(bundle),
        lat=str(bundle),
        lon=str(bundle),
        harden_rad_map=str(hardening_path),
        harden_spo_map=str(hardening_path),
        water=str(bundle) if inputs["variables"].get("water") else None,
        wind=str(root / inputs["wind"]["speed_file"]),
        grid_size=float(cfg["grid_size"]),
        t_start=parse_datetime(cfg["t_start"]),
        t_end=parse_datetime(cfg["t_end"]),
        timezone=validate_timezone(str(cfg["timezone"])),
        harden_rad=float(cfg["harden_rad"]),
        harden_spo=float(cfg["harden_spo"]),
        rad_ig_thresh=scalar("rad_energy_ig", float(cfg["rad_ig_thresh"])),
        rad_decay=scalar("rad_rf", float(cfg["rad_decay"])),
        brand_wind_coef=scalar("fb_wind_coef", float(cfg["brand_wind_coef"])),
        brand_wind_sd=scalar("fb_wind_sd", float(cfg["brand_wind_sd"])),
        brand_wind_sd_lat=scalar(
            "fb_wind_sd_transverse", float(cfg["brand_wind_sd_lat"])
        ),
        seed_harden=cfg.get("seed_harden"),
        seed_spread=cfg.get("seed_spread"),
        lazy_wind=lazy_wind,
        output_dir=validate_output_dir(output_dir, manifest.scenario_id),
        frame_dpi=frame_dpi,
        dump_every=dump_every,
        dump_csv=dump_csv,
        out_frames=out_frames,
        out_video=out_video,
        out_gif=out_gif,
        out_ig_plots=out_ig_plots,
        scenario_id=manifest.scenario_id,
        scenario_manifest=str(manifest.path),
        data_root=str(root),
        hardening_profile=str(cfg["hardening_profile"]),
        rng_profile=str(cfg["rng_profile"]),
        checkpoint_every=checkpoint_every,
        forensic_full=forensic_full,
        t_step_min=scalar("t_step_min", 5.0),
        aes=scalar("aes", 60.0),
        ee=scalar("ee", 0.7),
        er=scalar("er", 0.7),
        sconst=scalar("sconst", 5.67e-8),
        fb_mass=scalar("fb_mass", 0.5),
        fb_dist_mu=scalar("fb_dist_mu", 0.01),
        fb_dist_sd=scalar("fb_dist_sd", 0.5),
        veg_included=bool(scalar("veg_included", 1.0)),
        tmpr=(
            tuple(float(value) for value in np.asarray(defaults["tmpr"]).ravel())
            if "tmpr" in defaults else None
        ),
    )
