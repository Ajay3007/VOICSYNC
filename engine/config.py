"""Pipeline configuration.

A single frozen-ish dataclass carries every knob from the UI into the
pipeline so that function signatures stay stable as options grow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_AUDIO_EXTENSIONS: tuple[str, ...] = (
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".ogg",
    ".aac",
    ".mpeg",  # MPEG audio (ElevenLabs / WhatsApp exports)
    ".mpga",
    ".opus",
    ".webm",
)

AVAILABLE_MODELS: tuple[str, ...] = (
    "tiny",
    "base",
    "small",
    "medium",
    "large-v2",
    "large-v3",
)

# "auto" lets WhisperX detect the language from the first 30 seconds.
AVAILABLE_LANGUAGES: dict[str, str | None] = {
    "Auto detect": None,
    "English (en)": "en",
    "Spanish (es)": "es",
    "French (fr)": "fr",
    "German (de)": "de",
    "Italian (it)": "it",
    "Portuguese (pt)": "pt",
    "Dutch (nl)": "nl",
    "Hindi (hi)": "hi",
    "Japanese (ja)": "ja",
    "Chinese (zh)": "zh",
    "Korean (ko)": "ko",
    "Russian (ru)": "ru",
    "Arabic (ar)": "ar",
    "Turkish (tr)": "tr",
    "Polish (pl)": "pl",
    "Ukrainian (uk)": "uk",
}


@dataclass(slots=True)
class PipelineConfig:
    """Everything a pipeline run needs to know."""

    audio_path: Path
    output_dir: Path
    script_path: Path | None = None
    model_name: str = "small"
    language: str | None = None  # None = auto detect
    device_preference: str = "auto"  # "auto" | "cuda" | "cpu"
    batch_size: int = 8

    # --- analysis thresholds -------------------------------------------------
    min_pause: float = 0.25          # gaps shorter than this are ignored
    long_pause: float = 0.60         # gaps >= this count as "long"
    sentence_gap: float = 1.00       # fallback sentence break when no punctuation
    region_window: float = 5.0       # sliding window (s) for speed regions
    region_step: float = 1.0         # window step (s)
    fast_factor: float = 1.25        # region is "fast" above avg_wpm * factor
    slow_factor: float = 0.75        # region is "slow" below avg_wpm * factor
    min_region_duration: float = 2.0

    # --- emphasis thresholds -------------------------------------------------
    emphasis_high: float = 0.90      # composite z-score for "high"
    emphasis_medium: float = 0.35    # composite z-score for "medium"

    extra: dict[str, object] = field(default_factory=dict)

    def validate(self) -> None:
        """Raise ``ValueError`` for unusable configuration."""
        if not self.audio_path.is_file():
            raise ValueError(f"Audio file not found: {self.audio_path}")
        if self.audio_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format '{self.audio_path.suffix}'. "
                f"Supported: {', '.join(SUPPORTED_AUDIO_EXTENSIONS)}"
            )
        if self.script_path is not None and not self.script_path.is_file():
            raise ValueError(f"Script file not found: {self.script_path}")
        if self.model_name not in AVAILABLE_MODELS:
            raise ValueError(f"Unknown model '{self.model_name}'")
