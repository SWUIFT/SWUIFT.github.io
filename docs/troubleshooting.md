# Troubleshooting and contact

## Installation

**`swuift: command not found`**

Activate the environment used for installation, then reinstall from the
versioned source root if necessary:

=== "venv"

    ```bash
    source .venv/bin/activate
    python -m pip install -r requirements-cli.txt
    swuift --help
    ```

    On PowerShell, activate with `.\.venv\Scripts\Activate.ps1`.

=== "uv"

    ```bash
    uv pip install -r requirements-cli.txt
    uv run swuift --help
    ```

=== "Conda"

    ```bash
    conda activate swuift
    python -m pip install -e packages/core -e packages/cli
    swuift --help
    ```

If the console script is still unavailable, verify the package in the active
environment with `python -m swuift --help`.

**The desktop application does not open**

Verify the package first. On source installations, launch from a terminal to
see the error:

```bash
cd apps/desktop
python swuift_app.py
```

Confirm the platform and architecture match the downloaded package.

## Inputs and time

**Missing or invalid input files**

All nine required paths must exist and be readable. A supplied water-mask path
must also be valid, but the water input may be omitted. Confirm internal
variable names and formats against [Input schema](input-schema.md).

**Incompatible shape**

All rasters must use one rows × columns grid; latitude length equals rows and
longitude length equals columns. Confirm layer orientation and preprocessing.

**Wind timestep is out of range**

The wind file does not cover the requested inclusive state count. Shorten the
window only when scientifically appropriate or obtain the complete bundle.

**Integer timestep or time-alignment error**

Start and end must be on five-minute boundaries and the duration must be
divisible by five minutes after conversion from the required IANA timezone to
UTC. Do not append `Z` or a numeric offset; provide `--timezone` separately.

**Unknown, ambiguous, or nonexistent timezone value**

Use an exact identifier from `swuift --list-timezones` or the
[Timezone codes](timezones.md) page. Abbreviations such as `CST` are ambiguous.
During daylight-saving transitions, choose a different unambiguous wall time;
SWUIFT will not guess which instant was intended.

## Runtime and outputs

**Out of memory while loading wind**

Enable **Lazy Wind** in the GUI or pass `--lazy-wind` to the CLI. Close other
memory-intensive applications.

**Run is slow**

Large grids, lazy wind I/O, high-DPI frames, animations, and per-step exports
increase runtime. Disable unneeded outputs. Do not alter the scientific window
only to improve speed without documenting the change.

**Video or GIF is missing**

Frames must be enabled for animation generation. Confirm there is enough disk
space and inspect `run_log.txt` for encoder errors. Desktop installers include
the required encoders; users should not need to install `ffmpeg` separately.

**Output folder rejected**

Choose a writable directory outside the installed CLI package tree. Prefer a
dedicated results folder with ample free space.

**A GUI job failed**

Open the failed queue entry to view details, then inspect `run_log.txt`. Keep
the log, `run_params.json`, software version, and input checksums when asking
for help.

## Contact

For scientific questions:

- Prof. Negar Elhami-Khorasani
- Email: `negarkho@buffalo.edu`

For commercial licensing, email `techtransfer@buffalo.edu`.

For software issues, open a GitHub issue at
[SWUIFT/SWUIFT.github.io](https://github.com/SWUIFT/SWUIFT.github.io/issues). Do not attach
restricted input data. Include:

1. SWUIFT version and full commit SHA;
2. operating system and architecture;
3. GUI or CLI;
4. exact command or relevant settings, with sensitive paths removed;
5. the error text and the relevant portion of `run_log.txt`;
6. input shapes and checksums, but not restricted files.
