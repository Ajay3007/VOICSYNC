"""Time formatting helpers shared by the UI and exporters."""
from __future__ import annotations


def format_clock(seconds: float) -> str:
    """Format seconds as ``MM:SS`` (or ``H:MM:SS`` past one hour)."""
    seconds = max(0.0, seconds)
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp: ``HH:MM:SS,mmm``."""
    seconds = max(0.0, seconds)
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def format_seconds(seconds: float, digits: int = 2) -> str:
    """Format seconds as a plain decimal string, e.g. ``2.31``."""
    return f"{max(0.0, seconds):.{digits}f}"
