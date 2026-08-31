> **Canonical CLI manual:** see [CLI_MANUAL.md](../../CLI_MANUAL.md) at the repo root.
>
> **License:** [SWUIFT Research and Academic Use License](../../LICENSE) — University at Buffalo. Commercial inquiries: Prof. Negar Elhami-Khorasani, `negarkho@buffalo.edu`.

![SWUIFT Banner](./SWUIFT%20LOGO.png)

# SWUIFT

**Streamlined Wildland-Urban Interface Fire Tracing**

SWUIFT models fire spread within wildland-urban interface (WUI) and urban
communities using a semi-empirical approach. A **three-domain** solution is
utilized, defining wildland, transition and community domains following the
neighbourhood-based housing density (NBHD) method. Near- and far-field
transport mechanisms are captured, including thermal radiation and fire
spotting. SWUIFT considers urban and vegetative fuels and wind, and tracks fire
progression at a 10-meter resolution. Offline coupling with wildland fire
spread simulators is supported. Utilize the desktop application for an
interactive workflow or the command-line (CLI) for scripted and batch runs.

SWUIFT simulation results depend on input quality and modelling assumptions.
Analysis of results should rely on expert interpretation.

# SWUIFT User Manual

This guide is written for users who want to run SWUIFT experiments from a terminal, including users with limited programming background.

The workflow supports:
- Single-run execution from CLI
- Multi-run sequential experiments from JSON
- Full run metadata logging for reproducibility

Every simulation invocation displays the bundled license path and digest and
requires `y`/`yes` acceptance. Acceptance is not saved. Redirected,
non-interactive, and automated runs must pass `--accept-license` each time,
for example `swuift --accept-license --batch jobs_example.json`.

## 1) What You Need

- A Linux machine, macOS machine, or Windows machine with terminal access
- Python 3.10 or newer
- Access to SWUIFT input files in `.mat` and/or `.csv` format
- A writable external output location **outside this project folder**

## 2) Choose an Environment Manager

SWUIFT supports Python `venv`, uv, and Conda. The canonical setup commands are
in the repository's [CLI manual](../../CLI_MANUAL.md) and
[installation guide](../../docs/installation.md).

## 3) Go to the Repository Root

```bash
cd /path/to/SWUIFT
pwd
```

Confirm that this directory contains `requirements-cli.txt` and
`environment.yml`.

## 4) Create the Environment and Install

### venv — Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-cli.txt
```

### venv — Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-cli.txt
```

### uv

```bash
uv venv --python 3.12
uv pip install -r requirements-cli.txt
```

Use `uv run swuift ...` for CLI commands, or activate `.venv`.

### Conda

```bash
conda env create -f environment.yml
conda activate swuift
```

## 5) Verify Installation

For venv or Conda:

```bash
swuift --help
```

For uv:

```bash
uv run swuift --help
```

Check key packages:

```bash
python -c "import numpy, scipy, h5py, numba, matplotlib, tqdm, imageio, imageio_ffmpeg, av, PIL; print('OK')"
```

If you see `OK`, installation is successful.

## 6) Run the Environment Smoke Simulation

The repository includes a synthetic one-step simulation that verifies the CLI
entry point, data loading, simulation loop, and required output files:

```bash
python scripts/smoke_test_cli_environment.py
```

With uv, use `uv run python scripts/smoke_test_cli_environment.py`.

## 7) Important Rule: Output Directory Must Be Outside Project

`output_dir` is required for every run and must be outside this repository.

Examples:
- Good: `/mnt/swuift_runs`
- Good: `/home/user/experiments/swuift_out`
- Bad: `./outputs` (inside project)

If you use an inside-project path, SWUIFT now throws an explicit error.

## 8) Run a Single Experiment from CLI

Use full explicit arguments:

```bash
swuift \
  --job-name baseline \
  --fire-prog extracted_mat/eaton/wildland_fire_matrix.mat \
  --domains extracted_mat/eaton/domain_matrix.mat \
  --landcover extracted_mat/eaton/binary_cover_landcover.mat \
  --homes extracted_mat/eaton/homes_matrix.mat \
  --lat extracted_mat/eaton/latitude.mat \
  --lon extracted_mat/eaton/longitude.mat \
  --harden-rad-map extracted_mat/eaton/radiation_matrix.mat \
  --harden-spo-map extracted_mat/eaton/spotting_matrix.mat \
  --water extracted_mat/eaton/water_matrix.mat \
  --wind extracted_mat/eaton/wind.mat \
  --grid-size 10 \
  --t-start "2025-01-07 18:20" \
  --t-end "2025-01-08 14:20" \
  --timezone America/Los_Angeles \
  --harden-rad 70 \
  --harden-spo 70 \
  --rad-ig-thresh 14000.0 \
  --rad-decay 1.0 \
  --brand-wind-coef 30.0 \
  --brand-wind-sd 0.3 \
  --brand-wind-sd-lat 4.85 \
  --seed-harden 123456 \
  --seed-spread 10 \
  --no-lazy-wind \
  --output-dir /mnt/swuift_runs \
  --frame-dpi 300 \
  --dump-every 0 \
  --no-dump-csv
```

`--water` is optional. If it is omitted, SWUIFT creates an all-zero water mask,
so no cells are marked as water.

## 9) Run Multiple Experiments from JSON

A ready example file is included at:

- `jobs_example.json`

Run it:

