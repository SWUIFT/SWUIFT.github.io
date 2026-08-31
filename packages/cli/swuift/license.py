"""Locate and identify the authoritative SWUIFT license."""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path


@dataclass(frozen=True)
class LicenseInfo:
    path: Path
    text: str
    sha256: str


def _license_candidates() -> list[Path]:
    candidates: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "LICENSE")

    module_path = Path(__file__).resolve()
    source_root = module_path.parents[3]
    source_module = source_root / "packages" / "cli" / "swuift" / "license.py"
    if source_module.resolve() == module_path:
        candidates.append(source_root / "LICENSE")

    try:
        package = distribution("swuift")
    except PackageNotFoundError:
        package = None
    if package is not None:
        for entry in package.files or ():
            normalized = entry.as_posix()
            if normalized == "LICENSE" or normalized.endswith("/licenses/LICENSE"):
                candidates.append(Path(str(package.locate_file(entry))))

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved not in seen:
            unique.append(resolved)
            seen.add(resolved)
    return unique


def load_license() -> LicenseInfo:
    """Read the bundled license or fail closed when it cannot be located."""
    for path in _license_candidates():
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"Cannot read the SWUIFT license at {path}: {exc}") from exc
        if not text.strip():
            raise RuntimeError(f"The SWUIFT license at {path} is empty.")
        return LicenseInfo(
            path=path,
            text=text,
            sha256=hashlib.sha256(raw).hexdigest(),
        )
    checked = ", ".join(str(path) for path in _license_candidates())
    raise FileNotFoundError(
        f"SWUIFT cannot start because its required LICENSE file is missing. Checked: {checked}"
    )
