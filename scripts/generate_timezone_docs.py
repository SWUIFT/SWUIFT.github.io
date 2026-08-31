#!/usr/bin/env python3
"""Generate the complete IANA timezone reference used by SWUIFT."""

from __future__ import annotations

import argparse
from pathlib import Path
from zoneinfo import available_timezones, reset_tzpath

reset_tzpath(())


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def render() -> str:
    zones = sorted(available_timezones() | {"UTC"})
    lines = [
        "# Supported timezones",
        "",
        "SWUIFT accepts the following IANA timezone identifiers. Enter local wall",
        "times with one of these identifiers; SWUIFT converts them to UTC for the",
        "simulation and converts result timestamps back to the selected timezone.",
        "",
        "Use `swuift --list-timezones` to print this same catalog in a terminal.",
        "Abbreviations such as `CST` are not accepted because they are ambiguous.",
        "",
    ]
    grouped: dict[str, list[str]] = {}
    for zone in zones:
        group = zone.split("/", 1)[0] if "/" in zone else "Other"
        grouped.setdefault(group, []).append(zone)
    groups = sorted(group for group in grouped if group != "Other")
    if "Other" in grouped:
        groups.append("Other")
    for group in groups:
        lines.extend((f"## {group}", ""))
        lines.extend(f"- `{zone}`" for zone in grouped[group])
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when docs/timezones.md is not current.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = repository_root() / "docs" / "timezones.md"
    expected = render()
    if args.check:
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"{path} is stale; run {Path(__file__).name}")
        print(f"Timezone documentation is current ({len(available_timezones())} zones).")
        return
    path.write_text(expected, encoding="utf-8")
    print(f"Wrote {path} ({len(available_timezones())} zones).")


if __name__ == "__main__":
    main()
