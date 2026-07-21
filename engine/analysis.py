"""Timeline analysis: sentences, pauses, speaking-speed statistics.

All functions are pure (no I/O, no engine imports) so they are trivially
unit-testable and reusable by future exporters.
"""
from __future__ import annotations

import difflib
import logging

from engine.base import RawWord
from engine.config import PipelineConfig
from models import AnalysisResult, PauseEntry, SentenceEntry, SpeechRegion, WordEntry
from utils.text import clean_word, ends_sentence, normalize_words

logger = logging.getLogger(__name__)

_MAX_SENTENCE_WORDS = 40  # hard split for punctuation-less transcripts


def build_words(raw_words: list[RawWord]) -> list[WordEntry]:
    """Convert raw engine words to model entries, repairing missing times.

    WhisperX occasionally cannot align a token (numbers, foreign words);
    those come back without ``start``/``end``.  Missing times are
    interpolated between the nearest aligned neighbours so the timeline
    stays gap-free and monotonic.
    """
    entries: list[WordEntry] = []
    for raw in raw_words:
        token = clean_word(raw.word)
        if token:
            entries.append(
                WordEntry(
                    word=token,
                    start=raw.start if raw.start is not None else -1.0,
                    end=raw.end if raw.end is not None else -1.0,
                    score=raw.score,
                )
            )

    _interpolate_missing_times(entries)

    # Enforce monotonic, non-overlapping times.
    for i in range(1, len(entries)):
        if entries[i].start < entries[i - 1].end:
            entries[i].start = entries[i - 1].end
        if entries[i].end < entries[i].start:
            entries[i].end = entries[i].start
    return entries


def _interpolate_missing_times(words: list[WordEntry]) -> None:
    """Fill ``-1`` sentinel times by spreading unaligned runs evenly
    between the surrounding aligned words."""
    n = len(words)
    i = 0
    while i < n:
        if words[i].start >= 0.0 and words[i].end >= 0.0:
            i += 1
            continue

        run_start = i
        while i < n and (words[i].start < 0.0 or words[i].end < 0.0):
            i += 1
        run_end = i  # exclusive

        left = words[run_start - 1].end if run_start > 0 else 0.0
        right = words[run_end].start if run_end < n else left + 0.3 * (run_end - run_start)
        right = max(right, left)
        span = (right - left) / (run_end - run_start)
        for j in range(run_start, run_end):
            words[j].start = left + (j - run_start) * span
            words[j].end = words[j].start + span

        if run_end - run_start:
            logger.debug(
                "Interpolated timestamps for %d unaligned word(s) at index %d.",
                run_end - run_start,
                run_start,
            )


def build_sentences(
    words: list[WordEntry], config: PipelineConfig
) -> list[SentenceEntry]:
    """Group words into sentences and stamp ``sentence_index`` on each word.

    Primary signal is terminal punctuation.  For transcripts without
    punctuation, a long silence (``config.sentence_gap``) or a hard word
    cap also closes the sentence.
    """
    sentences: list[SentenceEntry] = []
    current: list[WordEntry] = []

    def flush() -> None:
        if not current:
            return
        index = len(sentences)
        for w in current:
            w.sentence_index = index
        sentences.append(
            SentenceEntry(
                text=" ".join(w.word for w in current),
                start=current[0].start,
                end=current[-1].end,
                word_count=len(current),
            )
        )
        current.clear()

    for i, word in enumerate(words):
        current.append(word)
        next_gap = (
            words[i + 1].start - word.end if i + 1 < len(words) else 0.0
        )
        if (
            ends_sentence(word.word)
            or (next_gap >= config.sentence_gap and len(current) >= 4)
            or len(current) >= _MAX_SENTENCE_WORDS
        ):
            flush()
    flush()
    return sentences


def detect_pauses(
    words: list[WordEntry], total_duration: float, config: PipelineConfig
) -> list[PauseEntry]:
    """Find every silence of at least ``config.min_pause`` seconds."""
    pauses: list[PauseEntry] = []
    if not words:
        return pauses

    def classify(duration: float) -> str:
        return "long" if duration >= config.long_pause else "short"

    leading = words[0].start
    if leading >= config.min_pause:
        pauses.append(PauseEntry(start=0.0, end=leading, kind="leading"))

    for previous, current in zip(words, words[1:]):
        gap = current.start - previous.end
        if gap >= config.min_pause:
            pauses.append(
                PauseEntry(start=previous.end, end=current.start, kind=classify(gap))
            )

    trailing = total_duration - words[-1].end
    if trailing >= config.min_pause:
        pauses.append(
            PauseEntry(start=words[-1].end, end=total_duration, kind="trailing")
        )
    return pauses


