#!/usr/bin/env python3
"""Check that package release metadata agrees on version and license."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised in the Python 3.10 CI job
    import tomli as tomllib

EXPECTED_LICENSE = "LicenseRef-SWUIFT-Research-Academic-Use"


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="release tag, expected in the form vX.Y.Z")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    core = load_toml(root / "packages/core/pyproject.toml")["project"]
    cli = load_toml(root / "packages/cli/pyproject.toml")["project"]

    versions = {
        str(core["version"]),
        str(cli["version"]),
    }
    if len(versions) != 1:
        raise ValueError(f"release versions disagree: {sorted(versions)}")
    version = versions.pop()

    if core["license"] != EXPECTED_LICENSE or cli["license"] != EXPECTED_LICENSE:
        raise ValueError("package license expressions disagree")
    root_license = (root / "LICENSE").read_bytes()
    for package_license in ("packages/core/LICENSE", "packages/cli/LICENSE"):
        if (root / package_license).read_bytes() != root_license:
            raise ValueError(f"{package_license} differs from the authoritative LICENSE")
    if f"swuift-core=={version}" not in cli["dependencies"]:
        raise ValueError("CLI must depend on the matching swuift-core release")
    if args.tag and args.tag != f"v{version}":
        raise ValueError(f"tag {args.tag!r} does not match package version v{version}")

    print(f"Release metadata is consistent at version {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