```bash
swuift --batch ./jobs_example.json
```

The `water` field is optional in each JSON job and has the same all-zero-mask
default when omitted.

## 10) JSON File Format (Sequential Jobs)

Top-level key must be `jobs`, containing an array:

```json
{
  "jobs": [
    {
      "name": "baseline",
      "fire_prog": "extracted_mat/eaton/wildland_fire_matrix.mat",
      "domains": "extracted_mat/eaton/domain_matrix.mat",
      "landcover": "extracted_mat/eaton/binary_cover_landcover.mat",
      "homes": "extracted_mat/eaton/homes_matrix.mat",
      "lat": "extracted_mat/eaton/latitude.mat",
      "lon": "extracted_mat/eaton/longitude.mat",
      "harden_rad_map": "extracted_mat/eaton/radiation_matrix.mat",
      "harden_spo_map": "extracted_mat/eaton/spotting_matrix.mat",
      "water": "extracted_mat/eaton/water_matrix.mat",
      "wind": "extracted_mat/eaton/wind.mat",
      "grid_size": 10,
      "t_start": "2025-01-07 18:20",
      "t_end": "2025-01-08 14:20",
      "timezone": "America/Los_Angeles",
      "harden_rad": 70.0,
      "harden_spo": 70.0,
      "rad_ig_thresh": 14000.0,
      "rad_decay": 0.9,
      "brand_wind_coef": 30.0,
      "brand_wind_sd": 0.3,
      "brand_wind_sd_lat": 4.85,
      "seed_harden": 123456,
      "seed_spread": 10,
      "lazy_wind": false,
      "output_dir": "/mnt/swuift_runs",
      "frame_dpi": 300,
      "dump_every": 0,
      "dump_csv": false,
      "out_frames": true,
      "out_video": true,
      "out_gif": true,
      "out_ig_plots": true,
      "out_fire_csv": true,
      "out_buildings_csv": true,
      "out_rad_steps": false,
      "out_spo_steps": false
    }
  ]
}
```

Notes:
- `t_start` and `t_end` are local wall times in the required IANA `timezone`.
  Run `swuift --list-timezones` for every supported identifier.
- SWUIFT converts the interval to UTC, then automatically derives 5-minute
  simulation states. Displayed result times use the entered timezone.
- If `t_start` or `t_end` is not quantized to a 5-minute boundary, SWUIFT raises:
  `not possible to calculate integer time steps`.
- Any non-wind input can be either `.mat` or `.csv` (mixed formats are allowed).
- For wind CSV mode, pass `--wind /path/to/wind.csv` and place companion files in the same directory:
  `wind_s.csv` + `wind_d.csv` (or `<wind_stem>_s.csv` + `<wind_stem>_d.csv`).

## 11) Output Controls

Defaults:
- `out_frames`, `out_video`, `out_gif`, `out_ig_plots`, `out_fire_csv`, `out_buildings_csv`: `true`
- `out_rad_steps`, `out_spo_steps`: `false`

You can disable outputs per job (JSON) or with CLI flags such as `--no-out-video`.

## 12) What Gets Saved Per Run

Each job creates:

```text
<output_dir>/<job_name>_<YYYYMMDD_HHMMSS>/
```

Always saved:
- `run_log.txt` (full console log + full command line)
- `run_params.json` (all options selected + timing + metadata)

Optional (based on output flags):
- `frames/`
- `simulation.mp4`
- `simulation.gif`
- `ig_pixel.png`
- `ig_structure.png`
- `fire_prog.csv`
- `zvector.csv`
- `timesteps/` (state/rad/spo step files)

## 13) Running in Background (`nohup`) on Linux

### Single-run nohup

```bash
nohup swuift --job-name baseline ... --output-dir /mnt/swuift_runs > /mnt/swuift_runs/nohup_single.log 2>&1 &
```

### Batch-run nohup

```bash
nohup swuift --accept-license --batch ./jobs_example.json > /mnt/swuift_runs/nohup_batch.log 2>&1 &
```

Monitor progress:

```bash
tail -f /mnt/swuift_runs/nohup_batch.log
```

See background jobs:

```bash
jobs -l
```

Find process:

```bash
ps -ef | grep swuift | grep -v grep
```

## 14) Basic Troubleshooting

- `swuift: command not found`:
  - Activate virtual environment and reinstall with `pip install -e .`
- Missing package error:
  - Re-run `pip install -e .`
- Output directory error:
  - Set `output_dir` to a path outside the project (absolute path recommended)
- JSON validation error:
  - Check job name and missing fields listed in the error

## 15) Recommended Team Workflow

- Keep dataset files outside the repository
- Keep output directory on high-capacity storage
- Use JSON batch files for reproducible experiment sets
- Archive each run folder (`run_log.txt` + `run_params.json`) for auditability

## 16) Kernel Environment Variables

Both the CLI and the shared `swuift_core` physics package honor:

| Variable | Default | Description |
|----------|---------|-------------|
| `SWUIFT_APP_KERNEL_BACKEND` | `numba` | Set to `python` to force pure-Python kernels (useful for debugging or frozen builds) |
| `SWUIFT_APP_RADIATION_WORKERS` | `1` | Number of processes for parallel radiation chunking on multi-core hosts |

Example:

```bash
export SWUIFT_APP_RADIATION_WORKERS=4
export SWUIFT_APP_KERNEL_BACKEND=numba
swuift --job-name baseline ...
```

