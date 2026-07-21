"""Centralized logging configuration.

The application logs to a rotating file (``output/logs/voice-sync.log``)
and to the console.  The UI can additionally attach a
:class:`CallbackLogHandler` to mirror log records into the live log view.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%H:%M:%S"


def setup_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure the root logger with file and console handlers."""
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers when called twice (e.g. in tests).
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return root

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_dir / "voice-sync.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Third-party libraries are extremely chatty at INFO.
    for noisy in ("urllib3", "matplotlib", "numba", "speechbrain", "pyannote"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return root


class CallbackLogHandler(logging.Handler):
    """Forwards formatted log records to an arbitrary callable.

    Used by the UI to mirror pipeline logs into the on-screen log view
    without the pipeline knowing anything about tkinter.
    """

    def __init__(self, callback: Callable[[str, str], None]) -> None:
        super().__init__()
        self._callback = callback
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._callback(self.format(record), record.levelname)
        except Exception:  # pragma: no cover - never break logging
            self.handleError(record)
