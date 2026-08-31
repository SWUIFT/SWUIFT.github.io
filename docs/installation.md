# Install and verify

Download packages from [Downloads](downloads.md), verify the SHA-256 digest,
then install. Read the [complete SWUIFT license](license.md) before running.

Desktop releases are published for **Windows x64** and **macOS** (Apple silicon
and Intel). Linux users install and run the **CLI from source**.

## 1. Verify the download (SHA-256)

A matching digest means your file is byte-identical to the release asset. Compare
**all 64 hexadecimal characters** (case does not matter). Do not install if the
hash differs by even one character.

### Expected digests (v1.0.0)

| File | Expected SHA-256 |
|---|---|
| `SWUIFT_Setup_1.0.0.exe` | `REPLACE_AFTER_BUILD` |
| `SWUIFT_macOS_arm64.dmg` | `REPLACE_AFTER_BUILD` |
| `SWUIFT_macOS_x86_64.dmg` | `REPLACE_AFTER_BUILD` |
| `marshall_20211230_1100-2100_MST-inputs.tar.gz` | `REPLACE_AFTER_BUILD` |
| `marshall_20211230_1100-2100_MST-output.tar.gz` | `REPLACE_AFTER_BUILD` |

The same values appear in the SHA-256 column on [Downloads](downloads.md).
For Python wheels and source distributions, use
[SHA256SUMS](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/SHA256SUMS)
from the [v1.0.0 release](https://github.com/SWUIFT/SWUIFT.github.io/releases/tag/v1.0.0).

### Compute the hash

Open a terminal in the folder that contains the downloaded file.

=== "Linux"

    ```bash
    sha256sum SWUIFT_Setup_1.0.0.exe
    ```

    Example:

    ```text
    REPLACE_AFTER_BUILD  SWUIFT_Setup_1.0.0.exe
    ```

    The left field must match the table above. For Python packages listed in
    `SHA256SUMS`:

    ```bash
    sha256sum --check SHA256SUMS
    ```

    Every checked line should end with `OK`.

=== "macOS"

    ```bash
    shasum -a 256 SWUIFT_macOS_arm64.dmg
    ```

    Compare the printed 64-character hash to the expected value for that file.

=== "Windows (PowerShell)"

    ```powershell
    Get-FileHash .\SWUIFT_Setup_1.0.0.exe -Algorithm SHA256
    ```

    Compare the `Hash` field to the expected digest for that installer.

If verification fails, delete the file, download again from the official
release, and contact the maintainers if the mismatch persists. A checksum
proves file identity, not that the software is safe for a particular use.

## 2. Install the desktop app

### Windows (x64)

1. Download `SWUIFT_Setup_1.0.0.exe` from [Downloads](downloads.md) and verify
   its digest above.
2. Double-click the installer and follow the prompts.
3. Launch **SWUIFT** from the Start menu.

Windows may show a SmartScreen reputation warning for newly published
installers. Confirm the filename and verified digest before continuing.

### macOS

1. Download the `.dmg` that matches your Mac (Apple silicon arm64 or Intel
   x86_64) from [Downloads](downloads.md) and verify its digest above.
2. Open the disk image and drag **SWUIFT.app** to **Applications**.
3. Open **SWUIFT** from Applications.

If macOS blocks first launch, open **System Settings → Privacy & Security**
and review the message. Proceed only after the digest matches.

## 3. Install the CLI from source

Python **3.10 or newer** is required. Use a fresh isolated environment for each
SWUIFT version. The CLI works with Python `venv`,
[uv](https://docs.astral.sh/uv/), or Conda. Linux is CLI-only; no Linux desktop
build is published.

### Get the source

Either download the release source archive or clone the repository, then change
into the project root (the directory that contains `requirements.txt`).

=== "Download source archive"

    1. Download
       [Source code (zip)](https://github.com/SWUIFT/SWUIFT.github.io/archive/refs/tags/v1.0.0.zip)
       from the [v1.0.0 release](https://github.com/SWUIFT/SWUIFT.github.io/releases/tag/v1.0.0)
       (or the matching tarball).
    2. Extract it and enter the directory:

    ```bash
    unzip SWUIFT.github.io-1.0.0.zip
    cd SWUIFT.github.io-1.0.0
    ```

=== "Clone the repository"

    ```bash
    git clone https://github.com/SWUIFT/SWUIFT.github.io.git
    cd SWUIFT.github.io
    git checkout v1.0.0
    ```

    Use `v1.0.0` for a reproducible release checkout, or stay on `main` only if
    you intentionally want the latest development tip.

### Create the environment and install

Run these commands from the project root. `requirements-cli.txt` installs only
the CLI and simulation core; it does not install the desktop application's
PySide6 dependency.

=== "venv — Linux / macOS"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements-cli.txt
    swuift --help
    ```

=== "venv — Windows"

    ```powershell
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements-cli.txt
    swuift --help
    ```

=== "uv"

    Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

    ```bash
    uv venv --python 3.12
    uv pip install -r requirements-cli.txt
    uv run swuift --help
    ```

    Prefix later commands with `uv run`, for example
    `uv run swuift --batch jobs.json`. You may instead activate `.venv` and use
    `swuift` directly.

=== "Conda"

    The included `environment.yml` installs FFmpeg from conda-forge and the
    local SWUIFT packages with pip:

    ```bash
    conda env create -f environment.yml
    conda activate swuift
    swuift --help
    ```

    Recreate the environment after switching SWUIFT versions:
    `conda env remove -n swuift`, then run `conda env create` again.

### Run an installation smoke test

From the project root, verify the selected environment with a one-step
synthetic simulation:

```bash
python scripts/smoke_test_cli_environment.py
```

For uv without activation, run
`uv run python scripts/smoke_test_cli_environment.py`. A successful test ends
with `SWUIFT environment smoke simulation passed.` and verifies that the CLI
created both `run_log.txt` and `run_params.json`.

## License file locations

- Source checkouts: `LICENSE` at the repository root.
- Installed Python wheels: under
  `swuift-<version>.dist-info/licenses/LICENSE`.
- Desktop bundles: `LICENSE` inside the application resources.

The desktop startup dialog and CLI prompt show the absolute path used on the
current machine. SWUIFT will not run if that file is missing or unreadable.
