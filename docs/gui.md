# Desktop GUI

The desktop application combines six configuration tabs, a live simulation
log, and a sequential job queue.

You need a complete, licensed SWUIFT input bundle before beginning. The
software distribution does not imply redistribution rights for third-party
geospatial or wind data.

## License consent at launch

Every launch begins with a modal dialog containing the complete
[SWUIFT license](license.md), its exact local file path, and **I Agree** /
**Decline and Exit** controls. Acceptance is never stored. Declining, closing
the dialog, or a missing license exits before the main window appears.

## Standard workflow

1. Open **SWUIFT - WUI fire spread simulation**.
2. Read the full license shown at startup and choose **I Agree** to continue.
   Acceptance is required on every launch and is not saved.
3. On **Data Inputs**, select the nine required files described in the
   [input schema](input-schema.md). Add a water mask when available.
4. On **Grid & Time**, select the required [IANA timezone](timezones.md), then
   enter local start and end values aligned to five-minute boundaries.
5. Configure the model and choose a writable folder on **Output Settings**.
   Enable **Lazy Wind** when memory is limited.
6. Click **Add to Queue** to snapshot the settings. Add more parameter variants
   if needed, then click **Run All**.

The queue progresses through loading, configuration, simulation, and optional
video generation. When the status is **Done**, use the output directory shown
in the queue.

## Configuration tabs

### Data Inputs

Select the nine required `.mat` or `.csv` inputs. The water matrix is optional:
leaving it blank creates an all-zero mask, so no cells are marked as water.
The GUI validates every path that is supplied before a job can be queued. See
[Input schema](input-schema.md).

### Grid & Time

Start and end are inclusive. Both must align to the fixed five-minute timestep.
Select a required IANA timezone from the searchable list; the date/time fields
are interpreted as local wall times in that zone. The panel previews the UTC
conversion, duration, and calculated number of states. Invalid, ambiguous, and
nonexistent daylight-saving times cannot be queued. See
[Timezone codes](timezones.md).

### Radiation

- **Ignition Threshold (W/m²):** radiant-energy threshold for ignition.
- **Radiation Reduction Factor:** multiplier applied before the ignition check;
  `1.0` means no reduction.

### Firebrands

The wind coefficient and longitudinal/transverse standard deviations control
wind-driven transport and stochastic scatter.

### Hardening & Seeds

Radiation and spotting hardening are percentages. Random-number seeds make a
configuration reproducible when software, inputs, and platform are also held
constant. Record both seeds in publications.

### Output Settings

- **Output Folder:** base folder for timestamped run directories.
- **Generate Video / GIF:** creates animations after simulation.
- **Frame DPI:** resolution of rendered frames.
- **Dump Interval:** saves full state every N steps; `0` disables dumps.
- **Dump as CSV:** human-readable dumps, typically larger and slower.
- **Lazy Wind:** lowers memory use by reading wind slices on demand.
- **Radiation/spotting CSV:** optional per-step diagnostic exports.

## Queue controls

| Control | Effect |
|---|---|
| **Add to Queue** | Validate and snapshot the current configuration |
| **Run All** | Run pending jobs sequentially |
| **Cancel** | Stop the current job or queue after confirmation |
| **Remove Selected** | Remove a pending job |
| **Duplicate Selected** | Copy a job for a parameter variant |
| **Clear Queue** | Remove jobs when no simulation is active |

The queue reports status, phase, elapsed time, estimated remaining time, and
the run output directory. A failed row can be opened to view its error.

## Save and restore settings

Use **File → Save Settings as JSON…** (`Ctrl+S`) and **File → Load Settings
from JSON…** (`Ctrl+O`). Saved settings contain paths and model parameters, but
not the input files themselves. Review paths after moving a settings file to
another computer.

## Reproducibility checklist

- Keep the released software version and full commit SHA.
- Keep the input-bundle identifier and checksums.
- Save the settings JSON.
- Preserve `run_params.json` and `run_log.txt`.
- Record platform, timezone, seed values, and whether lazy wind was enabled.
