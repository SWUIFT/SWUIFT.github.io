#!/usr/bin/env python3
"""Fail when the public tree contains disallowed or unsafe files."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised in the Python 3.10 CI job
    import tomli as tomllib


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def tracked_files(root: Path) -> list[Path] | None:
    top_level = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if top_level.returncode != 0 or Path(top_level.stdout.strip()).resolve() != root.resolve():
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return [root / item.decode() for item in result.stdout.split(b"\0") if item]


def fallback_files(root: Path, ignores: list[str]) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not matches(path.relative_to(root).as_posix(), ignores)
        and not any(part == ".git" for part in path.relative_to(root).parts)
    ]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    if config.get("schema_version") != 1:
        raise ValueError("public-boundary.toml must use schema_version = 1")
    return config


def check(root: Path, config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for required in config["required_files"]:
        if not (root / required).is_file():
            errors.append(f"required file is missing: {required}")

    files = tracked_files(root) if config["tracked_files_only"] else None
    if files is None:
        files = fallback_files(root, config["fallback_scan_ignores"])

    root_resolved = root.resolve()
    for path in files:
        relative = path.relative_to(root).as_posix()
        if matches(relative, config["denied_paths"]):
            errors.append(f"denied public path: {relative}")
        lowered = relative.casefold()
        for fragment in config["denied_name_fragments"]:
            if fragment.casefold() in lowered:
                errors.append(f"denied name fragment {fragment!r}: {relative}")
        if (
            path.is_symlink()
            and not config["allow_external_symlinks"]
            and not path.resolve().is_relative_to(root_resolved)
        ):
            errors.append(f"symlink leaves repository: {relative}")
        if path.exists() and path.stat().st_size > config["maximum_file_size_bytes"]:
            errors.append(f"file exceeds public size limit: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("public-boundary.toml"),
        help="boundary configuration relative to the repository root",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = args.config if args.config.is_absolute() else root / args.config
    errors = check(root, load_config(config_path))
    if errors:
        print("Public-boundary check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Public-boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
