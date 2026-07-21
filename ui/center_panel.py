"""Center panel: live log, progress bar, status, elapsed / remaining time."""
from __future__ import annotations

import customtkinter as ctk

from ui import theme
from utils.time_format import format_clock

_MAX_LOG_LINES = 2000


class CenterPanel(ctk.CTkFrame):
    """Live processing feedback."""

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(
            master, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_PANEL
        )
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="Processing Log",
            font=ctk.CTkFont(theme.FONT_FAMILY, 16, weight="bold"),
            anchor="w",
        )
        title.grid(
            row=0, column=0, sticky="ew", padx=theme.PAD, pady=(theme.PAD, 0)
        )

        self._log = ctk.CTkTextbox(
            self,
            fg_color=theme.COLOR_BG,
            text_color=theme.COLOR_TEXT,
            font=ctk.CTkFont(theme.FONT_MONO, 12),
            wrap="word",
            state="disabled",
        )
        self._log.grid(
            row=1, column=0, sticky="nsew", padx=theme.PAD, pady=theme.PAD_SMALL
        )
        for level, color in theme.LOG_COLORS.items():
            self._log.tag_config(level, foreground=color)

        self._status_label = ctk.CTkLabel(
            self,
            text="Ready. Select an audio file and press Start.",
            font=ctk.CTkFont(theme.FONT_FAMILY, 12),
            text_color=theme.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self._status_label.grid(row=2, column=0, sticky="ew", padx=theme.PAD)

        self._progress = ctk.CTkProgressBar(
            self, progress_color=theme.COLOR_ACCENT, height=12
        )
        self._progress.set(0.0)
        self._progress.grid(
            row=3, column=0, sticky="ew", padx=theme.PAD, pady=theme.PAD_SMALL
        )

        time_row = ctk.CTkFrame(self, fg_color="transparent")
        time_row.grid(
            row=4, column=0, sticky="ew", padx=theme.PAD, pady=(0, theme.PAD)
        )
        time_row.grid_columnconfigure((0, 1, 2), weight=1)

        self._percent_label = self._time_label(time_row, "0%")
        self._percent_label.grid(row=0, column=0, sticky="w")
        self._elapsed_label = self._time_label(time_row, "Elapsed  00:00")
        self._elapsed_label.grid(row=0, column=1)
        self._eta_label = self._time_label(time_row, "Remaining  --:--")
        self._eta_label.grid(row=0, column=2, sticky="e")

    @staticmethod
    def _time_label(master: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            master,
            text=text,
            font=ctk.CTkFont(theme.FONT_MONO, 12),
            text_color=theme.COLOR_TEXT_MUTED,
        )

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def log(self, message: str, level: str = "INFO") -> None:
        """Append one line to the live log (main thread only)."""
        tag = level if level in theme.LOG_COLORS else "INFO"
        self._log.configure(state="normal")
        self._log.insert("end", message.rstrip() + "\n", tag)
        # Trim so multi-hour sessions never bloat the widget.
        lines = int(self._log.index("end-1c").split(".")[0])
        if lines > _MAX_LOG_LINES:
            self._log.delete("1.0", f"{lines - _MAX_LOG_LINES}.0")
        self._log.see("end")
        self._log.configure(state="disabled")

    def clear_log(self) -> None:
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def set_progress(self, fraction: float, status: str) -> None:
        fraction = min(max(fraction, 0.0), 1.0)
        self._progress.set(fraction)
        self._percent_label.configure(text=f"{fraction * 100:.0f}%")
        self._status_label.configure(text=status, text_color=theme.COLOR_TEXT)

    def set_status(self, status: str, color: str = theme.COLOR_TEXT_MUTED) -> None:
        self._status_label.configure(text=status, text_color=color)

    def update_times(self, elapsed: float, eta: float | None) -> None:
        self._elapsed_label.configure(text=f"Elapsed  {format_clock(elapsed)}")
        remaining = format_clock(eta) if eta is not None else "--:--"
        self._eta_label.configure(text=f"Remaining  {remaining}")

    def reset(self) -> None:
        self.set_progress(0.0, "Starting…")
        self.update_times(0.0, None)
