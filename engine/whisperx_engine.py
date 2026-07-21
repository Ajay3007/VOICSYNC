"""WhisperX transcription engine with word-level forced alignment.

Pipeline inside this engine:

1. ``whisperx.load_audio``      – decode any ffmpeg-readable file to 16 kHz mono
2. ``whisperx.load_model``      – faster-whisper backend, auto-downloaded
3. ``model.transcribe``         – batched transcription (+ language detection)
4. ``whisperx.load_align_model``– wav2vec2 alignment model for the language
5. ``whisperx.align``           – phoneme-level forced alignment -> word times

Models are cached per (name, device, compute, language) so repeated runs
in one session are fast.  GPU is used when available; CPU (int8) is the
automatic fallback.
"""
from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Any, ClassVar

from engine.base import (
    CancelFn,
    EngineError,
    PipelineCancelled,
    ProgressFn,
    RawSegment,
    RawWord,
    TranscriptionEngine,
    TranscriptionResult,
)
from engine.device import resolve_device

logger = logging.getLogger(__name__)

WHISPERX_SAMPLE_RATE = 16_000


class WhisperXEngine(TranscriptionEngine):
    """Speaker-independent transcription + forced alignment via WhisperX."""

    name = "whisperx"

    # Cache heavyweight models across runs within the process.
    _asr_cache: ClassVar[dict[tuple[str, str, str, str | None], Any]] = {}
    _align_cache: ClassVar[dict[tuple[str, str], tuple[Any, Any]]] = {}

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
        progress(0.01, "Importing WhisperX (first import can take a moment)…")
        whisperx = self._import_whisperx()

        device, compute_type = resolve_device(device_preference)
        logger.info("Using device=%s compute_type=%s", device, compute_type)

        self._check_cancel(cancel)
        progress(0.04, f"Decoding audio: {audio_path.name}")
        try:
            audio = whisperx.load_audio(str(audio_path))
        except Exception as exc:
            raise EngineError(
                f"Could not decode '{audio_path.name}'. "
                "Make sure FFmpeg is installed and on your PATH. "
                f"({exc})"
            ) from exc
        duration = len(audio) / WHISPERX_SAMPLE_RATE
        logger.info("Audio decoded: %.2f s @ %d Hz", duration, WHISPERX_SAMPLE_RATE)

        self._check_cancel(cancel)
        progress(
            0.08,
            f"Loading model '{model_name}' on {device} "
            "(downloads automatically on first use)…",
        )
        model = self._load_asr_model(whisperx, model_name, device, compute_type, language)

        self._check_cancel(cancel)
        progress(0.25, "Transcribing…")
        try:
            result: dict[str, Any] = model.transcribe(
                audio, batch_size=batch_size, language=language
            )
        except Exception as exc:
            raise EngineError(f"Transcription failed: {exc}") from exc

        detected_language: str = result.get("language") or language or "en"
        segments_raw: list[dict[str, Any]] = result.get("segments") or []
        if not segments_raw:
            raise EngineError(
                "No speech detected in the audio. "
                "Check that the file actually contains narration."
            )
        logger.info(
            "Transcribed %d segments, language=%s", len(segments_raw), detected_language
        )

        self._check_cancel(cancel)
        progress(0.58, f"Language: {detected_language}. Loading alignment model…")
        align_model, align_metadata = self._load_align_model(
            whisperx, detected_language, device
        )

        self._check_cancel(cancel)
        progress(0.66, "Forced alignment (word-level timestamps)…")
        try:
            aligned: dict[str, Any] = whisperx.align(
                segments_raw,
                align_model,
                align_metadata,
                audio,
                device,
                return_char_alignments=False,
            )
        except Exception as exc:
            raise EngineError(f"Forced alignment failed: {exc}") from exc

        words, segments = self._collect_words(aligned, segments_raw)
        if not words:
            raise EngineError("Alignment produced no words; cannot build a timeline.")

        progress(0.97, f"Alignment complete: {len(words)} words.")
        gc.collect()

        return TranscriptionResult(
            words=words,
            segments=segments,
            language=detected_language,
            audio=audio,
            sample_rate=WHISPERX_SAMPLE_RATE,
            duration=duration,
        )

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _import_whisperx() -> Any:
        try:
            import whisperx  # noqa: PLC0415 - deliberate lazy import
        except ImportError as exc:
            raise EngineError(
                "WhisperX is not installed. Install dependencies with:\n"
                "    pip install -r requirements.txt"
            ) from exc
        _register_torch_safe_globals()
        return whisperx

    @classmethod
    def _load_asr_model(
        cls,
        whisperx: Any,
        model_name: str,
        device: str,
        compute_type: str,
        language: str | None,
    ) -> Any:
        key = (model_name, device, compute_type, language)
        if key not in cls._asr_cache:
            try:
                cls._asr_cache[key] = whisperx.load_model(
                    model_name, device, compute_type=compute_type, language=language
                )
            except Exception as exc:
                raise EngineError(
                    f"Could not load model '{model_name}' on {device}: {exc}"
                ) from exc
        return cls._asr_cache[key]

    @classmethod
    def _load_align_model(
        cls, whisperx: Any, language: str, device: str
    ) -> tuple[Any, Any]:
        key = (language, device)
        if key not in cls._align_cache:
            try:
                cls._align_cache[key] = whisperx.load_align_model(
                    language_code=language, device=device
                )
            except Exception as exc:
                raise EngineError(
                    f"No alignment model available for language '{language}': {exc}"
                ) from exc
        return cls._align_cache[key]

    @staticmethod
    def _collect_words(
        aligned: dict[str, Any], fallback_segments: list[dict[str, Any]]
    ) -> tuple[list[RawWord], list[RawSegment]]:
        """Flatten aligned segments into word and segment lists."""
        words: list[RawWord] = []
        segments: list[RawSegment] = []

        aligned_segments: list[dict[str, Any]] = aligned.get("segments") or []
        source = aligned_segments if aligned_segments else fallback_segments

        for segment in source:
            text = str(segment.get("text", "")).strip()
            seg_start = float(segment.get("start", 0.0) or 0.0)
            seg_end = float(segment.get("end", seg_start) or seg_start)
            if text:
                segments.append(RawSegment(text=text, start=seg_start, end=seg_end))

            for w in segment.get("words") or []:
                token = str(w.get("word", "")).strip()
                if not token:
                    continue
                start = w.get("start")
                end = w.get("end")
                words.append(
                    RawWord(
                        word=token,
                        start=float(start) if start is not None else None,
                        end=float(end) if end is not None else None,
                        score=float(w.get("score", 1.0) or 1.0),
                    )
                )
        return words, segments

    @staticmethod
    def _check_cancel(cancel: CancelFn) -> None:
        if cancel():
            raise PipelineCancelled("Cancelled by user.")


