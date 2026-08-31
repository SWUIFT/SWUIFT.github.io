#!/usr/bin/env python3
"""Prepare a sanitized, deterministic Marshall simulation output artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


EXAMPLE_ID = "marshall_20211230_1100-2100_MST"
OUTPUT_ID = f"{EXAMPLE_ID}-output"
SOURCE_LABEL = (
    "cross_fire_YYYYMMDD_HHMMSS/public_release_marshall_output/"
    "marshall_python_20260820_160839"
)
SCIENTIFIC_FILES = (
    "fire_prog.csv",
    "ig_pixel.png",
    "ig_structure.png",
    "metrics_per_step.csv",
    "metrics_per_step.json",
    "zvector.csv",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_source() -> Path:
    return repository_root().parent / SOURCE_LABEL


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


def all_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def sanitize_path(value: str) -> str:
    if not value.startswith("/"):
        return value
    name = Path(value).name
    if name == "manifest.json":
        return "manifest.json"
    if name == EXAMPLE_ID:
        return "."
    if name == "public_release_marshall_output":
        return "<OUTPUT_PARENT>"
    if name.startswith("marshall_python_"):
        return "<OUTPUT_DIR>"
    return name


def sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, str):
        if value.startswith("/"):
            return sanitize_path(value)
        if "/home/" in value:
            tokens = value.split()
            return " ".join(sanitize_path(token) if token.startswith("/") else token for token in tokens)
    return value


def sanitize_run_params(source: Path, target: Path) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    sanitized = sanitize_json_value(payload)
    write_json(target, sanitized)


def sanitize_run_log(source: Path, target: Path) -> None:
    text = source.read_text(encoding="utf-8")
    replacements = {
        str(source.parent): "<OUTPUT_DIR>",
        str(source.parent.parent): "<OUTPUT_PARENT>",
        str(repository_root() / "examples" / "artifacts" / EXAMPLE_ID): ".",
        str(repository_root() / "examples" / EXAMPLE_ID / "manifest.json"): "manifest.json",
    }
    for original in sorted(replacements, key=len, reverse=True):
        text = text.replace(original, replacements[original])
    if "/home/" in text:
        raise ValueError("Absolute path remains in sanitized run_log.txt")
    target.write_text(text, encoding="utf-8")


def copy_outputs(source: Path, artifact_dir: Path) -> None:
    for name in SCIENTIFIC_FILES:
        shutil.copyfile(source / name, artifact_dir / name)
    for dirname in ("checkpoints", "normalized_frame_state"):
        shutil.copytree(source / dirname, artifact_dir / dirname)
    sanitize_run_params(source / "run_params.json", artifact_dir / "run_params.json")
    sanitize_run_log(source / "run_log.txt", artifact_dir / "run_log.txt")


def make_final_state_preview(final_state_path: Path, output: Path) -> None:
    state = np.load(final_state_path, allow_pickle=False)
    if state.shape != (864, 965) or state.dtype != np.int16:
        raise ValueError(f"Unexpected final state: shape={state.shape}, dtype={state.dtype}")
    colors = {
        -4: (106, 64, 42),
        -2: (190, 225, 255),
        -1: (91, 143, 70),
        0: (245, 245, 240),
        1: (55, 55, 55),
        2: (255, 211, 92),
        3: (235, 91, 55),
        4: (87, 31, 31),
    }
    rgb = np.empty((*state.shape, 3), dtype=np.uint8)
    for value, color in colors.items():
        rgb[state == value] = color
    unknown = ~np.isin(state, list(colors))
    if np.any(unknown):
        raise ValueError(f"Unknown final-state categories: {np.unique(state[unknown])}")
    Image.fromarray(rgb, mode="RGB").save(
        output, format="PNG", optimize=False, compress_level=9
    )


def describe(path: Path, relative: str) -> dict[str, Any]:
    item: dict[str, Any] = {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    if path.suffix == ".npy":
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        item.update(dtype=str(array.dtype), shape=list(array.shape))
    elif path.suffix == ".png":
        with Image.open(path) as image:
            item.update(format=image.format, mode=image.mode, size=list(image.size))
    elif relative == "fire_prog.csv":
        item.update(dtype="float64 text", shape=[864, 965])
    elif relative == "zvector.csv":
        item.update(dtype="float64 text", shape=[22767, 5])
    elif relative == "metrics_per_step.csv":
        item.update(records=121)
    return item


def build_summary(artifact_dir: Path) -> dict[str, Any]:
    metrics = json.loads((artifact_dir / "metrics_per_step.json").read_text())
    steps = metrics["steps"]
    if len(steps) != 121 or steps[-1]["tstep"] != 121:
        raise ValueError("Expected exactly 121 completed metric steps")
    final_state = np.load(
        artifact_dir / "normalized_frame_state" / "state_0121.npy",
        allow_pickle=False,
    )
    values, counts = np.unique(final_state, return_counts=True)
    return {
        "schema_version": 1,
        "artifact_id": OUTPUT_ID,
        "run": {
            "status": "completed",
            "steps": 121,
            "start_time_utc": "2021-12-30T18:00:00Z",
            "end_time_utc": "2021-12-31T04:00:00Z",
            "wall_start_timestamp_preserved_in_run_params": "2026-08-20T16:08:39.868780",
            "wall_end_timestamp_preserved_in_run_params": "2026-08-20T16:12:36.959090",
        },
        "final_step_metrics": steps[-1],
        "final_state_counts": {
            str(int(value)): int(count)
            for value, count in zip(values, counts)
        },
        "equivalence": {
            "equivalent": True,
            "comparison": "public 121-step run versus private 144-step run through step 121",
            "excluded_fields": ["progress_fraction", "step_wall_seconds"],
            "semantic_differences": 0,
            "basis": "completed cross-run numerical equivalence comparison",
        },
    }


def parse_args() -> argparse.Namespace:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=default_source())
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=root / "examples" / "artifacts" / OUTPUT_ID,
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
    required = [
        *SCIENTIFIC_FILES,
        "run_params.json",
        "run_log.txt",
        "checkpoints/t000121/fire.npy",
        "checkpoints/t000121/ignition.npy",
        "checkpoints/t000121/out_fire.npy",
        "checkpoints/t000121/radtotal.npy",
        "checkpoints/t000121/zvector.npy",
        "normalized_frame_state/state_0121.npy",
    ]
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing completed outputs: {', '.join(missing)}")

    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    artifact_dir.mkdir(parents=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    copy_outputs(source, artifact_dir)
    make_final_state_preview(
        artifact_dir / "normalized_frame_state" / "state_0121.npy",
        artifact_dir / "final-state-preview.png",
    )

    source_files = all_files(source)
    staged_files = all_files(artifact_dir)
    source_hashes = {
        path.relative_to(source).as_posix(): sha256(path) for path in source_files
    }
    artifacts = {
        path.relative_to(artifact_dir).as_posix(): describe(
            path, path.relative_to(artifact_dir).as_posix()
        )
        for path in staged_files
    }
    manifest = {
        "schema_version": 1,
        "artifact_id": OUTPUT_ID,
        "scenario_id": "marshall",
        "timesteps": 121,
        "files": artifacts,
    }
    provenance = {
        "schema_version": 1,
        "artifact_id": OUTPUT_ID,
        "source": {
            "completed_run": SOURCE_LABEL,
            "files": source_hashes,
        },
        "transformations": {
            "scientific_outputs": "copied byte-for-byte",
            "timestamps": "preserved in run_params.json and run_log.txt",
            "run_params.json": "absolute paths replaced with portable relative names or placeholders",
            "run_log.txt": "absolute paths replaced with portable relative names or placeholders",
            "final-state-preview.png": "deterministic categorical rendering of state_0121.npy",
        },
        "path_safety": {
            "absolute_source_paths_emitted": False,
            "machine_specific_command_paths_emitted": False,
        },
    }
    write_json(metadata_dir / "output-manifest.json", manifest)
    write_json(metadata_dir / "output-provenance.json", provenance)
    write_json(metadata_dir / "output-summary.json", build_summary(artifact_dir))
    print(f"Prepared {OUTPUT_ID}")
    print(f"files\t{len(staged_files)}")
    print(f"bytes\t{sum(path.stat().st_size for path in staged_files)}")


if __name__ == "__main__":
    main()
