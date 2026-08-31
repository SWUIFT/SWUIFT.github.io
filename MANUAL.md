# SWUIFT Desktop Manual

SWUIFT's desktop application provides six configuration tabs, a live log, and
a sequential job queue.

## Install and launch

Use a verified packaged build from [Downloads](docs/downloads.md), or install a
versioned source checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd apps/desktop
python swuift_app.py
```

Platform-specific steps are in the [install and verify guide](docs/installation.md).
Every launch displays the complete [SWUIFT license](LICENSE) and its exact local
path. Choose **I Agree** to open the main window. Acceptance is not saved;
declining or closing the dialog exits the application.

## Run a simulation

1. On **Data Inputs**, select the nine required files. The water matrix is
   optional; leaving it blank means no cells are marked as water.
2. On **Grid & Time**, select a required IANA timezone and enter inclusive
   local start and end times aligned to five-minute boundaries. Confirm the UTC
   preview before queueing the job.
3. Configure radiation, firebrands, hardening, and random-number seeds.
4. On **Output Settings**, choose a writable output directory and requested
   artifacts.
5. Click **Add to Queue**.
6. Click **Run All** and monitor the status, phase, progress, and log.
7. When the job is **Done**, open its output directory and review
   `run_params.json` and `run_log.txt`.

Enable **Lazy Wind** to reduce memory use. Save reusable configurations with
**File → Save Settings as JSON…** and restore them with **File → Load Settings
from JSON…**.

## Marshall walkthrough

For the 121-state window from `2021-12-30T18:00Z` through
`2021-12-31T04:00Z`—11:00 through 21:00 MST—follow the
[Marshall tutorial](docs/marshall-tutorial.md).

## Complete documentation

- [Desktop GUI controls](docs/gui.md)
- [Input schema](docs/input-schema.md)
- [Supported timezone codes](docs/timezones.md)
- [Expected outputs](docs/outputs.md)
- [Troubleshooting and contact](docs/troubleshooting.md)
- [Research and academic use license](docs/citation-license.md)
- [Complete license text](docs/license.md)