def _register_torch_safe_globals() -> None:
    """Allowlist classes contained in the pyannote VAD checkpoint.

    torch >= 2.6 defaults ``torch.load`` to ``weights_only=True``; the
    standard whisperx VAD checkpoint stores its training config as
    omegaconf objects, which the safe unpickler rejects.  pyannote.audio
    3.4 does not allowlist them itself, so register them here — this
    keeps ``weights_only=True`` (no arbitrary code execution) while
    letting the known config classes through.
    """
    try:
        import torch.serialization  # noqa: PLC0415
    except Exception as exc:
        logger.debug("Skipping torch safe-globals registration: %s", exc)
        return

    import collections  # noqa: PLC0415
    import typing  # noqa: PLC0415

    # (module path, attribute) pairs known to appear in pyannote/whisperx
    # checkpoints.  Resolved individually so one missing attribute (across
    # library versions) never blocks the rest.
    candidates: list[tuple[str, str]] = [
        ("omegaconf.listconfig", "ListConfig"),
        ("omegaconf.dictconfig", "DictConfig"),
        ("omegaconf.base", "ContainerMetadata"),
        ("omegaconf.base", "Metadata"),
        ("omegaconf.nodes", "AnyNode"),
        ("omegaconf.nodes", "ValueNode"),
        ("torch.torch_version", "TorchVersion"),
        ("pyannote.audio.core.task", "Specifications"),
        ("pyannote.audio.core.task", "Problem"),
        ("pyannote.audio.core.task", "Resolution"),
        ("pyannote.audio.core.model", "Introspection"),
    ]

    allowed: list[Any] = [
        typing.Any,
        list,
        dict,
        tuple,
        set,
        int,
        float,
        str,
        bytes,
        collections.defaultdict,
        collections.OrderedDict,
    ]
    for module_path, attribute in candidates:
        try:
            module = __import__(module_path, fromlist=[attribute])
            allowed.append(getattr(module, attribute))
        except Exception:
            logger.debug("Safe-globals candidate unavailable: %s.%s", module_path, attribute)

    try:
        torch.serialization.add_safe_globals(allowed)
    except Exception as exc:  # torch < 2.4 has no add_safe_globals; not needed there
        logger.debug("add_safe_globals failed: %s", exc)
