# swuift-core

Shared physics package for SWUIFT (Streamlined Wildland-Urban Interface Fire Tracing).

Contains the canonical simulation kernels used by the desktop app and CLI:

- `kernels.py` — Numba JIT with Python fallback
- `spread.py` — brand generation/transport, full-grid radiation, ignition
- `hardening.py` — structure hardening initialization
- `config.py` — canonical `SWUIFTConfig` dataclass

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SWUIFT_APP_KERNEL_BACKEND` | `numba` | Set to `python` to force pure-Python kernels |
| `SWUIFT_APP_RADIATION_WORKERS` | `1` | Process count for parallel radiation chunking |

## Install

```bash
cd doe-wildfire/packages/core
pip install -e .
```
