# Changelog

All notable changes to this project will be documented in this file.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

## [1.0.0] - 2026-08-26

### Added
- Inline comments throughout core modules (CLI entrypoint, runners, data loading, and simulation utilities) to clarify control flow, data shapes, and key modeling assumptions.
- A consolidated list and description of primary hyperparameters in `README.md` to support easier configuration, tuning, and reproducibility of experiments.
- A looping, watermarked Marshall fire-progression animation in the tutorial.

### Changed
- Water input is optional in desktop, single-run CLI, and batch workflows. When it is omitted, SWUIFT constructs an all-zero “no water” mask.
- Quick-start guidance is consolidated into the desktop and command-line pages.

## [1.0.2] - 2026-08-24

### Fixed
- Bundle the platform-specific FFmpeg executable and `imageio` package metadata in Windows and macOS desktop builds.
- Use PyAV and Pillow fallbacks so MP4 and GIF assembly still succeeds if the FFmpeg subprocess is unavailable.

## [1.0.0] - 2025-xx-xx

### Added
- Initial public CLI for running single and batch SWUIFT experiments.
- Core data-loading, wind handling, and simulation pipeline.
- Basic documentation and example JSON job specification.
