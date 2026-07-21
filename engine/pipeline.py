"""End-to-end pipeline: audio file -> :class:`models.Timeline`.

Stages (with their share of the progress bar):

1. Transcription + forced alignment (engine)  ....... 0.00 – 0.80
2. Acoustic features + emphasis  .................... 0.80 – 0.92
3. Sentences, pauses, analysis  ..................... 0.92 – 1.00

The pipeline is UI-agnostic: it reports through a ``progress(fraction,
message)`` callback and honours a ``cancel()`` predicate, which makes it
equally usable from the GUI, a CLI, or tests.
"""
from __future__ import annotations

import logging
from pathlib import Path

from engine import analysis, emphasis
from engine.base import (
    CancelFn,
    PipelineCancelled,
    ProgressFn,
    TranscriptionEngine,
)
from engine.config import PipelineConfig
from models import Timeline

logger = logging.getLogger(__name__)

_ENGINE_SPAN = (0.0, 0.80)
_EMPHASIS_SPAN = (0.80, 0.92)
_ANALYSIS_SPAN = (0.92, 1.00)


def _noop_progress(_fraction: float, _message: str) -> None:
    """Default progress sink."""


def _never_cancel() -> bool:
    return False


class VoicePipeline:
    """Runs one full extraction with any :class:`TranscriptionEngine`."""

    def __init__(self, engine: TranscriptionEngine) -> None:
        self._engine = engine

    def run(
        self,
        config: PipelineConfig,
        progress: ProgressFn = _noop_progress,
        cancel: CancelFn = _never_cancel,
    ) -> Timeline:
        """Execute the pipeline and return the completed timeline.

        Raises :class:`engine.base.PipelineCancelled` if *cancel* fires and
        :class:`engine.base.EngineError` for engine failures.
        """
        config.validate()
        logger.info(
            "Pipeline start: %s (model=%s, language=%s)",
            config.audio_path.name,
            config.model_name,
            config.language or "auto",
        )

        # ---- stage 1: transcription + alignment -------------------------
        result = self._engine.transcribe(
            config.audio_path,
            model_name=config.model_name,
            language=config.language,
            device_preference=config.device_preference,
            batch_size=config.batch_size,
            progress=_scaled(progress, *_ENGINE_SPAN),
            cancel=cancel,
        )
        self._check_cancel(cancel)

        # Surface the transcription in the live log, segment by segment.
        for segment in result.segments:
            logger.info("[%7.2fs] %s", segment.start, segment.text)

        words = analysis.build_words(result.words)
        logger.info("Timeline words: %d", len(words))

        # ---- stage 2: acoustic features + emphasis -----------------------
        emphasis_progress = _scaled(progress, *_EMPHASIS_SPAN)
        emphasis_progress(0.1, "Extracting loudness and pitch…")
        emphasis.annotate_emphasis(words, result.audio, result.sample_rate, config)
        emphasis_progress(1.0, "Emphasis estimation done.")
        self._check_cancel(cancel)

        # ---- stage 3: structure + statistics -----------------------------
        analysis_progress = _scaled(progress, *_ANALYSIS_SPAN)
        analysis_progress(0.2, "Building sentences and pauses…")
        sentences = analysis.build_sentences(words, config)
        pauses = analysis.detect_pauses(words, result.duration, config)

        script_text = _read_script(config.script_path)
        analysis_result = analysis.build_analysis(
            words=words,
            sentences=sentences,
            pauses=pauses,
            total_duration=result.duration,
            language=result.language,
            config=config,
            script_text=script_text,
        )
        analysis_progress(1.0, "Analysis complete.")

        timeline = Timeline(
            audio_file=config.audio_path,
            language=result.language,
            duration=result.duration,
            words=words,
            sentences=sentences,
            pauses=pauses,
            analysis=analysis_result,
            model_name=config.model_name,
            engine_name=self._engine.name,
        )
        logger.info(
            "Pipeline done: %d words, %d sentences, %d pauses, %.1f WPM",
            len(words),
            len(sentences),
            len(pauses),
            analysis_result.words_per_minute,
        )
        return timeline

    @staticmethod
    def _check_cancel(cancel: CancelFn) -> None:
        if cancel():
            raise PipelineCancelled("Cancelled by user.")


def _scaled(progress: ProgressFn, lower: float, upper: float) -> ProgressFn:
    """Map a stage-local 0..1 fraction into the global progress range."""

    def scaled(fraction: float, message: str) -> None:
        fraction = min(max(fraction, 0.0), 1.0)
        progress(lower + fraction * (upper - lower), message)

    return scaled


def _read_script(script_path: Path | None) -> str | None:
    if script_path is None:
        return None
    try:
        return script_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Could not read script file %s: %s", script_path, exc)
        return None
