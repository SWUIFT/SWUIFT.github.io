# Input schema

Every run requires nine inputs; a water mask is optional. Small arrays may be
`.mat` or comma-separated `.csv`. All provided numeric rasters must be finite
and have the same `(rows, columns)` shape as `binary_cover`.

| CLI option | `.mat` variable | Shape | Meaning |
|---|---|---|---|
| `--fire-prog` | `wildland_fire_matrix` | rows × columns | Prescribed ignition/progression grid |
| `--domains` | `domains_mat` | rows × columns | Domain classification |
| `--landcover` | `binary_cover` | rows × columns | Vegetation/structure cover |
| `--homes` | `homes_mat` | rows × columns | Structure identifiers |
| `--lat` | `lati` | rows | Latitude coordinate vector |
| `--lon` | `long` | columns | Longitude coordinate vector |
| `--harden-rad-map` | `hardening_mat_rad` | rows × columns | Radiation-hardening map |
| `--harden-spo-map` | `hardening_mat_spo` | rows × columns | Spotting-hardening map |
| `--water` (optional) | `water` | rows × columns | Non-burnable water mask; omission creates an all-zero mask (no cells marked as water) |
| `--wind` | `wind_s`, `wind_d` | time × columns × rows on disk | Wind speed and direction through time |

!!! note "Fire-progression variable names"
    The extracted-file loader expects `wildland_fire_matrix` in the selected
    file and stores it internally as the known-ignition grid. Do not rename
    variables inside a supplied bundle.

## Raster requirements

- Use one consistent grid, orientation, extent, and resolution.
- Latitude length must equal the number of rows.
- Longitude length must equal the number of columns.
- Wind slices must resolve to the same rows × columns grid.
- If provided, the water mask must match the raster grid. If omitted, SWUIFT
  uses an all-zero mask, so no cells receive the water classification.
- Prescribed ignition values must be non-negative; `0` means no prescribed
  ignition and positive values are one-based timestep indices.
- Hardening, cover, structure, domain, and water semantics must follow the
  input bundle's data dictionary.

The loader checks shape compatibility but cannot establish that layers are
geographically aligned. Visually inspect source rasters before simulation.

## Wind formats

### HDF5-backed `.mat`

The file contains `wind_s` and `wind_d`. On disk, logical
rows × columns × time arrays are exposed as time × columns × rows. SWUIFT
transposes each selected slice to rows × columns. The number of wind slices
must cover the requested inclusive simulation window.

### CSV pair

Pass a marker `.csv` path. In the same folder provide either:

- `wind_s.csv` and `wind_d.csv`; or
- `<marker_stem>_s.csv` and `<marker_stem>_d.csv`.

CSV wind input represents one timestep only and both arrays must match the
raster grid.

## Time indexing

SWUIFT uses fixed-duration timesteps. A start and end time are inclusive, so a
ten-hour window at five-minute spacing contains **121 states**: the initial
state plus 120 transitions.

For a start, end, and fixed timestep, the inclusive state count is:

`state count = duration / timestep + 1`

Start and end must fall on five-minute boundaries and the duration must be
divisible by five minutes. The Marshall tutorial uses ten hours:
`600 / 5 + 1 = 121` states.

Every run must also provide an [IANA timezone](timezones.md). SWUIFT interprets
the entered timestamps in that zone, rejects ambiguous or nonexistent
daylight-saving wall times, then converts the interval to UTC before calculating
states and indexing wind. Input wind slice zero remains simulation state one.

## Data provenance

For reproducible work, record:

- input bundle name and version;
- source and access date;
- SHA-256 digest for every file;
- coordinate reference system and grid resolution;
- any preprocessing performed before SWUIFT;
- software version and full commit SHA.
