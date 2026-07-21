"""Abstract exporter interface.

Every output format (JSON, CSV, SRT, Claude prompt, and future targets
such as Premiere Pro XML, After Effects markers, DaVinci Resolve EDL, or
CapCut timelines) implements :class:`TimelineExporter`.  New formats are
added by dropping in a subclass and registering it in
``exporters/__init__.py`` — no core changes required.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from models import Timeline


class ExportError(RuntimeError):
    """Raised when an export cannot be written."""


class TimelineExporter(ABC):
    """Contract for one output format."""

    #: Default file name produced inside the output directory.
    filename: str = "export.txt"
    #: Human-readable label used in logs and the UI.
    label: str = "Export"

    def export(self, timeline: Timeline, output_dir: Path) -> Path:
        """Render *timeline* and write it below *output_dir*.

        Returns the path of the written file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / self.filename
        try:
            target.write_text(self.render(timeline), encoding="utf-8", newline="\n")
        except OSError as exc:
            raise ExportError(f"Could not write {target}: {exc}") from exc
        return target

    @abstractmethod
    def render(self, timeline: Timeline) -> str:
        """Return the full file content for *timeline*."""
        raise NotImplementedError
