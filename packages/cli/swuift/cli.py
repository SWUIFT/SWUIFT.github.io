"""Command-line entry point for strict SWUIFT runs (single or batch)."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from .job import JobSpec, load_jobs, parse_datetime, validate_output_dir
from .license import LicenseInfo, load_license
from .logger import format_command
from .runner import run_single
from .scenario import build_scenario_job, load_scenario_manifest
from .timezones import timezone_catalog, validate_timezone


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swuift",
        description="SWUIFT wildfire-urban-interface simulation (explicit inputs only).",
    )
    parser.add_argument("--batch", help="Path to JSON file containing a jobs array.")
    parser.add_argument("--scenario", choices=("marshall",))
    parser.add_argument("--manifest", help="Path to a scenario manifest JSON file.")
    parser.add_argument(
        "--data-root", help="Scenario data root (or parent containing scenario folders)."
    )
    parser.add_argument("--job-name", help="Unique name for single-run mode.")
    parser.add_argument(
        "--accept-license",
        action="store_true",
        help="Accept the bundled SWUIFT license for this non-interactive invocation.",
    )
    parser.add_argument(
        "--list-timezones",
        action="store_true",
        help="List every supported IANA timezone identifier and exit.",
    )

    # Input files
    parser.add_argument("--fire-prog")
    parser.add_argument("--domains")
    parser.add_argument("--landcover")
    parser.add_argument("--homes")
    parser.add_argument("--lat")
    parser.add_argument("--lon")
    parser.add_argument("--harden-rad-map")
    parser.add_argument("--harden-spo-map")
    parser.add_argument(
        "--water",
        help="Optional non-burnable water mask; omitted means no cells are marked as water.",
    )
    parser.add_argument("--wind")

    # Required hyperparameters
    parser.add_argument("--grid-size", type=float)
    parser.add_argument(
        "--t-start",
        type=parse_datetime,
        help="Simulation start as local wall time (YYYY-MM-DD HH:MM).",
    )
    parser.add_argument(
        "--t-end",
        type=parse_datetime,
        help="Simulation end as local wall time (YYYY-MM-DD HH:MM).",
    )
    parser.add_argument(
        "--timezone",
        type=validate_timezone,
        help="Required IANA timezone for --t-start/--t-end, for example America/Denver.",
    )
    parser.add_argument("--harden-rad", type=float)
    parser.add_argument("--harden-spo", type=float)
    parser.add_argument("--rad-ig-thresh", type=float)
    parser.add_argument("--rad-decay", type=float)
    parser.add_argument("--brand-wind-coef", type=float)
    parser.add_argument("--brand-wind-sd", type=float)
    parser.add_argument("--brand-wind-sd-lat", type=float)
    parser.add_argument("--seed-harden", type=int)
    parser.add_argument("--seed-spread", type=int)
    parser.add_argument(
        "--lazy-wind",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable/disable lazy HDF5 wind loading (required in single-run mode).",
    )

    # Run controls required for single mode
    parser.add_argument("--output-dir")
    parser.add_argument("--frame-dpi", type=int)
    parser.add_argument("--dump-every", type=int)
    parser.add_argument(
        "--dump-csv",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Dump step-state as CSV (or disable for .npy). Required in single mode.",
    )

    # Output controls (defaults only here)
    parser.add_argument("--out-frames", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out-video", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out-gif", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out-ig-plots", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out-fire-csv", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out-buildings-csv", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out-rad-steps", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--out-spo-steps", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--forensic-full", action=argparse.BooleanOptionalAction, default=False)
    return parser


def _exit_for_license(parser: argparse.ArgumentParser, message: str) -> NoReturn:
    parser.exit(2, f"swuift: error: {message}\n")


def _require_license_acceptance(
    parser: argparse.ArgumentParser,
    *,
    accepted_by_flag: bool,
) -> LicenseInfo:
    try:
        license_info = load_license()
    except (FileNotFoundError, RuntimeError) as exc:
        _exit_for_license(parser, str(exc))

    print(f"SWUIFT license: {license_info.path}")
    print(f"SHA-256: {license_info.sha256}")
    if accepted_by_flag:
        print("License accepted for this invocation via --accept-license.")
        return license_info
    if not sys.stdin.isatty():
        _exit_for_license(
            parser,
            "non-interactive simulation runs require --accept-license. "
            f"Read the license at {license_info.path}",
        )
    try:
        response = input("Do you accept the SWUIFT license? [y/N] ")
    except EOFError:
        _exit_for_license(parser, "license response was unavailable; simulation cancelled.")
    if response.strip().lower() not in {"y", "yes"}:
        _exit_for_license(parser, "license was not accepted; simulation cancelled.")
    return license_info


def _missing_single_fields(args: argparse.Namespace) -> list[str]:
    required = [
        "job_name",
        "fire_prog",
        "domains",
        "landcover",
        "homes",
        "lat",
        "lon",
        "harden_rad_map",
        "harden_spo_map",
        "wind",
        "grid_size",
        "t_start",
        "t_end",
        "timezone",
        "harden_rad",
        "harden_spo",
        "rad_ig_thresh",
        "rad_decay",
        "brand_wind_coef",
        "brand_wind_sd",
        "brand_wind_sd_lat",
        "seed_harden",
        "seed_spread",
        "lazy_wind",
        "output_dir",
        "frame_dpi",
        "dump_every",
        "dump_csv",
    ]
    return [name for name in required if getattr(args, name) is None]


def _build_single_job(args: argparse.Namespace) -> JobSpec:
    missing = _missing_single_fields(args)
    if missing:
        joined = ", ".join(f"--{m.replace('_', '-')}" for m in missing)
        raise ValueError(f"Job {args.job_name!r} missing required CLI parameters: {joined}")
    return JobSpec(
        name=args.job_name,
        fire_prog=args.fire_prog,
        domains=args.domains,
        landcover=args.landcover,
        homes=args.homes,
        lat=args.lat,
        lon=args.lon,
        harden_rad_map=args.harden_rad_map,
        harden_spo_map=args.harden_spo_map,
        water=(args.water.strip() or None) if args.water else None,
        wind=args.wind,
        grid_size=args.grid_size,
        t_start=args.t_start,
        t_end=args.t_end,
        timezone=args.timezone,
        harden_rad=args.harden_rad,
        harden_spo=args.harden_spo,
        rad_ig_thresh=args.rad_ig_thresh,
        rad_decay=args.rad_decay,
        brand_wind_coef=args.brand_wind_coef,
        brand_wind_sd=args.brand_wind_sd,
        brand_wind_sd_lat=args.brand_wind_sd_lat,
        seed_harden=args.seed_harden,
        seed_spread=args.seed_spread,
        lazy_wind=args.lazy_wind,
        output_dir=validate_output_dir(args.output_dir, args.job_name),
        frame_dpi=args.frame_dpi,
        dump_every=args.dump_every,
        dump_csv=args.dump_csv,
        out_frames=args.out_frames,
        out_video=args.out_video,
        out_gif=args.out_gif,
        out_ig_plots=args.out_ig_plots,
        out_fire_csv=args.out_fire_csv,
        out_buildings_csv=args.out_buildings_csv,
        out_rad_steps=args.out_rad_steps,
        out_spo_steps=args.out_spo_steps,
        checkpoint_every=args.checkpoint_every,
        forensic_full=args.forensic_full,
    )


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.list_timezones:
        print("\n".join(timezone_catalog()))
        return
    command_line = format_command(["swuift", *(argv or sys.argv[1:])])

    if args.batch:
        license_info = _require_license_acceptance(
            parser,
            accepted_by_flag=args.accept_license,
        )
        jobs = load_jobs(args.batch)
        for idx, job in enumerate(jobs, start=1):
            print(f"[{idx}/{len(jobs)}] Executing {job.name}")
            run_single(
                job,
                command_line=f"{command_line} --job {job.name}",
                license_info=license_info,
            )
        return

    if args.scenario or args.manifest:
        if args.scenario and args.manifest:
            parser.error("Use either --scenario or --manifest, not both.")
        if not args.data_root or not args.output_dir:
            parser.error("Scenario mode requires --data-root and --output-dir.")
        license_info = _require_license_acceptance(
            parser,
            accepted_by_flag=args.accept_license,
        )
        manifest = load_scenario_manifest(args.manifest or args.scenario)
        job = build_scenario_job(
            manifest,
            data_root=args.data_root,
            output_dir=args.output_dir,
            lazy_wind=True if args.lazy_wind is None else args.lazy_wind,
            frame_dpi=150 if args.frame_dpi is None else args.frame_dpi,
            dump_every=0 if args.dump_every is None else args.dump_every,
            dump_csv=False if args.dump_csv is None else args.dump_csv,
            out_frames=args.out_frames,
            out_video=args.out_video,
            out_gif=args.out_gif,
            out_ig_plots=args.out_ig_plots,
            checkpoint_every=args.checkpoint_every,
            forensic_full=args.forensic_full,
        )
        run_single(job, command_line=command_line, license_info=license_info)
        return

    missing = _missing_single_fields(args)
    if missing:
        joined = ", ".join(f"--{name.replace('_', '-')}" for name in missing)
        parser.error(f"Single-run mode is missing required parameters: {joined}")
    license_info = _require_license_acceptance(
        parser,
        accepted_by_flag=args.accept_license,
    )
    job = _build_single_job(args)
    run_single(job, command_line=command_line, license_info=license_info)


if __name__ == "__main__":
    main()
