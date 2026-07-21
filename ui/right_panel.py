"""Right panel: narration statistics."""
from __future__ import annotations

import customtkinter as ctk

from models import AnalysisResult
from ui import theme
from utils.time_format import format_clock

_PLACEHOLDER = "—"


class RightPanel(ctk.CTkFrame):
    """Read-only statistics column, filled after each run."""

    _ROWS: tuple[tuple[str, str], ...] = (
        ("duration", "Total duration"),
        ("words", "Word count"),
        ("sentences", "Sentence count"),
        ("wpm", "Speaking speed"),
        ("articulation", "Articulation speed"),
        ("pauses", "Pauses"),
        ("avg_pause", "Average pause"),
        ("longest_pause", "Longest pause"),
        ("fast", "Fast regions"),
        ("slow", "Slow regions"),
        ("emphasis", "Emphasized words"),
        ("similarity", "Script match"),
    )

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(
            master, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_PANEL
        )
        self._values: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        title = ctk.CTkLabel(
            self,
            text="Statistics",
            font=ctk.CTkFont(theme.FONT_FAMILY, 16, weight="bold"),
            anchor="w",
        )
        title.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=theme.PAD,
            pady=(theme.PAD, theme.PAD_SMALL),
        )

        for i, (key, label_text) in enumerate(self._ROWS, start=1):
            name = ctk.CTkLabel(
                self,
                text=label_text,
                font=ctk.CTkFont(theme.FONT_FAMILY, 12),
                text_color=theme.COLOR_TEXT_MUTED,
                anchor="w",
            )
            name.grid(row=i, column=0, sticky="w", padx=(theme.PAD, 4), pady=3)

            value = ctk.CTkLabel(
                self,
                text=_PLACEHOLDER,
                font=ctk.CTkFont(theme.FONT_MONO, 12, weight="bold"),
                anchor="e",
            )
            value.grid(row=i, column=1, sticky="e", padx=(4, theme.PAD), pady=3)
            self._values[key] = value

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def show_analysis(self, analysis: AnalysisResult) -> None:
        """Populate every statistic from a finished run."""
        self._set("duration", format_clock(analysis.total_duration))
        self._set("words", str(analysis.word_count))
        self._set("sentences", str(analysis.sentence_count))
        self._set("wpm", f"{analysis.words_per_minute:.0f} WPM")
        self._set("articulation", f"{analysis.articulation_wpm:.0f} WPM")
        self._set(
            "pauses",
            f"{analysis.pause_count} ({analysis.long_pause_count} long)",
        )
        self._set("avg_pause", f"{analysis.average_pause_duration:.2f}s")
        self._set("longest_pause", f"{analysis.longest_pause:.2f}s")
        self._set("fast", str(len(analysis.fast_regions)))
        self._set("slow", str(len(analysis.slow_regions)))
        self._set("emphasis", str(len(analysis.emphasized_words)))
        if analysis.script_similarity is not None:
            self._set("similarity", f"{analysis.script_similarity * 100:.1f}%")
        else:
            self._set("similarity", _PLACEHOLDER)

    def clear(self) -> None:
        for value in self._values.values():
            value.configure(text=_PLACEHOLDER)

    def _set(self, key: str, text: str) -> None:
        self._values[key].configure(text=text)
