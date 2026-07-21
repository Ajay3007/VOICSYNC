"""voice-sync — Voiceover Timeline Generator.

Entry point.  Run with:

    python app.py

Transcribes an AI voiceover with WhisperX, performs word-level forced
alignment, detects pauses / speaking speed / emphasis, and exports
timeline.json, timeline.csv, timeline.srt, analysis.json and a
ready-to-paste Claude prompt for Manim synchronization.
"""
from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Guarantee absolute imports (ui, engine, …) resolve regardless of CWD.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.logging_config import setup_logging  # noqa: E402

logger = logging.getLogger("voice-sync")

MIN_PYTHON = (3, 10)
MAX_TESTED_PYTHON = (3, 12)


def _check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        sys.exit(
            f"voice-sync requires Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
            f"(you are running {sys.version.split()[0]})."
        )
    if sys.version_info[:2] > MAX_TESTED_PYTHON:
        print(
            f"WARNING: Python {sys.version.split()[0]} detected. "
            "PyTorch/WhisperX wheels are typically published for Python "
            f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}-{MAX_TESTED_PYTHON[0]}.{MAX_TESTED_PYTHON[1]}; "
            "if installation failed, create a venv with Python 3.11 or 3.12.",
            file=sys.stderr,
        )


def _check_environment() -> None:
    """Log (not fail on) missing runtime prerequisites."""
    if shutil.which("ffmpeg") is None:
        logger.warning(
            "FFmpeg was not found on PATH. Audio decoding will fail. "
            "Install it, e.g.:  winget install Gyan.FFmpeg"
        )
    try:
        from engine.device import describe_hardware

        logger.info("Compute device: %s", describe_hardware())
    except Exception as exc:  # torch not installed yet, etc.
        logger.warning("Could not probe compute device: %s", exc)


def main() -> None:
    _check_python_version()
    setup_logging(PROJECT_ROOT / "output" / "logs")
    logger.info("Starting voice-sync from %s", PROJECT_ROOT)

    try:
        import customtkinter  # noqa: F401
    except ImportError:
        sys.exit(
            "CustomTkinter is not installed.\n"
            "Install dependencies first:\n"
            "    pip install -r requirements.txt"
        )

    _check_environment()

    from ui.main_window import MainWindow

    window = MainWindow(PROJECT_ROOT)
    window.mainloop()


if __name__ == "__main__":
    main()
