"""``analysis.json`` – aggregate statistics for the narration."""
from __future__ import annotations

import json

from exporters.base import TimelineExporter
from models import Timeline


class AnalysisExporter(TimelineExporter):
    filename = "analysis.json"
    label = "Analysis JSON"

    def render(self, timeline: Timeline) -> str:
        return json.dumps(timeline.analysis.to_dict(), indent=2, ensure_ascii=False) + "\n"
