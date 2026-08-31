#!/usr/bin/env python3
"""Verify release artifacts against a SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

CHUNK_SIZE = 1024 * 1024
LINE_PATTERN = re.compile(r"^([0-9a-f]{64})  (.+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = LINE_PATTERN.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid manifest line {line_number}")
        expected, relative = match.groups()
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"unsafe path on manifest line {line_number}: {relative}")
        if relative in entries:
            raise ValueError(f"duplicate path on manifest line {line_number}: {relative}")
        entries[relative] = expected
    if not entries:
        raise ValueError("manifest contains no entries")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--strict-directory",
        type=Path,
        help="also fail for unsigned files in this artifact directory",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    entries = load_manifest(manifest)
    failures: list[str] = []

    for relative, expected in entries.items():
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            failures.append(f"path escapes root: {relative}")
            continue
        if not path.is_file():
            failures.append(f"missing: {relative}")
        elif sha256(path) != expected:
            failures.append(f"checksum mismatch: {relative}")

    if args.strict_directory:
        directory = (
            args.strict_directory
            if args.strict_directory.is_absolute()
            else root / args.strict_directory
        ).resolve()
        for path in directory.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if (
                path.is_file()
                and path.resolve() != manifest.resolve()
                and relative not in entries
                and not relative.endswith((".sig", ".sigstore.json", ".intoto.jsonl"))
            ):
                failures.append(f"unlisted artifact: {relative}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print(f"Verified {len(entries)} artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
