"""Output formats for a finished timeline.

``ALL_EXPORTERS`` is the registry used for "export everything"; adding a
new format means writing one subclass and appending it here.
"""
from __future__ import annotations

import logging
from pathlib import Path

from exporters.analysis_exporter import AnalysisExporter
from exporters.base import ExportError, TimelineExporter
from exporters.claude_prompt import ClaudePromptExporter
from exporters.csv_exporter import CsvExporter
from exporters.json_exporter import JsonExporter
from exporters.srt_exporter import SrtExporter
from models import Timeline

logger = logging.getLogger(__name__)

ALL_EXPORTERS: tuple[TimelineExporter, ...] = (
    JsonExporter(),
    CsvExporter(),
    SrtExporter(),
    AnalysisExporter(),
    ClaudePromptExporter(),
)


def export_all(timeline: Timeline, output_dir: Path) -> list[Path]:
    """Write every registered format; returns the created file paths."""
    written: list[Path] = []
    for exporter in ALL_EXPORTERS:
        path = exporter.export(timeline, output_dir)
        logger.info("Exported %s -> %s", exporter.label, path)
        written.append(path)
    return written


__all__ = [
    "ALL_EXPORTERS",
    "AnalysisExporter",
    "ClaudePromptExporter",
    "CsvExporter",
    "ExportError",
    "JsonExporter",
    "SrtExporter",
    "TimelineExporter",
    "export_all",
]
