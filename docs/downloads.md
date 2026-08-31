# Downloads

Official releases are published as immutable, versioned GitHub Release assets.
Do not use temporary workflow artifacts for archival or cited research.

## Current release: v1.0.0

Release page: [https://github.com/SWUIFT/SWUIFT.github.io/releases/tag/v1.0.0](https://github.com/SWUIFT/SWUIFT.github.io/releases/tag/v1.0.0)

Tagged commit: [`REPLACE_AFTER_TAG`](https://github.com/SWUIFT/SWUIFT.github.io/tree/v1.0.0)

> Desktop digests are `REPLACE_AFTER_BUILD` until CI publishes installers.
> Marshall archive digests below match the archives committed under
> `examples/artifacts/`.

## Desktop packages

| Platform | Package | Download | SHA-256 |
|---|---|---|---|
| Windows x64 | Installer (`.exe`) | [SWUIFT_Setup_1.0.0.exe](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/SWUIFT_Setup_1.0.0.exe) | `REPLACE_AFTER_BUILD` |
| macOS Apple silicon (arm64) | Disk image (`.dmg`) | [SWUIFT_macOS_arm64.dmg](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/SWUIFT_macOS_arm64.dmg) | `REPLACE_AFTER_BUILD` |
| macOS Intel (x86_64) | Disk image (`.dmg`) | [SWUIFT_macOS_x86_64.dmg](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/SWUIFT_macOS_x86_64.dmg) | `REPLACE_AFTER_BUILD` |

Desktop packages are published only for Windows and macOS. Linux users can use
the CLI from a versioned source release; no Linux desktop application is built
or supported.

## Marshall example archives

Separate input and validated-output archives for the public Marshall 121-state
window (11:00–21:00 MST on 2021-12-30). Use these with the
[Marshall tutorial](marshall-tutorial.md).

When using these archives, cite the
[Marshall Fire coupling article](citation-license.md#marshall-example) in
addition to the main SWUIFT implementation article.

| Archive | Contents | Download | SHA-256 |
|---|---|---|---|
| Inputs | Marshall example inputs | [marshall_20211230_1100-2100_MST-inputs.tar.gz](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/marshall_20211230_1100-2100_MST-inputs.tar.gz) | `3a0f719dd7747e11849b192cf6a28b12ae2ddaebccfa9189d8f922d083a64f8b` |
| Outputs | Marshall example outputs | [marshall_20211230_1100-2100_MST-output.tar.gz](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/marshall_20211230_1100-2100_MST-output.tar.gz) | `f5e244562223bace9da1b29ac605b3950f46af958a8557d03a3f1d661afb993a` |

The same archives are also stored in the repository at
[`examples/artifacts/`](https://github.com/SWUIFT/SWUIFT.github.io/tree/main/examples/artifacts).

Extract the input archive to a local data directory, then point the CLI
`--data-root` or desktop file pickers at that directory. Metadata, manifests,
and per-file checksums remain in
[`examples/marshall_20211230_1100-2100_MST/`](https://github.com/SWUIFT/SWUIFT.github.io/tree/main/examples/marshall_20211230_1100-2100_MST).

## Python packages

Source distributions and wheels for `swuift` and `swuift-core` are attached to
the same [v1.0.0 release](https://github.com/SWUIFT/SWUIFT.github.io/releases/tag/v1.0.0),
together with `SHA256SUMS`.

## Release records

- Release page: [v1.0.0](https://github.com/SWUIFT/SWUIFT.github.io/releases/tag/v1.0.0)
- Source at release tag: [v1.0.0](https://github.com/SWUIFT/SWUIFT.github.io/tree/v1.0.0)
- Source archive: [Source code (zip)](https://github.com/SWUIFT/SWUIFT.github.io/archive/refs/tags/v1.0.0.zip)
- Python package checksums: [SHA256SUMS](https://github.com/SWUIFT/SWUIFT.github.io/releases/download/v1.0.0/SHA256SUMS)

For cited work, point to this tagged release (or a version DOI once Zenodo
mints one). Prefer the tag or commit over a moving branch such as `main`.
