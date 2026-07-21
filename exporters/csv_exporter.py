"""``timeline.csv`` – flat spreadsheet view of the whole timeline.

One file, one row per event.  The ``type`` column distinguishes words,
sentences and pauses so the CSV can be filtered in any spreadsheet tool.
"""
from __future__ import annotations

import csv
import io

from exporters.base import TimelineExporter
from models import Timeline

_HEADER = (
    "type",
    "index",
    "text",
    "start",
    "end",
    "duration",
    "importance",
    "confidence",
    "sentence_index",
)


class CsvExporter(TimelineExporter):
    filename = "timeline.csv"
    label = "CSV timeline"

    def render(self, timeline: Timeline) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(_HEADER)

        for i, word in enumerate(timeline.words):
            writer.writerow(
                (
                    "word",
                    i,
                    word.word,
                    f"{word.start:.3f}",
                    f"{word.end:.3f}",
                    f"{word.duration:.3f}",
                    word.importance,
                    f"{word.score:.3f}",
                    word.sentence_index,
                )
            )

        for i, sentence in enumerate(timeline.sentences):
            writer.writerow(
                (
                    "sentence",
                    i,
                    sentence.text,
                    f"{sentence.start:.3f}",
                    f"{sentence.end:.3f}",
                    f"{sentence.duration:.3f}",
                    "",
                    "",
                    i,
                )
            )

        for i, pause in enumerate(timeline.pauses):
            writer.writerow(
                (
                    "pause",
                    i,
                    pause.kind,
                    f"{pause.start:.3f}",
                    f"{pause.end:.3f}",
                    f"{pause.duration:.3f}",
                    "",
                    "",
                    "",
                )
            )

        return buffer.getvalue()
