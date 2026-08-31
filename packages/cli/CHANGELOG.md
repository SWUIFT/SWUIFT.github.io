# Changelog

All notable changes to this project will be documented in this file.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where applicable.

## [1.0.0] - 2026-08-30

### Added
- Public CLI for single-run and batch SWUIFT experiments.
- Core data-loading, wind handling, and simulation pipeline.
- Windows and macOS desktop applications.
- User documentation site, Marshall tutorial, and example archives.
- Optional water input (omitted water uses an all-zero mask).
- venv, uv, and Conda CLI environment support.
- Inline comments and hyperparameter guidance for reproducibility.

### Fixed
- Bundle platform-specific FFmpeg and `imageio` metadata in desktop builds.
- PyAV and Pillow fallbacks when the FFmpeg subprocess is unavailable.