def detect_speech_regions(
    words: list[WordEntry], total_duration: float, config: PipelineConfig
) -> tuple[list[SpeechRegion], list[SpeechRegion], float]:
    """Sliding-window speed analysis.

    Returns ``(fast_regions, slow_regions, overall_wpm)`` where regions
    are merged windows whose WPM deviates from the overall rate by the
    configured factors.
    """
    if not words or total_duration <= 0:
        return [], [], 0.0

    overall_wpm = len(words) / (total_duration / 60.0)
    window = config.region_window
    step = config.region_step
    midpoints = [(w.start + w.end) / 2.0 for w in words]

    # Classify each window: +1 fast, -1 slow, 0 normal.
    labelled: list[tuple[float, float, float, int]] = []
    t = 0.0
    while t < total_duration:
        end = min(t + window, total_duration)
        count = sum(1 for m in midpoints if t <= m < end)
        span_minutes = max(end - t, 1e-6) / 60.0
        wpm = count / span_minutes
        if count == 0:
            label = 0  # silence is a pause, not "slow speech"
        elif wpm >= overall_wpm * config.fast_factor:
            label = 1
        elif wpm <= overall_wpm * config.slow_factor:
            label = -1
        else:
            label = 0
        labelled.append((t, end, wpm, label))
        t += step

    fast = _merge_regions(labelled, 1, "fast", config.min_region_duration)
    slow = _merge_regions(labelled, -1, "slow", config.min_region_duration)
    return fast, slow, overall_wpm


def _merge_regions(
    windows: list[tuple[float, float, float, int]],
    target_label: int,
    kind: str,
    min_duration: float,
) -> list[SpeechRegion]:
    """Merge consecutive same-label windows into contiguous regions."""
    regions: list[SpeechRegion] = []
    run: list[tuple[float, float, float, int]] = []

    def flush() -> None:
        if not run:
            return
        start, end = run[0][0], run[-1][1]
        if end - start >= min_duration:
            avg_wpm = sum(w[2] for w in run) / len(run)
            regions.append(
                SpeechRegion(start=start, end=end, words_per_minute=avg_wpm, kind=kind)
            )
        run.clear()

    for window in windows:
        if window[3] == target_label:
            run.append(window)
        else:
            flush()
    flush()
    return regions


def compare_with_script(transcript: str, script_text: str) -> float:
    """Similarity ratio (0..1) between the transcript and the user script."""
    spoken = normalize_words(transcript)
    written = normalize_words(script_text)
    if not spoken or not written:
        return 0.0
    return difflib.SequenceMatcher(a=spoken, b=written, autojunk=False).ratio()


def build_analysis(
    words: list[WordEntry],
    sentences: list[SentenceEntry],
    pauses: list[PauseEntry],
    total_duration: float,
    language: str,
    config: PipelineConfig,
    script_text: str | None = None,
) -> AnalysisResult:
    """Aggregate every statistic exposed in ``analysis.json``."""
    fast_regions, slow_regions, overall_wpm = detect_speech_regions(
        words, total_duration, config
    )

    pause_durations = [p.duration for p in pauses]
    total_pause_time = sum(pause_durations)
    speech_time = max(total_duration - total_pause_time, 1e-6)

    emphasized = [
        {"word": w.word, "start": round(w.start, 3), "importance": w.importance}
        for w in words
        if w.importance in ("medium", "high")
    ]

    similarity: float | None = None
    if script_text and script_text.strip():
        transcript = " ".join(s.text for s in sentences)
        similarity = compare_with_script(transcript, script_text)
        logger.info("Script similarity: %.1f%%", similarity * 100)

    return AnalysisResult(
        total_duration=total_duration,
        language=language,
        word_count=len(words),
        sentence_count=len(sentences),
        words_per_minute=overall_wpm,
        articulation_wpm=len(words) / (speech_time / 60.0),
        pause_count=len(pauses),
        short_pause_count=sum(1 for p in pauses if p.kind == "short"),
        long_pause_count=sum(1 for p in pauses if p.kind == "long"),
        total_pause_time=total_pause_time,
        average_pause_duration=(
            total_pause_time / len(pauses) if pauses else 0.0
        ),
        longest_pause=max(pause_durations, default=0.0),
        fast_regions=fast_regions,
        slow_regions=slow_regions,
        emphasized_words=emphasized,
        script_similarity=similarity,
    )
