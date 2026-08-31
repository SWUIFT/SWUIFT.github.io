#!/usr/bin/env python3
"""Checksum, reproducibly archive, or verify the Marshall output artifact."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import tarfile
from pathlib import Path


EXAMPLE_ID = "marshall_20211230_1100-2100_MST"
OUTPUT_ID = f"{EXAMPLE_ID}-output"
CHECKSUM_NAME = "output-checksums.sha256"
METADATA_FILES = (
    "output-manifest.json",
    "output-provenance.json",
    "output-summary.json",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def entries(metadata_dir: Path, artifact_dir: Path) -> list[tuple[str, Path]]:
    result = [(name, metadata_dir / name) for name in METADATA_FILES]
    result.extend(
        (path.relative_to(artifact_dir).as_posix(), path)
        for path in artifact_dir.rglob("*")
        if path.is_file()
    )
    missing = [name for name, path in result if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing output package files: {', '.join(missing)}")
    names = [name for name, _ in result]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate output archive member name")
    return sorted(result)


def checksum_text(package_entries: list[tuple[str, Path]]) -> str:
    return "".join(
        f"{sha256(path)}  {name}\n" for name, path in package_entries
    )


def write_checksums(
    metadata_dir: Path, package_entries: list[tuple[str, Path]]
) -> Path:
    path = metadata_dir / CHECKSUM_NAME
    path.write_text(checksum_text(package_entries), encoding="ascii")
    return path


def add_file(archive: tarfile.TarFile, name: str, path: Path) -> None:
    info = tarfile.TarInfo(name=f"{OUTPUT_ID}/{name}")
    info.size = path.stat().st_size
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    with path.open("rb") as handle:
        archive.addfile(info, handle)


def build_archive(
    output: Path,
    package_entries: list[tuple[str, Path]],
    checksum_path: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(
                fileobj=zipped, mode="w|", format=tarfile.PAX_FORMAT
            ) as archive:
                archive_entries = [
                    *package_entries,
                    (CHECKSUM_NAME, checksum_path),
                ]
                for name, path in sorted(archive_entries):
                    add_file(archive, name, path)


def verify(
    metadata_dir: Path,
    artifact_dir: Path,
    output: Path,
) -> None:
    package_entries = entries(metadata_dir, artifact_dir)
    checksum_path = metadata_dir / CHECKSUM_NAME
    if not checksum_path.is_file():
        raise FileNotFoundError(checksum_path)
    if checksum_path.read_text(encoding="ascii") != checksum_text(package_entries):
        raise ValueError(f"{CHECKSUM_NAME} does not match prepared output files")
    manifest = json.loads(
        (metadata_dir / "output-manifest.json").read_text(encoding="utf-8")
    )
    described = manifest.get("files", {})
    staged = {
        path.relative_to(artifact_dir).as_posix(): path
        for path in artifact_dir.rglob("*")
        if path.is_file()
    }
    if set(described) != set(staged):
        raise ValueError("Output manifest file list does not match staging")
    for name, path in staged.items():
        if described[name].get("bytes") != path.stat().st_size:
            raise ValueError(f"Output manifest size mismatch: {name}")
        if described[name].get("sha256") != sha256(path):
            raise ValueError(f"Output manifest checksum mismatch: {name}")
    summary = json.loads(
        (metadata_dir / "output-summary.json").read_text(encoding="utf-8")
    )
    metrics = json.loads(
        (artifact_dir / "metrics_per_step.json").read_text(encoding="utf-8")
    )
    if summary.get("final_step_metrics") != metrics["steps"][-1]:
        raise ValueError("Output summary final metrics do not match scientific output")
    equivalence = summary.get("equivalence", {})
    if not equivalence.get("equivalent") or equivalence.get("semantic_differences") != 0:
        raise ValueError("Output summary does not record zero-difference equivalence")
    for name in ("run_params.json", "run_log.txt"):
        text = (artifact_dir / name).read_text(encoding="utf-8")
        if "/home/" in text:
            raise ValueError(f"Absolute path remains in {name}")
    if not output.is_file():
        raise FileNotFoundError(output)

    root = f"{OUTPUT_ID}/"
    expected = {name: path for name, path in package_entries}
    expected[CHECKSUM_NAME] = checksum_path
    with tarfile.open(output, "r:gz") as archive:
        regular = {
            member.name.removeprefix(root): member
            for member in archive.getmembers()
            if member.isfile() and member.name.startswith(root)
        }
        if set(regular) != set(expected):
            raise ValueError("Output archive member list does not match expected files")
        for name, path in expected.items():
            archived = archive.extractfile(regular[name])
            if archived is None:
                raise ValueError(f"Cannot read archived member: {name}")
            digest = hashlib.sha256()
            for block in iter(lambda: archived.read(8 * 1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != sha256(path):
                raise ValueError(f"Archived checksum mismatch: {name}")
    print(f"Verified output package\t{output.stat().st_size}\t{sha256(output)}")


def parse_args() -> argparse.Namespace:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata-dir", type=Path, default=root / "examples" / EXAMPLE_ID
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=root / "examples" / "artifacts" / OUTPUT_ID,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "examples" / "artifacts" / f"{OUTPUT_ID}.tar.gz",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify staging files, path sanitation, checksums, and archive without writing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata_dir = args.metadata_dir.expanduser().resolve()
    artifact_dir = args.artifact_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if args.verify_only:
        verify(metadata_dir, artifact_dir, output)
        return
    package_entries = entries(metadata_dir, artifact_dir)
    checksum_path = write_checksums(metadata_dir, package_entries)
    build_archive(output, package_entries, checksum_path)
    print(f"{output.name}\t{output.stat().st_size}\t{sha256(output)}")


if __name__ == "__main__":
    main()
