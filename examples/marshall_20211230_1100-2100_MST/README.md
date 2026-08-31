# Marshall 2021-12-30 11:00–21:00 MST

This is a Python-only, 121-timestep Marshall input example. The 5-minute
timesteps are inclusive from `2021-12-30T18:00:00Z` through
`2021-12-31T04:00:00Z` (11:00–21:00 MST).
Enter `2021-12-30 11:00` through `2021-12-30 21:00` with the required IANA
timezone `America/Denver`; SWUIFT converts that interval to UTC internally.

## Citation

Fernando Szasdi-Bardales, Kasra Shamsaei, Timothy W. Juliano, Branko Kosovic,
Hamed Ebrahimian, and Negar Elhami-Khorasani. “An offline coupling of fire
spread models to simulate the 2021 Marshall Fire.” *International Journal of
Wildland Fire* 34, no. 1 (2025): WF24027. ISSN 1049-8001.
[https://doi.org/10.1071/WF24027](https://doi.org/10.1071/WF24027).

See the documentation's
[Marshall citation and BibTeX](https://swuift.github.io/citation-license/#marshall-example).

Binary inputs are generated under the Git-ignored
`examples/artifacts/marshall_20211230_1100-2100_MST/` directory. The example
contains one HDF5 wind file, `wind.mat`, holding both `wind_s` and `wind_d`.
Ignition values for source timesteps 122–144 are set to zero because they are
outside this package's time window. The exact count is recorded in
`provenance.json`.

## Published archives (v1.0.0)

Separate input and output archives are committed under
[`examples/artifacts/`](https://github.com/SWUIFT/SWUIFT.github.io/tree/main/examples/artifacts)
and attached to the GitHub release linked from
[Downloads](https://swuift.github.io/downloads/):

| Archive | Download | SHA-256 |
|---|---|---|
| Inputs | [marshall_20211230_1100-2100_MST-inputs.tar.gz](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/marshall_20211230_1100-2100_MST-inputs.tar.gz) | `3a0f719dd7747e11849b192cf6a28b12ae2ddaebccfa9189d8f922d083a64f8b` |
| Outputs | [marshall_20211230_1100-2100_MST-output.tar.gz](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/marshall_20211230_1100-2100_MST-output.tar.gz) | `f5e244562223bace9da1b29ac605b3950f46af958a8557d03a3f1d661afb993a` |

```bash
tar -xzf marshall_20211230_1100-2100_MST-inputs.tar.gz
# use ./marshall_20211230_1100-2100_MST as --data-root
```

## Prepare and package

Run from the repository root:

```bash
python scripts/prepare_marshall_example.py
python scripts/package_marshall_example.py
python scripts/package_marshall_example.py --verify-only
```

The packaging command writes `input-checksums.sha256` here and creates the
reproducible archive
`examples/artifacts/marshall_20211230_1100-2100_MST-inputs.tar.gz`. Verification is
read-only and checks staging files, the single `wind.mat` representation,
metadata checksums, and every archived member.

## Reproducible CLI command

Install the public packages as described in the CLI documentation, then run:

```bash
swuift \
  --manifest examples/marshall_20211230_1100-2100_MST/manifest.json \
  --data-root examples/artifacts/marshall_20211230_1100-2100_MST \
  --output-dir /tmp/swuift-marshall-example \
  --lazy-wind \
  --no-out-frames \
  --no-out-video \
  --no-out-gif \
  --no-out-ig-plots \
  --checkpoint-every 0
```

The command displays the local license path and prompts for acceptance before
loading the example. For a non-interactive reproduction, add
`--accept-license`; acceptance applies only to that invocation.

The simulation is intentionally not run by the preparation or packaging
scripts. `manifest.json` is directly consumable by the public scenario CLI;
`provenance.json` documents source hashes and transformations without recording
machine-specific absolute paths.

## Validated output artifact

The completed 121-step public run can be prepared and packaged with:

```bash
python scripts/prepare_marshall_output.py
python scripts/package_marshall_output.py
python scripts/package_marshall_output.py --verify-only
```

Tracked `output-manifest.json`, `output-provenance.json`,
`output-summary.json`, and `output-checksums.sha256` describe the sanitized
output. Binary scientific outputs and representative PNGs are staged under
`examples/artifacts/marshall_20211230_1100-2100_MST-output/`; the reproducible
archive is written beside that directory with a `.tar.gz` suffix.
