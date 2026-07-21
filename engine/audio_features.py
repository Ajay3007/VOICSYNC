"""Acoustic feature extraction for emphasis detection.

Works directly on the 16 kHz mono float32 array WhisperX already decoded,
so the audio file is never read twice.

* Loudness: frame-wise RMS energy in dBFS (pure NumPy, always available).
* Pitch:    fundamental frequency via ``librosa.yin`` (optional — if
            librosa is missing or fails, emphasis simply runs without
            the pitch feature).
"""
from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

_EPS = 1e-10
_PITCH_MIN_HZ = 65.0
_PITCH_MAX_HZ = 400.0


def loudness_profile(
    audio: np.ndarray,
    sample_rate: int,
    frame_length: int = 1024,
    hop_length: int = 512,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(frame_times, rms_db)`` for the whole recording."""
    audio = np.asarray(audio, dtype=np.float64)
    if len(audio) < frame_length:
        audio = np.pad(audio, (0, frame_length - len(audio)))

    n_frames = 1 + (len(audio) - frame_length) // hop_length
    squared_cumsum = np.concatenate(([0.0], np.cumsum(np.square(audio))))
    starts = np.arange(n_frames) * hop_length
    energy = (squared_cumsum[starts + frame_length] - squared_cumsum[starts]) / frame_length
    rms_db = 10.0 * np.log10(energy + _EPS)
    times = (starts + frame_length / 2) / sample_rate
    return times, rms_db


def pitch_profile(
    audio: np.ndarray,
    sample_rate: int,
    frame_length: int = 2048,
    hop_length: int = 256,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Return ``(frame_times, f0_hz)`` or ``None`` when pitch tracking
    is unavailable (librosa missing) or fails."""
    try:
        import librosa  # noqa: PLC0415 - optional dependency

        f0 = librosa.yin(
            np.asarray(audio, dtype=np.float32),
            fmin=_PITCH_MIN_HZ,
            fmax=_PITCH_MAX_HZ,
            sr=sample_rate,
            frame_length=frame_length,
            hop_length=hop_length,
        )
        times = librosa.times_like(f0, sr=sample_rate, hop_length=hop_length)
        return times, f0
    except Exception as exc:
        logger.warning("Pitch tracking unavailable (%s); emphasis will skip pitch.", exc)
        return None


def mean_in_range(
    times: np.ndarray, values: np.ndarray, start: float, end: float
) -> float | None:
    """Mean of frame *values* whose timestamps fall inside ``[start, end)``."""
    mask = (times >= start) & (times < end)
    if not np.any(mask):
        return None
    selected = values[mask]
    selected = selected[np.isfinite(selected)]
    if selected.size == 0:
        return None
    return float(np.mean(selected))


def median_pitch_in_range(
    times: np.ndarray, f0: np.ndarray, start: float, end: float
) -> float | None:
    """Median voiced pitch inside a word span.

    YIN emits garbage in unvoiced frames, so only values inside the
    plausible speech range are kept.
    """
    mask = (times >= start) & (times < end)
    if not np.any(mask):
        return None
    voiced = f0[mask]
    voiced = voiced[
        np.isfinite(voiced) & (voiced > _PITCH_MIN_HZ * 1.05) & (voiced < _PITCH_MAX_HZ * 0.95)
    ]
    if voiced.size == 0:
        return None
    return float(np.median(voiced))
