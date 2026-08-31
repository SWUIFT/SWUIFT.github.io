from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

os.environ.setdefault("SWUIFT_APP_KERNEL_BACKEND", "python")

from swuift.cli import _build_parser, _missing_single_fields
from swuift.config import build_config
from swuift.data_loader import load_all_extracted
from swuift.job import load_jobs
from swuift.simulation import run_simulation


def _write_csv(path: Path, values: np.ndarray) -> str:
    np.savetxt(path, values, delimiter=",")
    return str(path)


def _load_without_water(tmp_path: Path):
    shape = (2, 2)
    zeros = np.zeros(shape)
    paths = {
        "fire": _write_csv(tmp_path / "fire.csv", zeros),
        "domains": _write_csv(tmp_path / "domains.csv", zeros),
        "cover": _write_csv(tmp_path / "cover.csv", zeros),
        "homes": _write_csv(tmp_path / "homes.csv", zeros),
        "lat": _write_csv(tmp_path / "lat.csv", np.array([40.0, 40.1])),
        "lon": _write_csv(tmp_path / "lon.csv", np.array([-105.1, -105.0])),
        "rad": _write_csv(tmp_path / "rad.csv", zeros),
        "spo": _write_csv(tmp_path / "spo.csv", zeros),
    }
    _write_csv(tmp_path / "wind_s.csv", zeros)
    _write_csv(tmp_path / "wind_d.csv", zeros)

    return load_all_extracted(
        wildland_fire_matrix_file=paths["fire"],
        domain_matrix_file=paths["domains"],
        binary_cover_file=paths["cover"],
        homes_matrix_file=paths["homes"],
        latitude_file=paths["lat"],
        longitude_file=paths["lon"],
        radiation_matrix_file=paths["rad"],
        spotting_matrix_file=paths["spo"],
        wind_file=str(tmp_path / "wind.csv"),
    )


def test_single_run_does_not_require_water_flag() -> None:
    args = _build_parser().parse_args([])
    assert "water" not in _missing_single_fields(args)


def test_batch_job_defaults_water_to_none(tmp_path: Path) -> None:
    payload = {
        "jobs": [
            {
                "name": "no_water",
                "fire_prog": "fire.csv",
                "domains": "domains.csv",
                "landcover": "cover.csv",
                "homes": "homes.csv",
                "lat": "lat.csv",
                "lon": "lon.csv",
                "harden_rad_map": "rad.csv",
                "harden_spo_map": "spo.csv",
                "wind": "wind.csv",
                "grid_size": 10,
                "t_start": "2026-01-01 00:00",
                "t_end": "2026-01-01 00:00",
                "timezone": "UTC",
                "harden_rad": 0,
                "harden_spo": 0,
                "rad_ig_thresh": 14000,
                "rad_decay": 1,
                "brand_wind_coef": 30,
                "brand_wind_sd": 0.3,
                "brand_wind_sd_lat": 4.85,
                "seed_harden": 1,
                "seed_spread": 1,
                "lazy_wind": False,
                "output_dir": str(tmp_path / "outputs"),
                "frame_dpi": 72,
                "dump_every": 0,
                "dump_csv": False,
            }
        ]
    }
    batch_path = tmp_path / "jobs.json"
    batch_path.write_text(json.dumps(payload), encoding="utf-8")

    jobs = load_jobs(str(batch_path))

    assert jobs[0].water is None

    payload["jobs"][0]["water"] = "   "
    batch_path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_jobs(str(batch_path))[0].water is None


def test_simulation_runs_with_synthesized_water_mask(tmp_path: Path) -> None:
    data = _load_without_water(tmp_path)
    try:
        assert data.water.shape == (2, 2)
        assert not data.water.any()

        instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
        config = build_config(
            grid_size=10,
            t_start=instant,
            t_end=instant,
            harden_rad=0,
            harden_spo=0,
            rad_ig_thresh=14000,
            rad_decay=1,
            brand_wind_coef=30,
            brand_wind_sd=0.3,
            brand_wind_sd_lat=4.85,
            seed_harden=1,
            seed_spread=1,
        )
        run_simulation(
            config,
            data,
            str(tmp_path / "run"),
            frame_dpi=72,
            dump_every=0,
            out_frames=False,
            out_video=False,
            out_gif=False,
            out_ig_plots=False,
            out_fire_csv=False,
            out_buildings_csv=False,
            emit_metrics=False,
            emit_frame_state=False,
        )
    finally:
        data.close()
