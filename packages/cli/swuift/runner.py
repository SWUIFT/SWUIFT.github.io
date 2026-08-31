"""Single-job execution runner and run metadata writer."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any

import numpy as np

from .config import SWUIFTConfig, build_config
from .data_loader import SWUIFTData, load_all_extracted, load_scenario_data
from .job import JobSpec, validate_output_dir
from .license import LicenseInfo
from .logger import tee_run_output
from .scenario import load_scenario_manifest
from .simulation import run_simulation
from .timezones import local_to_utc, localized_timestamp, utc_isoformat


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_job_name(name: str) -> str:
    keep = []
    for ch in name.strip():
        keep.append(ch if ch.isalnum() or ch in ("-", "_") else "_")
    return "".join(keep) or "job"


def _prepare_run_dir(base_output_dir: str, job_name: str) -> str:
    run_id = f"{_safe_job_name(job_name)}_{_timestamp()}"
    run_dir = os.path.join(base_output_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def _jsonable(value: Any) -> Any:
    """Recursively convert values to JSON-serializable representations."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _write_run_params(
    *,
    output_dir: str,
    job: JobSpec,
    cfg: SWUIFTConfig,
    command_line: str,
    start_ts: datetime,
    end_ts: datetime,
    elapsed_s: float,
    data: SWUIFTData,
    license_info: LicenseInfo,
    simulation_metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "job_name": job.name,
        "command_line": command_line,
        "started_at": start_ts.isoformat(),
        "ended_at": end_ts.isoformat(),
        "elapsed_seconds": elapsed_s,
        "license": {
            "accepted": True,
            "path": str(license_info.path),
            "sha256": license_info.sha256,
        },
        "input_files": {
            "fire_prog": job.fire_prog,
            "domains": job.domains,
            "landcover": job.landcover,
            "homes": job.homes,
            "lat": job.lat,
            "lon": job.lon,
            "harden_rad_map": job.harden_rad_map,
            "harden_spo_map": job.harden_spo_map,
            "water": job.water,
            "wind": job.wind,
        },
        "config": {
            "grid_size": cfg.grid_size,
            "t_start": cfg.t_start.isoformat(sep=" "),
            "t_end": cfg.t_end.isoformat(sep=" "),
            "timezone": job.timezone,
            "t_start_utc": utc_isoformat(cfg.t_start),
            "t_end_utc": utc_isoformat(cfg.t_end),
            "t_start_local": localized_timestamp(cfg.t_start, job.timezone)["local"],
            "t_end_local": localized_timestamp(cfg.t_end, job.timezone)["local"],
            "max_steps": cfg.maxstep,
            "harden_rad": cfg.harden_rad,
            "harden_spo": cfg.harden_spo,
            "rad_ig_thresh": cfg.rad_ig_thresh,
            "rad_decay": cfg.rad_decay,
            "brand_wind_coef": cfg.brand_wind_coef,
            "brand_wind_sd": cfg.brand_wind_sd,
            "brand_wind_sd_lat": cfg.brand_wind_sd_lat,
            "seed_harden": cfg.seed_harden,
            "seed_spread": cfg.seed_spread,
            "hardening_profile": cfg.hardening_profile,
            "rng_profile": cfg.rng_profile,
            "t_step_min": cfg.t_step_min,
            "aes": cfg.aes,
            "ee": cfg.ee,
            "er": cfg.er,
            "sconst": cfg.sconst,
            "fb_mass": cfg.fb_mass,
            "fb_dist_mu": cfg.fb_dist_mu,
            "fb_dist_sd": cfg.fb_dist_sd,
            "veg_included": cfg.veg_included,
            "tmpr": cfg.tmpr.tolist(),
            "fstep": cfg.fstep,
            "lstep": cfg.lstep,
        },
        "outputs": {
            "frame_dpi": job.frame_dpi,
            "dump_every": job.dump_every,
            "dump_csv": job.dump_csv,
            "out_frames": job.out_frames,
            "out_video": job.out_video,
            "out_gif": job.out_gif,
            "out_ig_plots": job.out_ig_plots,
            "out_fire_csv": job.out_fire_csv,
            "out_buildings_csv": job.out_buildings_csv,
            "out_rad_steps": job.out_rad_steps,
            "out_spo_steps": job.out_spo_steps,
        },
        "grid_shape": {"rows": data.rows, "cols": data.cols},
        "job_spec": _jsonable(asdict(job)),
        "simulation_metadata": _jsonable(simulation_metadata or {}),
    }
    out_path = os.path.join(output_dir, "run_params.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def run_single(
    job: JobSpec,
    *,
    command_line: str,
    license_info: LicenseInfo,
) -> str:
    """Run one job and return the run directory path."""
    if (job.out_video or job.out_gif) and not job.out_frames:
        raise ValueError(
            f"Job {job.name!r}: out_frames must be true when out_video/out_gif is enabled."
        )

    safe_output_dir = validate_output_dir(job.output_dir, job.name)
    run_dir = _prepare_run_dir(safe_output_dir, job.name)
    with tee_run_output(run_dir, command_line):
        print(f"Starting job: {job.name}")
        print(f"Run directory: {run_dir}")
        start_dt = datetime.now().astimezone()
        t0 = time.time()

        manifest = None
        if job.scenario_manifest:
            manifest = load_scenario_manifest(job.scenario_manifest)
            data = load_scenario_data(
                manifest,
                job.data_root or "",
                preload_wind=not job.lazy_wind,
            )
        else:
            data = load_all_extracted(
                wildland_fire_matrix_file=job.fire_prog,
                domain_matrix_file=job.domains,
                binary_cover_file=job.landcover,
                homes_matrix_file=job.homes,
                latitude_file=job.lat,
                longitude_file=job.lon,
                radiation_matrix_file=job.harden_rad_map,
                spotting_matrix_file=job.harden_spo_map,
                water_matrix_file=job.water,
                wind_file=job.wind,
                preload_wind=not job.lazy_wind,
            )
        t_start_utc = local_to_utc(job.t_start, job.timezone)
        t_end_utc = local_to_utc(job.t_end, job.timezone)
        cfg = build_config(
            grid_size=job.grid_size,
            t_start=t_start_utc,
            t_end=t_end_utc,
            harden_rad=job.harden_rad,
            harden_spo=job.harden_spo,
            rad_ig_thresh=job.rad_ig_thresh,
            rad_decay=job.rad_decay,
            brand_wind_coef=job.brand_wind_coef,
            brand_wind_sd=job.brand_wind_sd,
            brand_wind_sd_lat=job.brand_wind_sd_lat,
            seed_harden=job.seed_harden,
            seed_spread=job.seed_spread,
            hardening_profile=job.hardening_profile,
            rng_profile=job.rng_profile,
            scenario_id=job.scenario_id,
            t_step_min=job.t_step_min,
            aes=job.aes,
            ee=job.ee,
            er=job.er,
            sconst=job.sconst,
            fb_mass=job.fb_mass,
            fb_dist_mu=job.fb_dist_mu,
            fb_dist_sd=job.fb_dist_sd,
            veg_included=job.veg_included,
            tmpr=None if job.tmpr is None else np.asarray(job.tmpr, dtype=np.float64),
        )
        simulation_metadata: dict[str, Any] = {}
        try:
            simulation_metadata = run_simulation(
                cfg=cfg,
                data=data,
                output_dir=run_dir,
                frame_dpi=job.frame_dpi,
                dump_every=job.dump_every,
                dump_csv=job.dump_csv,
                out_frames=job.out_frames,
                out_video=job.out_video,
                out_gif=job.out_gif,
                out_ig_plots=job.out_ig_plots,
                out_fire_csv=job.out_fire_csv,
                out_buildings_csv=job.out_buildings_csv,
                out_rad_steps=job.out_rad_steps,
                out_spo_steps=job.out_spo_steps,
                emit_metrics=job.emit_metrics,
                emit_frame_state=job.emit_frame_state,
                checkpoint_every=job.checkpoint_every,
                forensic_full=job.forensic_full,
                display_timezone=job.timezone,
            )
        finally:
            data.close()

        elapsed_s = time.time() - t0
        end_dt = datetime.now().astimezone()
        _write_run_params(
            output_dir=run_dir,
            job=job,
            cfg=cfg,
            command_line=command_line,
            start_ts=start_dt,
            end_ts=end_dt,
            elapsed_s=elapsed_s,
            data=data,
            license_info=license_info,
            simulation_metadata=simulation_metadata,
        )
        print(f"Completed job: {job.name} in {elapsed_s:.2f}s")
    return run_dir
