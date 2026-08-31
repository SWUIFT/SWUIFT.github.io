"""Verify that a frozen SWUIFT desktop bundle can assemble videos."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        raise SystemExit(f"Desktop bundle does not exist: {bundle}")

    files = [path for path in bundle.rglob("*") if path.is_file()]
    ffmpeg_paths = [
        path
        for path in files
        if path.name.lower().startswith("ffmpeg") and "imageio_ffmpeg" in path.as_posix()
    ]
    ffmpeg = {path.resolve() for path in ffmpeg_paths}
    if len(ffmpeg) != 1:
        raise SystemExit(
            "Expected one physical imageio-ffmpeg executable, found "
            f"{len(ffmpeg)} via {ffmpeg_paths}"
        )

    imageio_metadata_paths = [
        path for path in bundle.rglob("imageio-*.dist-info") if "imageio_ffmpeg-" not in path.name
    ]
    imageio_metadata = {path.resolve() for path in imageio_metadata_paths}
    if len(imageio_metadata) != 1:
        raise SystemExit(
            "Expected one physical imageio metadata directory, found "
            f"{len(imageio_metadata)} via {imageio_metadata_paths}"
        )

    executable = ffmpeg.pop()
    if os.name != "nt" and not os.access(executable, os.X_OK):
        raise SystemExit(f"Bundled ffmpeg is not executable: {executable}")
    subprocess.run(
        [str(executable), "-version"],
        check=True,
        capture_output=True,
        text=True,
    )
    print(f"Verified bundled ffmpeg: {executable.relative_to(bundle)}")
    metadata = imageio_metadata.pop()
    print(f"Verified imageio metadata: {metadata.relative_to(bundle)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
