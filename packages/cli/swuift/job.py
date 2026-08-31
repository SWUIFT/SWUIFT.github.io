"""Job schema and JSON loader for SWUIFT batch execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .timezones import validate_timezone


def parse_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {value!r}")


def validate_output_dir(output_dir: str, job_name: str) -> str:
    """Ensure output directory is provided and outside project root."""
    if not output_dir or not str(output_dir).strip():
        raise ValueError(f"Job {job_name!r}: output_dir is required and cannot be empty.")
    resolved = Path(output_dir).expanduser().resolve()
    project_root = Path(__file__).resolve().parents[1]
    if resolved == project_root or resolved.is_relative_to(project_root):
        raise ValueError(
            f"Job {job_name!r}: output_dir must be outside project root "
            f"({project_root}), got {resolved}."
        )
    return str(resolved)


@dataclass(frozen=True)
class JobSpec:
    """Fully explicit run specification for a single SWUIFT job."""

    name: str

    # Input files
    fire_prog: str
    domains: str
    landcover: str
    homes: str
    lat: str
    lon: str
    harden_rad_map: str
    harden_spo_map: str
    water: str | None
    wind: str

    # Hyperparameters (all required)
    grid_size: float
    t_start: datetime
    t_end: datetime
    timezone: str
    harden_rad: float
    harden_spo: float
    rad_ig_thresh: float
    rad_decay: float
    brand_wind_coef: float
    brand_wind_sd: float
    brand_wind_sd_lat: float
    seed_harden: int | None
    seed_spread: int | None
    lazy_wind: bool

    # Run/output controls
    output_dir: str
    frame_dpi: int
    dump_every: int
    dump_csv: bool
    out_frames: bool = True
    out_video: bool = True
    out_gif: bool = True
    out_ig_plots: bool = True
    out_fire_csv: bool = True
    out_buildings_csv: bool = True
    out_rad_steps: bool = False
    out_spo_steps: bool = False
    scenario_id: str | None = None
    scenario_manifest: str | None = None
    data_root: str | None = None
    hardening_profile: str = "matlab_active"
    rng_profile: str = "seeded"
    emit_metrics: bool = True
    emit_frame_state: bool = True
    checkpoint_every: int = 0
    forensic_full: bool = False
    t_step_min: float = 5.0
    aes: float = 60.0
    ee: float = 0.7
    er: float = 0.7
    sconst: float = 5.67e-8
    fb_mass: float = 0.5
    fb_dist_mu: float = 0.01
    fb_dist_sd: float = 0.5
    veg_included: bool = True
    tmpr: tuple[float, ...] | None = None


_REQUIRED_JSON_FIELDS = [
    "name",
    "fire_prog",
    "domains",
    "landcover",
    "homes",
    "lat",
    "lon",
    "harden_rad_map",
    "harden_spo_map",
    "wind",
    "grid_size",
    "t_start",
    "t_end",
    "timezone",
    "harden_rad",
    "harden_spo",
    "rad_ig_thresh",
    "rad_decay",
    "brand_wind_coef",
    "brand_wind_sd",
    "brand_wind_sd_lat",
    "seed_harden",
    "seed_spread",
    "lazy_wind",
    "output_dir",
    "frame_dpi",
    "dump_every",
    "dump_csv",
]


def _as_bool(value: Any, field: str, job_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Job {job_name!r}: field {field!r} must be boolean.")


def _build_job(job_dict: dict[str, Any], idx: int) -> JobSpec:
    job_name = str(job_dict.get("name", f"job_{idx}"))
    missing = [f for f in _REQUIRED_JSON_FIELDS if f not in job_dict]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Job {job_name!r} missing required fields: {joined}")

    return JobSpec(
        name=str(job_dict["name"]),
        fire_prog=str(job_dict["fire_prog"]),
        domains=str(job_dict["domains"]),
        landcover=str(job_dict["landcover"]),
        homes=str(job_dict["homes"]),
        lat=str(job_dict["lat"]),
        lon=str(job_dict["lon"]),
        harden_rad_map=str(job_dict["harden_rad_map"]),
        harden_spo_map=str(job_dict["harden_spo_map"]),
        water=(str(job_dict["water"]).strip() or None) if job_dict.get("water") else None,
        wind=str(job_dict["wind"]),
        grid_size=float(job_dict["grid_size"]),
        t_start=parse_datetime(str(job_dict["t_start"])),
        t_end=parse_datetime(str(job_dict["t_end"])),
        timezone=validate_timezone(str(job_dict["timezone"])),
        harden_rad=float(job_dict["harden_rad"]),
        harden_spo=float(job_dict["harden_spo"]),
        rad_ig_thresh=float(job_dict["rad_ig_thresh"]),
        rad_decay=float(job_dict["rad_decay"]),
        brand_wind_coef=float(job_dict["brand_wind_coef"]),
        brand_wind_sd=float(job_dict["brand_wind_sd"]),
        brand_wind_sd_lat=float(job_dict["brand_wind_sd_lat"]),
        seed_harden=None if job_dict["seed_harden"] is None else int(job_dict["seed_harden"]),
        seed_spread=None if job_dict["seed_spread"] is None else int(job_dict["seed_spread"]),
        lazy_wind=_as_bool(job_dict["lazy_wind"], "lazy_wind", job_name),
        output_dir=validate_output_dir(str(job_dict["output_dir"]), job_name),
        frame_dpi=int(job_dict["frame_dpi"]),
        dump_every=int(job_dict["dump_every"]),
        dump_csv=_as_bool(job_dict["dump_csv"], "dump_csv", job_name),
        out_frames=_as_bool(job_dict.get("out_frames", True), "out_frames", job_name),
        out_video=_as_bool(job_dict.get("out_video", True), "out_video", job_name),
        out_gif=_as_bool(job_dict.get("out_gif", True), "out_gif", job_name),
        out_ig_plots=_as_bool(job_dict.get("out_ig_plots", True), "out_ig_plots", job_name),
        out_fire_csv=_as_bool(job_dict.get("out_fire_csv", True), "out_fire_csv", job_name),
        out_buildings_csv=_as_bool(
            job_dict.get("out_buildings_csv", True), "out_buildings_csv", job_name
        ),
        out_rad_steps=_as_bool(job_dict.get("out_rad_steps", False), "out_rad_steps", job_name),
        out_spo_steps=_as_bool(job_dict.get("out_spo_steps", False), "out_spo_steps", job_name),
        scenario_id=job_dict.get("scenario_id"),
        scenario_manifest=job_dict.get("scenario_manifest"),
        data_root=job_dict.get("data_root"),
        hardening_profile=str(job_dict.get("hardening_profile", "matlab_active")),
        rng_profile=str(job_dict.get("rng_profile", "seeded")),
        emit_metrics=_as_bool(job_dict.get("emit_metrics", True), "emit_metrics", job_name),
        emit_frame_state=_as_bool(
            job_dict.get("emit_frame_state", True), "emit_frame_state", job_name
        ),
        checkpoint_every=int(job_dict.get("checkpoint_every", 0)),
        forensic_full=_as_bool(job_dict.get("forensic_full", False), "forensic_full", job_name),
        t_step_min=float(job_dict.get("t_step_min", 5.0)),
        aes=float(job_dict.get("aes", 60.0)),
        ee=float(job_dict.get("ee", 0.7)),
        er=float(job_dict.get("er", 0.7)),
        sconst=float(job_dict.get("sconst", 5.67e-8)),
        fb_mass=float(job_dict.get("fb_mass", 0.5)),
        fb_dist_mu=float(job_dict.get("fb_dist_mu", 0.01)),
        fb_dist_sd=float(job_dict.get("fb_dist_sd", 0.5)),
        veg_included=_as_bool(job_dict.get("veg_included", True), "veg_included", job_name),
        tmpr=(
            tuple(float(value) for value in job_dict["tmpr"])
            if job_dict.get("tmpr") is not None else None
        ),
    )


def load_jobs(path: str) -> list[JobSpec]:
    """Load and validate a batch JSON file with a top-level ``jobs`` array."""
    batch_path = Path(path)
    with batch_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or "jobs" not in payload:
        raise ValueError("Batch JSON must contain top-level object with a 'jobs' array.")
    jobs_raw = payload["jobs"]
    if not isinstance(jobs_raw, list) or not jobs_raw:
        raise ValueError("'jobs' must be a non-empty array.")
    jobs: list[JobSpec] = []
    for idx, entry in enumerate(jobs_raw, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"jobs[{idx - 1}] must be an object.")
        jobs.append(_build_job(entry, idx))
    return jobs

