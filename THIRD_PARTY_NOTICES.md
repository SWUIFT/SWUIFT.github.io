# Third-Party Notices

SWUIFT depends on third-party software distributed under its own terms. Those
terms apply independently of the SWUIFT license. This inventory covers direct
runtime dependencies declared by the public packages and desktop environment;
transitive dependencies must also be reviewed for each release.

- NumPy — BSD 3-Clause
- SciPy — BSD 3-Clause
- h5py — BSD 3-Clause
- Numba — BSD 2-Clause
- Matplotlib — Matplotlib license (PSF-based)
- ImageIO — BSD 2-Clause
- imageio-ffmpeg / FFmpeg binaries — license depends on the distributed FFmpeg
  build; commonly LGPL or GPL
- tqdm — MPL 2.0 and MIT
- PyAV — BSD 3-Clause
- PySide6 / Qt — LGPLv3, GPLv3, or applicable commercial terms, depending on
  use and distribution
- Pillow — HPND
- tzdata (Python package) — Apache License 2.0; bundled IANA timezone database
  files remain subject to their upstream notices

Development and build tools are not part of the SWUIFT runtime distribution
unless a release artifact bundles them.

Before publishing a binary release, generate a dependency inventory from the
final environment, preserve all notices required by the resolved versions, and
confirm that the chosen Qt and FFmpeg distributions are compatible with the
intended distribution model. Package names and license metadata should be
verified against the exact artifacts installed for that release.
