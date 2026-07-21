"""Emphasis estimation.

Each word receives a composite emphasis score built from z-normalized
prosodic features:

* stretched duration   (duration per character, so long words aren't
  automatically "emphasized")
* pause before / after the word (speakers pause around key terms)
* relative loudness (RMS dB vs. the rest of the narration)
* relative pitch (median F0 vs. the rest, when pitch tracking is available)

The composite score maps to ``low`` / ``medium`` / ``high``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from engine import audio_features
from engine.config import PipelineConfig
from models import WordEntry

logger = logging.getLogger(__name__)

_MAX_MEANINGFUL_PAUSE = 1.5  # seconds; longer pauses saturate the feature

# Feature weights (sum to 1.0).
_W_DURATION = 0.30
_W_LOUDNESS = 0.25
_W_PITCH = 0.20
_W_PAUSE_AFTER = 0.15
_W_PAUSE_BEFORE = 0.10


@dataclass(slots=True)
class _Features:
    duration_per_char: np.ndarray
    pause_before: np.ndarray
    pause_after: np.ndarray
    loudness: np.ndarray
    pitch: np.ndarray


def annotate_emphasis(
    words: list[WordEntry],
    audio: np.ndarray,
    sample_rate: int,
    config: PipelineConfig,
) -> None:
    """Fill ``importance``, ``loudness_db`` and ``pitch_hz`` on each word in place."""
    if not words:
        return

    features = _extract_features(words, audio, sample_rate)
    scores = _composite_scores(features)

    high, medium = 0, 0
    for word, score in zip(words, scores):
        if score >= config.emphasis_high:
            word.importance = "high"
            high += 1
        elif score >= config.emphasis_medium:
            word.importance = "medium"
            medium += 1
        else:
            word.importance = "low"

    logger.info(
        "Emphasis: %d high, %d medium, %d low", high, medium, len(words) - high - medium
    )


def _extract_features(
    words: list[WordEntry], audio: np.ndarray, sample_rate: int
) -> _Features:
    n = len(words)

    loud_times, loud_db = audio_features.loudness_profile(audio, sample_rate)
    pitch = audio_features.pitch_profile(audio, sample_rate)

    duration_per_char = np.empty(n)
    pause_before = np.zeros(n)
    pause_after = np.zeros(n)
    loudness = np.full(n, np.nan)
    pitch_hz = np.full(n, np.nan)

    for i, word in enumerate(words):
        chars = max(1, sum(ch.isalnum() for ch in word.word))
        duration_per_char[i] = word.duration / chars

        if i > 0:
            gap = max(0.0, word.start - words[i - 1].end)
            pause_before[i] = min(gap, _MAX_MEANINGFUL_PAUSE) / _MAX_MEANINGFUL_PAUSE
        if i < n - 1:
            gap = max(0.0, words[i + 1].start - word.end)
            pause_after[i] = min(gap, _MAX_MEANINGFUL_PAUSE) / _MAX_MEANINGFUL_PAUSE

        db = audio_features.mean_in_range(loud_times, loud_db, word.start, word.end)
        if db is not None:
            loudness[i] = db
            word.loudness_db = db

        if pitch is not None:
            f0 = audio_features.median_pitch_in_range(
                pitch[0], pitch[1], word.start, word.end
            )
            if f0 is not None:
                pitch_hz[i] = f0
                word.pitch_hz = f0

    return _Features(
        duration_per_char=duration_per_char,
        pause_before=pause_before,
        pause_after=pause_after,
        loudness=loudness,
        pitch=pitch_hz,
    )


def _composite_scores(features: _Features) -> np.ndarray:
    """Weighted sum of z-scored features; NaNs contribute zero."""
    return (
        _W_DURATION * _zscore(features.duration_per_char)
        + _W_LOUDNESS * _zscore(features.loudness)
        + _W_PITCH * _zscore(features.pitch)
        + _W_PAUSE_AFTER * _zscore(features.pause_after)
        + _W_PAUSE_BEFORE * _zscore(features.pause_before)
    )


def _zscore(values: np.ndarray) -> np.ndarray:
    """NaN-aware z-score; returns zeros when the feature has no variance."""
    finite = values[np.isfinite(values)]
    if finite.size < 2:
        return np.zeros_like(values)
    mean = float(np.mean(finite))
    std = float(np.std(finite))
    if std < 1e-9:
        return np.zeros_like(values)
    z = (values - mean) / std
    return np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)
