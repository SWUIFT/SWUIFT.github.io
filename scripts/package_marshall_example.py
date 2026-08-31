#!/usr/bin/env python3
"""Checksum, reproducibly archive, or verify the Marshall input example."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import tarfile
from pathlib import Path


EXAMPLE_ID = "marshall_20211230_1100-2100_MST"
ARTIFACT_FILES = (
    "Marshall_inputs.mat",
    "default_values.mat",
    "domains_mat.mat",
    "standard.mat",
    "veg_knowing.mat",
    "wind.mat",
)
METADATA_FILES = ("README.md", "manifest.json", "provenance.json")
CHECKSUM_NAME = "input-checksums.sha256"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checksum_entries(
    metadata_dir: Path, artifact_dir: Path
) -> list[tuple[str, Path]]:
    entries = [(name, metadata_dir / name) for name in METADATA_FILES]
    # Keep inputs beside manifest.json so an extracted archive is directly
    # usable as both --manifest parent and --data-root.
    entries.extend((name, artifact_dir / name) for name in ARTIFACT_FILES)
    missing = [archive_name for archive_name, path in entries if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing prepared files: {', '.join(missing)}")
    return sorted(entries)


def write_checksums(metadata_dir: Path, entries: list[tuple[str, Path]]) -> Path:
    checksum_path = metadata_dir / CHECKSUM_NAME
    content = "".join(f"{sha256(path)}  {name}\n" for name, path in entries)
    checksum_path.write_text(content, encoding="ascii")
    return checksum_path


def add_file(archive: tarfile.TarFile, name: str, path: Path) -> None:
    info = tarfile.TarInfo(name=f"{EXAMPLE_ID}/{name}")
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
    entries: list[tuple[str, Path]],
    checksum_path: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(
                fileobj=zipped, mode="w|", format=tarfile.PAX_FORMAT
            ) as archive:
                archive_entries = [*entries, (CHECKSUM_NAME, checksum_path)]
                for archive_name, path in sorted(archive_entries):
                    add_file(archive, archive_name, path)


def expected_checksum_text(entries: list[tuple[str, Path]]) -> str:
    return "".join(f"{sha256(path)}  {name}\n" for name, path in entries)


def verify(
    metadata_dir: Path,
    artifact_dir: Path,
    output: Path,
) -> None:
    entries = checksum_entries(metadata_dir, artifact_dir)
    checksum_path = metadata_dir / CHECKSUM_NAME
    if not checksum_path.is_file():
        raise FileNotFoundError(checksum_path)
    expected = expected_checksum_text(entries)
    if checksum_path.read_text(encoding="ascii") != expected:
        raise ValueError(f"{CHECKSUM_NAME} does not match prepared input files")
    manifest = json.loads((metadata_dir / "manifest.json").read_text(encoding="utf-8"))
    described = manifest.get("artifacts", {})
    if set(described) != set(ARTIFACT_FILES):
        raise ValueError("Input manifest artifact list does not match expected files")
    for name in ARTIFACT_FILES:
        path = artifact_dir / name
        if described[name].get("bytes") != path.stat().st_size:
            raise ValueError(f"Input manifest size mismatch: {name}")
        if described[name].get("sha256") != sha256(path):
            raise ValueError(f"Input manifest checksum mismatch: {name}")
    forbidden_wind = ("wind_s.mat", "wind_d.mat", "marshal_wind.mat")
    present = [name for name in forbidden_wind if (artifact_dir / name).exists()]
    if present:
        raise ValueError(f"Duplicated wind representations found: {', '.join(present)}")
    if not output.is_file():
        raise FileNotFoundError(output)
    root = f"{EXAMPLE_ID}/"
    expected_members = {name: path for name, path in entries}
    expected_members[CHECKSUM_NAME] = checksum_path
    with tarfile.open(output, "r:gz") as archive:
        regular = {
            member.name.removeprefix(root): member
            for member in archive.getmembers()
            if member.isfile() and member.name.startswith(root)
        }
        if set(regular) != set(expected_members):
            raise ValueError("Input archive member list does not match expected files")
        for name, path in expected_members.items():
            archived = archive.extractfile(regular[name])
            if archived is None:
                raise ValueError(f"Cannot read archived member: {name}")
            digest = hashlib.sha256()
            for block in iter(lambda: archived.read(8 * 1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != sha256(path):
                raise ValueError(f"Archived checksum mismatch: {name}")
    print(f"Verified input package\t{output.stat().st_size}\t{sha256(output)}")


def parse_args() -> argparse.Namespace:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata-dir", type=Path, default=root / "examples" / EXAMPLE_ID
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=root / "examples" / "artifacts" / EXAMPLE_ID,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "examples" / "artifacts" / f"{EXAMPLE_ID}.tar.gz",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify staging files, checksums, and archive without writing.",
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
    entries = checksum_entries(metadata_dir, artifact_dir)
    checksum_path = write_checksums(metadata_dir, entries)
    build_archive(output, entries, checksum_path)
    print(f"{output.name}\t{output.stat().st_size}\t{sha256(output)}")


if __name__ == "__main__":
    main()
