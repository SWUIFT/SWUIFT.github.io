# Expected outputs

Each CLI job creates:

```text
<OUTPUT_DIR>/<JOB_NAME>_YYYYMMDD_HHMMSS/
```

Desktop runs create a timestamped run folder under the selected output folder.
Treat directory timestamps as labels, not stable identifiers.

## Core records

| Path | Purpose |
|---|---|
| `run_log.txt` | Console messages, progress, warnings, and elapsed time |
| `run_params.json` | Inputs, command, model settings, output switches, timing, grid shape, and job specification |

Review and preserve these records for every run.

Simulation timestamps are computed in UTC. Logs, frame titles, and plot labels
use the timezone selected by the user. Metrics retain the legacy UTC
`sim_time` field and add explicit `sim_time_utc`, `sim_time_local`,
`sim_time_timezone`, and `sim_time_offset` fields. `run_params.json` records
both UTC and localized simulation bounds.

## Standard scientific outputs

| Path | Contents |
|---|---|
| `fire_prog.csv` | Final fire-progression matrix |
| `zvector.csv` | Structure ignition summary |
| `ig_pixel.png` | Pixel-level ignition visualization |
| `ig_structure.png` | Structure-level ignition visualization |

## Visual outputs

| Path | Condition |
|---|---|
| `frames/0001.png`, … | Frame output enabled |
| `simulation.mp4` | Video and frame output enabled |
| `simulation.gif` | GIF and frame output enabled |

Frame count and naming may reflect renderer conventions. Use
`run_params.json`, not filenames alone, to establish the requested inclusive
state count.

## Optional diagnostics

| Path | Condition |
|---|---|
| `timesteps/rad_000001.csv`, … | Per-step radiation export enabled |
| `timesteps/spo_000001.csv`, … | Per-step spotting export enabled |
| `timesteps/t000001/` | Full state dump interval is greater than zero |
| `frame_state/state_XXXX.npy` | Normalized frame-state emission enabled |
| `frame_csvs/XXXX.csv` | Desktop frame-state CSV emission |
| `radiation_csv/XXXX.csv` | Desktop radiation CSV enabled |
| `spotting_csv/XXXX.csv` | Desktop spotting CSV enabled |

Full state dumps contain fire, ignition, radiation, output-fire, and structure
state arrays as `.npy` or `.csv`, depending on configuration. These artifacts
can be large.

## Marshall completion checklist

For the tutorial window, confirm:

1. `run_log.txt` ends with successful completion.
2. `run_params.json` reports the intended start, end, and `max_steps: 121`.
3. The recorded input paths and grid shape match the authorized Marshall bundle.
4. Requested maps, tables, frames, and animations exist.
5. No output file is zero bytes or unexpectedly truncated.

Do not interpret the presence of a file as scientific validation. Review input
provenance, configuration, model assumptions, and domain suitability.
