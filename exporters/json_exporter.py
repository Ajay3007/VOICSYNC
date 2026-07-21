"""``timeline.json`` – the complete machine-readable timeline."""
from __future__ import annotations

import json

from exporters.base import TimelineExporter
from models import Timeline


class JsonExporter(TimelineExporter):
    filename = "timeline.json"
    label = "JSON timeline"

    def render(self, timeline: Timeline) -> str:
        return json.dumps(timeline.to_dict(), indent=2, ensure_ascii=False) + "\n"
