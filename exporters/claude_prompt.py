"""``claude_prompt.md`` – ready-to-paste prompt for Claude.

The markdown skeleton lives in ``assets/claude_prompt_template.md`` so it
can be tweaked without touching code; a built-in copy of the template is
used as a fallback if the asset is ever missing.
"""
from __future__ import annotations

import logging
from pathlib import Path

from exporters.base import TimelineExporter
from models import Timeline
from utils.time_format import format_seconds

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_TEMPLATE_PATH = _ASSETS_DIR / "claude_prompt_template.md"

_FALLBACK_TEMPLATE = """# Voice Timeline

Audio: `{audio_name}`
Duration: **{duration}s** · Words: **{word_count}** · Sentences: **{sentence_count}** · Speaking speed: **{wpm} WPM** · Language: **{language}**

## Word timestamps

{word_block}

## Sentences

{sentence_block}

## Pauses

{pause_block}

## Instructions for Claude

Synchronize every Manim animation with these timestamps.

- Visuals should begin slightly before the spoken keyword (0.15-0.30 s early).
- Finish each animation before the next important keyword begins.
- Use pauses for scene transitions.
- Use sentence boundaries for camera changes.
- Words marked **high** importance deserve the strongest visual moment.
"""


class ClaudePromptExporter(TimelineExporter):
    filename = "claude_prompt.md"
    label = "Claude prompt"

    def render(self, timeline: Timeline) -> str:
        template = self._load_template()
        return template.format(
            audio_name=timeline.audio_file.name,
            duration=format_seconds(timeline.duration),
            word_count=len(timeline.words),
            sentence_count=len(timeline.sentences),
            wpm=f"{timeline.analysis.words_per_minute:.0f}",
            language=timeline.language,
            word_block=self._word_block(timeline),
            sentence_block=self._sentence_block(timeline),
            pause_block=self._pause_block(timeline),
        )

    @staticmethod
    def _load_template() -> str:
        try:
            return _TEMPLATE_PATH.read_text(encoding="utf-8")
        except OSError:
            logger.warning(
                "Template asset missing (%s); using built-in fallback.", _TEMPLATE_PATH
            )
            return _FALLBACK_TEMPLATE

    @staticmethod
    def _word_block(timeline: Timeline) -> str:
        lines: list[str] = []
        for word in timeline.words:
            stamp = format_seconds(word.start)
            if word.importance == "high":
                lines.append(f"`{stamp}`  **{word.word}**  (emphasis: high)")
            elif word.importance == "medium":
                lines.append(f"`{stamp}`  **{word.word}**  (emphasis: medium)")
            else:
                lines.append(f"`{stamp}`  {word.word}")
        return "\n".join(lines) if lines else "_(no words)_"

    @staticmethod
    def _sentence_block(timeline: Timeline) -> str:
        lines = [
            f"- `[{format_seconds(s.start)} – {format_seconds(s.end)}]` {s.text}"
            for s in timeline.sentences
        ]
        return "\n".join(lines) if lines else "_(no sentences)_"

    @staticmethod
    def _pause_block(timeline: Timeline) -> str:
        lines = [
            f"- `[{format_seconds(p.start)} – {format_seconds(p.end)}]` "
            f"{format_seconds(p.duration)}s ({p.kind})"
            for p in timeline.pauses
        ]
        return "\n".join(lines) if lines else "_(no pauses detected)_"
