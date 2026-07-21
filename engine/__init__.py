"""Speech-analysis engine: transcription, alignment, emphasis, statistics.

Public surface:

* :class:`engine.config.PipelineConfig` – all pipeline options
* :class:`engine.pipeline.VoicePipeline` – orchestrator
* :class:`engine.whisperx_engine.WhisperXEngine` – default backend
* :class:`engine.base.TranscriptionEngine` – implement this to add backends
"""
from engine.base import (
    EngineError,
    PipelineCancelled,
    TranscriptionEngine,
    TranscriptionResult,
)
from engine.config import (
    AVAILABLE_LANGUAGES,
    AVAILABLE_MODELS,
    SUPPORTED_AUDIO_EXTENSIONS,
    PipelineConfig,
)
from engine.pipeline import VoicePipeline
from engine.whisperx_engine import WhisperXEngine

__all__ = [
    "AVAILABLE_LANGUAGES",
    "AVAILABLE_MODELS",
    "SUPPORTED_AUDIO_EXTENSIONS",
    "EngineError",
    "PipelineCancelled",
    "PipelineConfig",
    "TranscriptionEngine",
    "TranscriptionResult",
    "VoicePipeline",
    "WhisperXEngine",
]
