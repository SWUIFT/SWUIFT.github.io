#!/usr/bin/env python3
"""Generate a deterministic SHA-256 manifest for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(root: Path, inputs: list[Path], output: Path) -> list[Path]:
    files: set[Path] = set()
    for supplied in inputs:
        path = supplied if supplied.is_absolute() else root / supplied
        if not path.exists():
            raise FileNotFoundError(f"artifact path does not exist: {supplied}")
        candidates = [path] if path.is_file() else path.rglob("*")
        for candidate in candidates:
            if candidate.is_symlink():
                raise ValueError(f"release artifacts may not be symlinks: {candidate}")
            if candidate.is_file() and candidate.resolve() != output.resolve():
                candidate.resolve().relative_to(root.resolve())
                files.add(candidate.resolve())
    return sorted(files, key=lambda item: item.relative_to(root.resolve()).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("dist")])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("dist/SHA256SUMS"))
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    files = collect_files(root, args.paths, output)
    if not files:
        raise ValueError("no release artifacts found")

    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{sha256(path)}  {path.relative_to(root).as_posix()}" for path in files]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(lines)} checksums to {output.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
