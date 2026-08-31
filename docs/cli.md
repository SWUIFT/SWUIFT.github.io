# Command line

The `swuift` command supports one explicit run or a sequential JSON batch.

You need a complete, licensed SWUIFT input bundle before beginning. The
software distribution does not imply redistribution rights for third-party
geospatial or wind data.

```bash
swuift --help
python -m swuift --help
```

## Quick start

1. Enter the venv, uv, or Conda environment created in
   [Install & verify](installation.md#3-install-the-cli-from-source), and
   confirm that `swuift --help` succeeds.
2. Create `jobs.json` using the complete [batch example](#batch-mode). Each job
   needs the nine required paths from the [input schema](input-schema.md),
   explicit model settings, and a writable output directory.
3. Replace every angle-bracket placeholder.
4. Run `swuift --batch jobs.json` and accept the displayed license, or use
   `swuift --accept-license --batch jobs.json` for a non-interactive invocation.
5. Review `run_log.txt` and `run_params.json` first, then see
   [Expected outputs](outputs.md) for the remaining artifacts.

=== "venv"

    ```bash
    source .venv/bin/activate
    swuift --help
    swuift --batch jobs.json
    ```

=== "uv"

    ```bash
    uv run swuift --help
    uv run swuift --batch jobs.json
    ```

=== "Conda"

    ```bash
    conda activate swuift
    swuift --help
    swuift --batch jobs.json
    ```

## License consent

Every single, scenario, or batch simulation invocation prints the exact local
license path and SHA-256 digest, then asks:

```text
Do you accept the SWUIFT license? [y/N]
```

Only `y` or `yes` starts the run. Acceptance is not saved. Automation and other
non-interactive invocations must pass `--accept-license` each time:

```bash
swuift --accept-license --batch jobs.json
```

Read the [complete license](license.md). `--help` and `--list-timezones` are
informational and never prompt.

## Single-run structure

```bash
swuift \
  --job-name <NAME> \
  --fire-prog <PATH> --domains <PATH> --landcover <PATH> \
  --homes <PATH> --lat <PATH> --lon <PATH> \
  --harden-rad-map <PATH> --harden-spo-map <PATH> \
  --wind <PATH> \
  --grid-size 10 \
  --t-start "2021-12-30 11:00" --t-end "2021-12-30 21:00" \
  --timezone America/Denver \
  --harden-rad 70 --harden-spo 70 \
  --rad-ig-thresh 14000 --rad-decay 1.0 \
  --brand-wind-coef 30 --brand-wind-sd 0.3 \
  --brand-wind-sd-lat 4.85 \
  --seed-harden 123456 --seed-spread 10 \
  --lazy-wind \
  --output-dir <OUTPUT_DIR> \
  --frame-dpi 150 --dump-every 0 --no-dump-csv
```

Replace every placeholder. The output directory must be writable and outside
the installed CLI package tree. Add `--water <PATH>` when a non-burnable water
mask is available. If `--water` is omitted, SWUIFT uses an all-zero mask, so no
cells are marked as water.

## Required options

| Group | Options |
|---|---|
| Identity | `--job-name` |
| Inputs | `--fire-prog`, `--domains`, `--landcover`, `--homes`, `--lat`, `--lon`, `--harden-rad-map`, `--harden-spo-map`, `--wind` |
| Optional input | `--water` |
| Grid/time | `--grid-size`, `--t-start`, `--t-end`, `--timezone` |
| Model | `--harden-rad`, `--harden-spo`, `--rad-ig-thresh`, `--rad-decay`, `--brand-wind-coef`, `--brand-wind-sd`, `--brand-wind-sd-lat` |
| Reproducibility | `--seed-harden`, `--seed-spread` |
| Execution | `--lazy-wind` or `--no-lazy-wind`, `--output-dir`, `--frame-dpi`, `--dump-every`, `--dump-csv` or `--no-dump-csv` |

Accepted time syntax is `YYYY-MM-DD HH:MM`, `YYYY-MM-DDTHH:MM`, or
`YYYY-MM-DD HH:MM:SS`. Values are local wall times in the required IANA
`--timezone`. The parser does not accept a trailing `Z`, numeric offset, or
ambiguous abbreviation. SWUIFT rejects nonexistent and ambiguous
daylight-saving transition times, converts valid inputs to UTC for simulation,
and displays results in the entered timezone.

List every accepted identifier with:

```bash
swuift --list-timezones
```

The complete list is also available on the [Timezone codes](timezones.md) page.

## Output switches

| Switch pair | Default |
|---|---|
| `--out-frames` / `--no-out-frames` | on |
| `--out-video` / `--no-out-video` | on |
| `--out-gif` / `--no-out-gif` | on |
| `--out-ig-plots` / `--no-out-ig-plots` | on |
| `--out-fire-csv` / `--no-out-fire-csv` | on |
| `--out-buildings-csv` / `--no-out-buildings-csv` | on |
| `--out-rad-steps` / `--no-out-rad-steps` | off |
| `--out-spo-steps` / `--no-out-spo-steps` | off |

Video and GIF generation require frames.

## Batch mode

```bash
swuift --batch jobs.json
```

The file must contain a non-empty top-level `jobs` array. Field names are the
snake_case equivalents of CLI flags. All required single-run fields are
required in each job; `water` and output switches are optional. Omitting
`water` has the same all-zero-mask behavior as omitting `--water`.

```json
{
  "jobs": [
    {
      "name": "run_a",
      "fire_prog": "<PATH>",
      "domains": "<PATH>",
      "landcover": "<PATH>",
      "homes": "<PATH>",
      "lat": "<PATH>",
      "lon": "<PATH>",
      "harden_rad_map": "<PATH>",
      "harden_spo_map": "<PATH>",
      "water": "<PATH>",
      "wind": "<PATH>",
      "grid_size": 10,
      "t_start": "2021-12-30 11:00",
      "t_end": "2021-12-30 21:00",
      "timezone": "America/Denver",
      "harden_rad": 70,
      "harden_spo": 70,
      "rad_ig_thresh": 14000,
      "rad_decay": 1.0,
      "brand_wind_coef": 30,
      "brand_wind_sd": 0.3,
      "brand_wind_sd_lat": 4.85,
      "seed_harden": 123456,
      "seed_spread": 10,
      "lazy_wind": true,
      "output_dir": "<OUTPUT_DIR>",
      "frame_dpi": 150,
      "dump_every": 0,
      "dump_csv": false
    }
  ]
}
```

## Performance controls

`--lazy-wind` reduces memory use but increases per-step I/O. Use
`--no-lazy-wind` only when enough memory is available. To limit rendering cost,
disable video, GIF, and frames together:

```bash
--no-out-video --no-out-gif --no-out-frames
```
