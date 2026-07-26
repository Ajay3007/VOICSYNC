"""Shared visual constants for the dark UI."""
from __future__ import annotations

import sys

# Base surfaces
COLOR_BG = "#101418"
COLOR_PANEL = "#171c22"
COLOR_PANEL_ALT = "#1d242c"
COLOR_BORDER = "#2a323c"

# Text
COLOR_TEXT = "#e6edf3"
COLOR_TEXT_MUTED = "#8b98a5"

# Accents
COLOR_ACCENT = "#3b82f6"
COLOR_ACCENT_HOVER = "#2563eb"
COLOR_SUCCESS = "#22c55e"
COLOR_WARNING = "#f59e0b"
COLOR_ERROR = "#ef4444"

# Log-level colors for the live log view.
LOG_COLORS: dict[str, str] = {
    "DEBUG": COLOR_TEXT_MUTED,
    "INFO": COLOR_TEXT,
    "WARNING": COLOR_WARNING,
    "ERROR": COLOR_ERROR,
    "CRITICAL": COLOR_ERROR,
    "SUCCESS": COLOR_SUCCESS,
}

# Tk resolves font families by exact name and falls back *silently* when a
# name is missing — so the family must exist on the platform.  macOS has
# neither "Segoe UI" nor "Consolas": both collapse to .AppleSystemUIFont,
# which is proportional, so the mono constant stops being monospaced and
# the log pane loses its alignment.  The real system fonts (SF Pro / SF
# Mono) are not exposed to Tk by name, leaving Helvetica Neue and Menlo as
# the reliable choices.
if sys.platform == "darwin":
    FONT_FAMILY = "Helvetica Neue"
    FONT_MONO = "Menlo"
elif sys.platform == "win32":
    FONT_FAMILY = "Segoe UI"
    FONT_MONO = "Consolas"
else:
    FONT_FAMILY = "DejaVu Sans"
    FONT_MONO = "DejaVu Sans Mono"

PAD = 12
PAD_SMALL = 6
CORNER_RADIUS = 8
