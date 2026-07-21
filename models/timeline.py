"""Data models describing a synchronized voiceover timeline.

Every entity produced by the analysis pipeline lives here as a typed,
serializable dataclass.  Exporters and the UI consume only these models,
never raw engine output, which keeps the engine swappable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _r(value: float, digits: int = 3) -> float:
    """Round a float for stable, compact serialization."""
    return round(float(value), digits)


@dataclass(slots=True)
class WordEntry:
    """A single spoken word with forced-alignment timing."""

    word: str
    start: float
    end: float
    score: float = 1.0
    importance: str = "low"  # "low" | "medium" | "high"
    loudness_db: float | None = None
    pitch_hz: float | None = None
    sentence_index: int = -1

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "word": self.word,
            "start": _r(self.start),
            "end": _r(self.end),
            "duration": _r(self.duration),
            "importance": self.importance,
            "confidence": _r(self.score),
            "sentence_index": self.sentence_index,
        }
        if self.loudness_db is not None:
            data["loudness_db"] = _r(self.loudness_db, 1)
        if self.pitch_hz is not None:
            data["pitch_hz"] = _r(self.pitch_hz, 1)
        return data


@dataclass(slots=True)
class SentenceEntry:
    """A sentence assembled from consecutive words."""

    text: str
    start: float
    end: float
    word_count: int = 0

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "start": _r(self.start),
            "end": _r(self.end),
            "duration": _r(self.duration),
            "word_count": self.word_count,
        }


@dataclass(slots=True)
class PauseEntry:
    """A silent gap in the narration."""

    start: float
    end: float
    kind: str = "short"  # "short" | "long" | "leading" | "trailing"

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": _r(self.start),
            "end": _r(self.end),
            "duration": _r(self.duration),
            "kind": self.kind,
        }


@dataclass(slots=True)
class SpeechRegion:
    """A time span where speaking speed deviates from the average."""

    start: float
    end: float
    words_per_minute: float
    kind: str  # "fast" | "slow"

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": _r(self.start),
            "end": _r(self.end),
            "words_per_minute": _r(self.words_per_minute, 1),
            "kind": self.kind,
        }


@dataclass(slots=True)
class AnalysisResult:
    """Aggregate statistics derived from the timeline."""

    total_duration: float = 0.0
    language: str = "en"
    word_count: int = 0
    sentence_count: int = 0
    words_per_minute: float = 0.0
    articulation_wpm: float = 0.0  # WPM excluding pause time
    pause_count: int = 0
    short_pause_count: int = 0
    long_pause_count: int = 0
    total_pause_time: float = 0.0
    average_pause_duration: float = 0.0
    longest_pause: float = 0.0
    fast_regions: list[SpeechRegion] = field(default_factory=list)
    slow_regions: list[SpeechRegion] = field(default_factory=list)
    emphasized_words: list[dict[str, Any]] = field(default_factory=list)
    script_similarity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "total_duration": _r(self.total_duration),
            "language": self.language,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "words_per_minute": _r(self.words_per_minute, 1),
            "articulation_wpm": _r(self.articulation_wpm, 1),
            "pauses": {
                "count": self.pause_count,
                "short": self.short_pause_count,
                "long": self.long_pause_count,
                "total_time": _r(self.total_pause_time),
                "average_duration": _r(self.average_pause_duration),
                "longest": _r(self.longest_pause),
            },
            "fast_speech_regions": [r.to_dict() for r in self.fast_regions],
            "slow_speech_regions": [r.to_dict() for r in self.slow_regions],
            "emphasized_words": self.emphasized_words,
        }
        if self.script_similarity is not None:
            data["script_similarity"] = _r(self.script_similarity)
        return data


@dataclass(slots=True)
class Timeline:
    """The complete result of one pipeline run."""

    audio_file: Path
    language: str
    duration: float
    words: list[WordEntry] = field(default_factory=list)
    sentences: list[SentenceEntry] = field(default_factory=list)
    pauses: list[PauseEntry] = field(default_factory=list)
    analysis: AnalysisResult = field(default_factory=AnalysisResult)
    model_name: str = ""
    engine_name: str = ""

    @property
    def transcript(self) -> str:
        return " ".join(sentence.text for sentence in self.sentences)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": {
                "audio_file": self.audio_file.name,
                "engine": self.engine_name,
                "model": self.model_name,
                "language": self.language,
                "duration": _r(self.duration),
            },
            "words": [w.to_dict() for w in self.words],
            "sentences": [s.to_dict() for s in self.sentences],
            "pauses": [p.to_dict() for p in self.pauses],
        }
