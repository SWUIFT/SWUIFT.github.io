#!/usr/bin/env python3
"""Fail if repository source or citation metadata leaked into a Jekyll build."""

from __future__ import annotations

import argparse
from pathlib import Path

FORBIDDEN_TOP_LEVEL = {
    ".github",
    "apps",
    "build",
    "dist",
    "docs",
    "examples",
    "overrides",
    "packages",
    "scripts",
    "site",
    "tests",
}
FORBIDDEN_NAMES = {
    ".zenodo.json",
    "CITATION.cff",
    "environment.yml",
    "mkdocs.yml",
    "public-boundary.toml",
    "pyproject.toml",
    "requirements-build.txt",
    "requirements-cli.txt",
    "requirements-dev.txt",
    "requirements.txt",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()

    if not args.site.is_dir():
        raise SystemExit(f"Jekyll output directory does not exist: {args.site}")

    leaked: list[Path] = []
    for path in args.site.rglob("*"):
        relative = path.relative_to(args.site)
        forbidden_source = path.is_file() and path.suffix in {".cff", ".py", ".toml"}
        if (
            relative.parts[0] in FORBIDDEN_TOP_LEVEL
            or path.name in FORBIDDEN_NAMES
            or forbidden_source
        ):
            leaked.append(relative)

    if leaked:
        formatted = "\n".join(f"- {path}" for path in sorted(leaked))
        raise SystemExit(f"Repository files leaked into the Jekyll site:\n{formatted}")
    print("Jekyll output contains no repository source or citation metadata.")


if __name__ == "__main__":
    main()
