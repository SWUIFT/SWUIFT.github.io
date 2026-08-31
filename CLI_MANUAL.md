# SWUIFT CLI Manual

The `swuift` command runs one explicit simulation or a sequential JSON batch.

## Install

Python 3.10 or newer is required. From the repository root, choose venv, uv,
or Conda:

### venv

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-cli.txt
swuift --help
```

### uv

```bash
uv venv --python 3.12
uv pip install -r requirements-cli.txt
uv run swuift --help
```

Use `uv run swuift ...` for subsequent commands.

### Conda

```bash
conda env create -f environment.yml
conda activate swuift
swuift --help
```

## Run

Single-run mode requires a job name, nine input paths, model parameters, seeds,
wind-loading choice, and output controls. The water mask is optional:

```bash
swuift \
  --job-name <NAME> \
  --fire-prog <PATH> --domains <PATH> --landcover <PATH> \
  --homes <PATH> --lat <PATH> --lon <PATH> \
  --harden-rad-map <PATH> --harden-spo-map <PATH> \
  --wind <PATH> \
  --grid-size 10 \
  --t-start "2021-12-30 11:00" \
  --t-end "2021-12-30 21:00" \
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

Add `--water <PATH>` when a non-burnable water mask is available. Omitting it
creates an all-zero mask, so no cells are marked as water. The `water` field is
likewise optional in batch JSON.

Every simulation invocation prints the exact local license path and SHA-256
digest and asks `Do you accept the SWUIFT license? [y/N]`. Only `y` or `yes`
continues, and acceptance is not saved. Non-interactive runs must include
`--accept-license` every time, for example
`swuift --accept-license --batch jobs.json`. Help and timezone-listing commands
do not prompt. Read the [complete license](LICENSE).

Replace all angle-bracket placeholders. The CLI accepts
`YYYY-MM-DD HH:MM`, `YYYY-MM-DDTHH:MM`, or `YYYY-MM-DD HH:MM:SS` as local wall
time. A separate IANA `--timezone` is required; list every accepted code with
`swuift --list-timezones`. Both endpoints must align to five-minute boundaries.
SWUIFT converts them to UTC for simulation and localizes displayed results.

Batch mode reads a non-empty top-level `jobs` array:

```bash
swuift --batch jobs.json
```

The output directory must be writable and outside the installed CLI package
tree. Every run writes `run_log.txt` and `run_params.json`; maps, tables,
frames, animations, and per-step diagnostics depend on output switches.

## Complete documentation

- [CLI options and JSON schema](docs/cli.md)
- [Input schema](docs/input-schema.md)
- [Supported timezone codes](docs/timezones.md)
- [Marshall 121-state tutorial](docs/marshall-tutorial.md)
- [Expected outputs](docs/outputs.md)
- [Troubleshooting and contact](docs/troubleshooting.md)

SWUIFT is source-available under a restrictive research and academic use
license. See [citation and license guidance](docs/citation-license.md).
