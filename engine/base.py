"""Abstract transcription engine interface.

Any speech-to-text backend (WhisperX today; ElevenLabs, Azure, Google
later) implements :class:`TranscriptionEngine` and returns the same
:class:`TranscriptionResult`, so the rest of the pipeline never changes
when a new engine is added.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

# progress(fraction_0_to_1, human_readable_message)
ProgressFn = Callable[[float, str], None]
# cancel() -> True means "stop as soon as possible"
CancelFn = Callable[[], bool]


class EngineError(RuntimeError):
    """Raised when a transcription engine cannot run."""


class PipelineCancelled(RuntimeError):
    """Raised when the user cancels a running pipeline."""


@dataclass(slots=True)
class RawWord:
    """A word as returned by the engine, before analysis."""

    word: str
    start: float | None
    end: float | None
    score: float = 1.0


@dataclass(slots=True)
class RawSegment:
    """An utterance-level segment (roughly one clause or sentence)."""

    text: str
    start: float
    end: float


@dataclass(slots=True)
class TranscriptionResult:
    """Engine output: aligned words plus the decoded audio itself.

    The audio samples are passed along so the acoustic feature stage
    (loudness / pitch for emphasis detection) does not decode twice.
    """

    words: list[RawWord]
    segments: list[RawSegment]
    language: str
    audio: np.ndarray  # mono float32
    sample_rate: int
    duration: float
    extra: dict[str, object] = field(default_factory=dict)


class TranscriptionEngine(ABC):
    """Contract every speech-to-text backend must fulfil."""

    name: str = "abstract"

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        *,
        model_name: str,
        language: str | None,
        device_preference: str,
        batch_size: int,
        progress: ProgressFn,
        cancel: CancelFn,
    ) -> TranscriptionResult:
        """Transcribe *audio_path* with word-level timestamps.

        Implementations must call *progress* regularly with a fraction in
        ``[0, 1]`` and check *cancel* between expensive steps, raising
        :class:`PipelineCancelled` when it returns True.
        """
        raise NotImplementedError
