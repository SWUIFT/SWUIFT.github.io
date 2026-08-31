"""Run logging utilities (console + run_log.txt tee)."""

from __future__ import annotations

import contextlib
import io
import os
import shlex
import sys
from typing import Iterable


class _TeeStream(io.TextIOBase):
    def __init__(self, original: io.TextIOBase, log_file: io.TextIOBase):
        self._original = original
        self._log_file = log_file

    def write(self, s: str) -> int:
        self._original.write(s)
        try:
            self._log_file.write(s)
        except ValueError:
            # Can happen during interpreter shutdown if log file is already closed.
            pass
        return len(s)

    def flush(self) -> None:
        self._original.flush()
        try:
            self._log_file.flush()
        except ValueError:
            # Can happen during interpreter shutdown if log file is already closed.
            pass


def format_command(argv: Iterable[str]) -> str:
    return " ".join(shlex.quote(a) for a in argv)


@contextlib.contextmanager
def tee_run_output(output_dir: str, command_line: str):
    """Duplicate stdout/stderr to ``run_log.txt`` under the run output folder."""
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "run_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Command: {command_line}\n")
        f.write("=" * 80 + "\n")
        f.flush()
        tee_out = _TeeStream(sys.stdout, f)
        tee_err = _TeeStream(sys.stderr, f)
        with contextlib.redirect_stdout(tee_out), contextlib.redirect_stderr(tee_err):
            yield log_path

