"""Text helpers: sentence-boundary detection and word normalization."""
from __future__ import annotations

import re

_TERMINAL_PUNCTUATION = ".!?…"
_CLOSING_CHARS = "\"'”’)]}»"
_WORD_RE = re.compile(r"[\w']+", re.UNICODE)

# Common abbreviations that end with a period but do NOT end a sentence.
_ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st.",
    "vs.", "etc.", "e.g.", "i.e.", "approx.", "no.", "fig.",
}


def ends_sentence(word: str) -> bool:
    """Return True when *word* terminates a sentence."""
    stripped = word.strip().rstrip(_CLOSING_CHARS)
    if not stripped:
        return False
    if stripped.lower() in _ABBREVIATIONS:
        return False
    # Initials such as "J." should not end a sentence.
    if len(stripped) == 2 and stripped[0].isupper() and stripped[1] == ".":
        return False
    return stripped[-1] in _TERMINAL_PUNCTUATION


def clean_word(word: str) -> str:
    """Trim whitespace while preserving punctuation for display."""
    return word.strip()


def normalize_words(text: str) -> list[str]:
    """Lowercased alphanumeric tokens, used for script comparison."""
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]
