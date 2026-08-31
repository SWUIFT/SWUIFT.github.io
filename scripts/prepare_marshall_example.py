#!/usr/bin/env python3
"""Build the deterministic, Python-only Marshall example input artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import scipy.io as sio


EXAMPLE_ID = "marshall_20211230_1100-2100_MST"
STEPS = 121
SOURCE_WIND_STEPS = 144
STATIC_FILES = (
    "default_values.mat",
    "domains_mat.mat",
    "Marshall_inputs.mat",
    "standard.mat",
)
SOURCE_LABEL = "SWUIFT-CORE/data/marshall"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_source() -> Path:
    return repository_root().parent / "SWUIFT-CORE" / "data" / "marshall"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def save_deterministic_mat(path: Path, variable: str, value: np.ndarray) -> None:
    """Write MATLAB v5 data with a fixed, non-timestamped header."""
    sio.savemat(
        path,
        {variable: value},
        appendmat=False,
        do_compression=True,
        format="5",
        long_field_names=True,
        oned_as="column",
    )
    fixed_header = (
        b"MATLAB 5.0 MAT-file, Platform: SWUIFT, "
        b"Created deterministically for the public Marshall example"
    )
    with path.open("r+b") as handle:
        handle.write(fixed_header[:116].ljust(116, b" "))


def copy_static_inputs(source: Path, artifact_dir: Path) -> None:
    for name in STATIC_FILES:
        shutil.copyfile(source / name, artifact_dir / name)


def prepare_ignition(source: Path, artifact_dir: Path) -> dict[str, int]:
    raw = sio.loadmat(source / "veg_knowing.mat", squeeze_me=True)["veg_knowing"]
    known = np.asarray(raw)
    if known.shape != (864, 965):
        raise ValueError(f"Unexpected veg_knowing shape: {known.shape}")
    if np.any(known < 0):
        raise ValueError("veg_knowing contains negative timestep values")
    post_cutoff = known > STEPS
    truncated = known.copy()
    truncated[post_cutoff] = 0
    save_deterministic_mat(artifact_dir / "veg_knowing.mat", "veg_knowing", truncated)
    return {
        "positive_entries_before": int(np.count_nonzero(known)),
        "post_cutoff_entries_zeroed": int(np.count_nonzero(post_cutoff)),
        "positive_entries_after": int(np.count_nonzero(truncated)),
        "maximum_source_timestep": int(np.max(known)),
        "maximum_output_timestep": int(np.max(truncated)),
    }


def prepare_wind(source: Path, artifact_dir: Path) -> None:
    source_path = source / "marshal_wind.mat"
    output_path = artifact_dir / "wind.mat"
    with h5py.File(source_path, "r") as src, h5py.File(
        output_path, "w", libver="earliest", track_order=False
    ) as dst:
        for name in ("wind_s", "wind_d"):
            source_data = src[name]
            expected = (SOURCE_WIND_STEPS, 965, 864)
            if source_data.shape != expected:
                raise ValueError(
                    f"Unexpected {name} storage shape: {source_data.shape}; "
                    f"expected {expected}"
                )
            output_data = dst.create_dataset(
                name,
                shape=(STEPS, 965, 864),
                dtype=np.dtype("<f8"),
                chunks=(1, 121, 108),
                compression="gzip",
                compression_opts=3,
                shuffle=False,
                fletcher32=False,
                track_times=False,
            )
            for step in range(STEPS):
                output_data[step, :, :] = source_data[step, :, :]


def describe_file(path: Path, variables: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "variables": variables,
    }


def build_manifest(artifact_dir: Path) -> dict[str, Any]:
    artifacts = {
        "default_values.mat": describe_file(
            artifact_dir / "default_values.mat",
            {"multiple_configuration_scalars": {"format": "MATLAB v5"}},
        ),
        "domains_mat.mat": describe_file(
            artifact_dir / "domains_mat.mat",
            {"domains_mat": {"dtype": "float64", "shape": [864, 965]}},
        ),
        "Marshall_inputs.mat": describe_file(
            artifact_dir / "Marshall_inputs.mat",
            {
                "binary_cover": {"dtype": "float64", "shape": [864, 965]},
                "homes_mat": {"dtype": "float64", "shape": [864, 965]},
                "knownig_mat": {"dtype": "float64", "shape": [864, 965]},
                "lati": {"dtype": "float64", "shape": [864, 1]},
                "long": {"dtype": "float64", "shape": [965, 1]},
            },
        ),
        "veg_knowing.mat": describe_file(
            artifact_dir / "veg_knowing.mat",
            {"veg_knowing": {"dtype": "uint8", "shape": [864, 965]}},
        ),
        "standard.mat": describe_file(
            artifact_dir / "standard.mat",
            {"standard": {"dtype": "float64", "shape": [864, 965]}},
        ),
        "wind.mat": describe_file(
            artifact_dir / "wind.mat",
            {
                "wind_s": {
                    "dtype": "float64",
                    "logical_shape": [864, 965, STEPS],
                    "hdf5_storage_shape": [STEPS, 965, 864],
                },
                "wind_d": {
                    "dtype": "float64",
                    "logical_shape": [864, 965, STEPS],
                    "hdf5_storage_shape": [STEPS, 965, 864],
                },
            },
        ),
    }
    return {
        "schema_version": 1,
        "scenario_id": "marshall",
        "display_name": "Marshall public Python example (121 steps)",
        "matlab": {"included": False},
        "inputs": {
            "defaults": {"file": "default_values.mat"},
            "bundle": {"file": "Marshall_inputs.mat"},
            "variables": {
                "binary_cover": "binary_cover",
                "homes_mat": "homes_mat",
                "lati": "lati",
                "long": "long",
                "water": None,
            },
            "domains": {"file": "domains_mat.mat", "variable": "domains_mat"},
            "known_ignition": {
                "file": "veg_knowing.mat",
                "variable": "veg_knowing",
            },
            "hardening": {
                "mode": "single_map",
                "file": "standard.mat",
                "variable": "standard",
            },
            "wind": {
                "packaging": "single_hdf5",
                "speed_file": "wind.mat",
                "direction_file": "wind.mat",
                "speed_variable": "wind_s",
                "direction_variable": "wind_d",
                "layout": "rows_cols_time",
            },
        },
        "config": {
            "grid_size": 13.875,
            "t_start": "2021-12-30 11:00",
            "t_end": "2021-12-30 21:00",
            "timezone": "America/Denver",
            "expected_steps": STEPS,
            "harden_rad": 70.0,
            "harden_spo": 70.0,
            "rad_ig_thresh": 14000.0,
            "rad_decay": 1.0,
            "brand_wind_coef": 30.0,
            "brand_wind_sd": 0.3,
            "brand_wind_sd_lat": 4.85,
            "hardening_profile": "matlab_inert",
            "rng_profile": "seeded",
            "seed_harden": 123456,
            "seed_spread": 10,
        },
        "time": {
            "basis": "local IANA timezone converted to UTC for simulation",
            "local_zone": "America/Denver",
            "start_inclusive_utc": "2021-12-30T18:00:00Z",
            "end_inclusive_utc": "2021-12-31T04:00:00Z",
            "start_inclusive_local": "2021-12-30T11:00:00-07:00",
            "end_inclusive_local": "2021-12-30T21:00:00-07:00",
            "step_minutes": 5,
            "inclusive_timesteps": STEPS,
        },
        "artifacts": artifacts,
    }


def parse_args() -> argparse.Namespace:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=default_source())
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=root / "examples" / "artifacts" / EXAMPLE_ID,
    )
    parser.add_argument(
        "--metadata-dir", type=Path, default=root / "examples" / EXAMPLE_ID
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.expanduser().resolve()
    artifact_dir = args.artifact_dir.expanduser().resolve()
    metadata_dir = args.metadata_dir.expanduser().resolve()
    required = [*STATIC_FILES, "veg_knowing.mat", "marshal_wind.mat"]
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing approved inputs: {', '.join(missing)}")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    expected_outputs = {*STATIC_FILES, "veg_knowing.mat", "wind.mat"}
    for child in artifact_dir.iterdir():
        if child.is_file() and child.name not in expected_outputs:
            raise ValueError(f"Refusing unexpected file in artifact directory: {child.name}")

    copy_static_inputs(source, artifact_dir)
    ignition_stats = prepare_ignition(source, artifact_dir)
    prepare_wind(source, artifact_dir)
    manifest = build_manifest(artifact_dir)
    provenance = {
        "schema_version": 1,
        "artifact_id": EXAMPLE_ID,
        "source": {
            "approved_dataset": SOURCE_LABEL,
            "files": {
                name: sha256(source / name)
                for name in required
            },
        },
        "transformations": {
            "static_inputs": "byte-for-byte copies of required approved inputs",
            "wind": {
                "source_file": "marshal_wind.mat",
                "output_file": "wind.mat",
                "source_timesteps": SOURCE_WIND_STEPS,
                "retained_zero_based_slice": [0, STEPS],
                "retained_inclusive_timesteps": STEPS,
                "variables": ["wind_s", "wind_d"],
            },
            "known_ignition": {
                "policy": "values after timestep 121 are set to zero",
                **ignition_stats,
            },
        },
        "determinism": {
            "json": "sorted keys, UTF-8, LF, final newline",
            "generated_mat_v5": "compressed with fixed 116-byte descriptive header",
            "generated_hdf5": "fixed dataset order, chunks, dtype, and compression",
        },
    }
    write_json(metadata_dir / "manifest.json", manifest)
    write_json(metadata_dir / "provenance.json", provenance)
    print(f"Prepared {EXAMPLE_ID}")
    for path in sorted(artifact_dir.iterdir()):
        print(f"{path.name}\\t{path.stat().st_size}\\t{sha256(path)}")


if __name__ == "__main__":
    main()
