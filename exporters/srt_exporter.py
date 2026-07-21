"""``timeline.srt`` – sentence-level SubRip subtitles."""
from __future__ import annotations

from exporters.base import TimelineExporter
from models import Timeline
from utils.time_format import format_srt_timestamp


class SrtExporter(TimelineExporter):
    filename = "timeline.srt"
    label = "SRT subtitles"

    def render(self, timeline: Timeline) -> str:
        blocks: list[str] = []
        for i, sentence in enumerate(timeline.sentences, start=1):
            blocks.append(
                f"{i}\n"
                f"{format_srt_timestamp(sentence.start)} --> "
                f"{format_srt_timestamp(sentence.end)}\n"
                f"{sentence.text}\n"
            )
        return "\n".join(blocks)
