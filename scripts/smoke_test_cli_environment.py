#!/usr/bin/env python3
"""Run a one-step synthetic simulation through the installed SWUIFT CLI."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np


def _write_csv(path: Path, values: np.ndarray) -> Path:
    np.savetxt(path, values, delimiter=",")
    return path


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="swuift-environment-smoke-") as temp:
        root = Path(temp)
        shape = (2, 2)
        zeros = np.zeros(shape)
        inputs = {
            name: _write_csv(root / f"{name}.csv", zeros)
            for name in (
                "fire",
                "domains",
                "cover",
                "homes",
                "rad",
                "spo",
            )
        }
        inputs["lat"] = _write_csv(root / "lat.csv", np.array([40.0, 40.1]))
        inputs["lon"] = _write_csv(root / "lon.csv", np.array([-105.1, -105.0]))
        _write_csv(root / "wind_s.csv", zeros)
        _write_csv(root / "wind_d.csv", zeros)

        command = [
            "swuift",
            "--accept-license",
            "--job-name",
            "environment-smoke",
            "--fire-prog",
            str(inputs["fire"]),
            "--domains",
            str(inputs["domains"]),
            "--landcover",
            str(inputs["cover"]),
            "--homes",
            str(inputs["homes"]),
            "--lat",
            str(inputs["lat"]),
            "--lon",
            str(inputs["lon"]),
            "--harden-rad-map",
            str(inputs["rad"]),
            "--harden-spo-map",
            str(inputs["spo"]),
            "--wind",
            str(root / "wind.csv"),
            "--grid-size",
            "10",
            "--t-start",
            "2026-01-01 00:00",
            "--t-end",
            "2026-01-01 00:00",
            "--timezone",
            "UTC",
            "--harden-rad",
            "0",
            "--harden-spo",
            "0",
            "--rad-ig-thresh",
            "14000",
            "--rad-decay",
            "1",
            "--brand-wind-coef",
            "30",
            "--brand-wind-sd",
            "0.3",
            "--brand-wind-sd-lat",
            "4.85",
            "--seed-harden",
            "1",
            "--seed-spread",
            "1",
            "--no-lazy-wind",
            "--output-dir",
            str(root / "outputs"),
            "--frame-dpi",
            "72",
            "--dump-every",
            "0",
            "--no-dump-csv",
            "--no-out-frames",
            "--no-out-video",
            "--no-out-gif",
            "--no-out-ig-plots",
            "--no-out-fire-csv",
            "--no-out-buildings-csv",
        ]
        environment = os.environ.copy()
        environment.setdefault("SWUIFT_APP_KERNEL_BACKEND", "python")
        subprocess.run(command, check=True, env=environment)

        run_directories = list((root / "outputs").glob("environment-smoke_*"))
        if len(run_directories) != 1:
            raise RuntimeError(f"Expected one run directory, found {len(run_directories)}")
        required_outputs = ("run_log.txt", "run_params.json")
        missing = [name for name in required_outputs if not (run_directories[0] / name).is_file()]
        if missing:
            raise RuntimeError(f"Simulation did not create: {', '.join(missing)}")
        print("SWUIFT environment smoke simulation passed.")


if __name__ == "__main__":
    main()
