"""Left panel: inputs, model/language selection, output folder, start."""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from engine import AVAILABLE_LANGUAGES, AVAILABLE_MODELS, SUPPORTED_AUDIO_EXTENSIONS
from ui import theme

_AUDIO_FILETYPES = [
    ("Audio files", " ".join(f"*{ext}" for ext in SUPPORTED_AUDIO_EXTENSIONS)),
    ("All files", "*.*"),
]
_SCRIPT_FILETYPES = [("Text files", "*.txt *.md"), ("All files", "*.*")]


class LeftPanel(ctk.CTkFrame):
    """Input configuration column."""

    def __init__(
        self,
        master: ctk.CTk,
        *,
        default_output_dir: Path,
        on_start: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__(
            master, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_PANEL
        )
        self._on_start = on_start
        self._on_cancel = on_cancel

        self.audio_path: Path | None = None
        self.script_path: Path | None = None
        self.output_dir: Path = default_output_dir

        self._build()

    # ------------------------------------------------------------------ #
    # public API used by MainWindow
    # ------------------------------------------------------------------ #

    @property
    def model_name(self) -> str:
        return self._model_menu.get()

    @property
    def language_code(self) -> str | None:
        return AVAILABLE_LANGUAGES.get(self._language_menu.get())

    def set_running(self, running: bool) -> None:
        """Toggle between Start and Cancel modes."""
        if running:
            self._start_button.configure(
                text="✕  Cancel",
                fg_color=theme.COLOR_ERROR,
                hover_color="#b91c1c",
                command=self._on_cancel,
            )
        else:
            self._start_button.configure(
                text="▶  Start Processing",
                fg_color=theme.COLOR_ACCENT,
                hover_color=theme.COLOR_ACCENT_HOVER,
                command=self._handle_start,
                state="normal",
            )
        for widget in (
            self._audio_button,
            self._script_button,
            self._script_clear,
            self._model_menu,
            self._language_menu,
            self._output_button,
        ):
            widget.configure(state="disabled" if running else "normal")

    def set_cancelling(self) -> None:
        self._start_button.configure(text="Cancelling…", state="disabled")

    # ------------------------------------------------------------------ #
    # layout
    # ------------------------------------------------------------------ #

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        pad = {"padx": theme.PAD, "pady": (theme.PAD_SMALL, 0)}
        row = 0

        title = ctk.CTkLabel(
            self,
            text="Input",
            font=ctk.CTkFont(theme.FONT_FAMILY, 16, weight="bold"),
            anchor="w",
        )
        title.grid(row=row, column=0, sticky="ew", padx=theme.PAD, pady=(theme.PAD, 0))
        row += 1

        # --- audio -------------------------------------------------------
        self._audio_button = ctk.CTkButton(
            self, text="🎵  Upload Audio", command=self._pick_audio
        )
        self._audio_button.grid(row=row, column=0, sticky="ew", **pad)
        row += 1
        self._audio_label = self._file_label("No audio selected")
        self._audio_label.grid(row=row, column=0, sticky="ew", padx=theme.PAD)
        row += 1

        # --- script ------------------------------------------------------
        self._script_button = ctk.CTkButton(
            self,
            text="📄  Upload Script (optional)",
            command=self._pick_script,
            fg_color=theme.COLOR_PANEL_ALT,
            hover_color=theme.COLOR_BORDER,
        )
        self._script_button.grid(row=row, column=0, sticky="ew", **pad)
        row += 1
        self._script_label = self._file_label("No script selected")
        self._script_label.grid(row=row, column=0, sticky="ew", padx=theme.PAD)
        row += 1
        self._script_clear = ctk.CTkButton(
            self,
            text="Clear script",
            width=90,
            height=22,
            command=self._clear_script,
            fg_color="transparent",
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_MUTED,
        )
        self._script_clear.grid(row=row, column=0, sticky="w", padx=theme.PAD)
        row += 1

        # --- model -------------------------------------------------------
        row = self._section_label("Model", row)
        self._model_menu = ctk.CTkOptionMenu(self, values=list(AVAILABLE_MODELS))
        self._model_menu.set("small")
        self._model_menu.grid(row=row, column=0, sticky="ew", **pad)
        row += 1
        hint = ctk.CTkLabel(
            self,
            text="tiny = fastest · large-v3 = most accurate",
            font=ctk.CTkFont(theme.FONT_FAMILY, 11),
            text_color=theme.COLOR_TEXT_MUTED,
            anchor="w",
        )
        hint.grid(row=row, column=0, sticky="ew", padx=theme.PAD)
        row += 1

        # --- language ----------------------------------------------------
        row = self._section_label("Language", row)
        self._language_menu = ctk.CTkOptionMenu(
            self, values=list(AVAILABLE_LANGUAGES.keys())
        )
        self._language_menu.set("Auto detect")
        self._language_menu.grid(row=row, column=0, sticky="ew", **pad)
        row += 1

        # --- output ------------------------------------------------------
        row = self._section_label("Export Folder", row)
        self._output_button = ctk.CTkButton(
            self,
            text="📁  Choose Folder",
            command=self._pick_output,
            fg_color=theme.COLOR_PANEL_ALT,
            hover_color=theme.COLOR_BORDER,
        )
        self._output_button.grid(row=row, column=0, sticky="ew", **pad)
        row += 1
        self._output_label = self._file_label(str(self.output_dir))
        self._output_label.grid(row=row, column=0, sticky="ew", padx=theme.PAD)
        row += 1

        # --- start -------------------------------------------------------
        self.grid_rowconfigure(row, weight=1)  # spacer pushes button down
        row += 1
        self._start_button = ctk.CTkButton(
            self,
            text="▶  Start Processing",
            height=44,
            font=ctk.CTkFont(theme.FONT_FAMILY, 15, weight="bold"),
            fg_color=theme.COLOR_ACCENT,
            hover_color=theme.COLOR_ACCENT_HOVER,
            command=self._handle_start,
        )
        self._start_button.grid(
            row=row, column=0, sticky="ew", padx=theme.PAD, pady=theme.PAD
        )

    def _section_label(self, text: str, row: int) -> int:
        label = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(theme.FONT_FAMILY, 13, weight="bold"),
            anchor="w",
        )
        label.grid(
            row=row, column=0, sticky="ew", padx=theme.PAD, pady=(theme.PAD, 0)
        )
        return row + 1

    def _file_label(self, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(theme.FONT_FAMILY, 11),
            text_color=theme.COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=220,
            justify="left",
        )

    # ------------------------------------------------------------------ #
    # actions
    # ------------------------------------------------------------------ #

    def _pick_audio(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Select voiceover audio", filetypes=_AUDIO_FILETYPES
        )
        if chosen:
            self.audio_path = Path(chosen)
            self._audio_label.configure(
                text=self.audio_path.name, text_color=theme.COLOR_SUCCESS
            )

    def _pick_script(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Select script (optional)", filetypes=_SCRIPT_FILETYPES
        )
        if chosen:
            self.script_path = Path(chosen)
            self._script_label.configure(
                text=self.script_path.name, text_color=theme.COLOR_SUCCESS
            )

    def _clear_script(self) -> None:
        self.script_path = None
        self._script_label.configure(
            text="No script selected", text_color=theme.COLOR_TEXT_MUTED
        )

    def _pick_output(self) -> None:
        chosen = filedialog.askdirectory(title="Select export folder")
        if chosen:
            self.output_dir = Path(chosen)
            self._output_label.configure(text=str(self.output_dir))

    def _handle_start(self) -> None:
        self._on_start()
