"""Bottom bar: export and utility buttons."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme


class BottomBar(ctk.CTkFrame):
    """Export actions, enabled once a timeline exists."""

    def __init__(
        self,
        master: ctk.CTk,
        *,
        on_export_json: Callable[[], None],
        on_export_csv: Callable[[], None],
        on_export_srt: Callable[[], None],
        on_copy_prompt: Callable[[], None],
        on_open_folder: Callable[[], None],
    ) -> None:
        super().__init__(
            master, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_PANEL
        )

        specs: tuple[tuple[str, Callable[[], None], bool], ...] = (
            ("⬇  Export JSON", on_export_json, True),
            ("⬇  Export CSV", on_export_csv, True),
            ("⬇  Export SRT", on_export_srt, True),
            ("📋  Copy Claude Prompt", on_copy_prompt, True),
            ("📂  Open Output Folder", on_open_folder, False),
        )

        self._export_buttons: list[ctk.CTkButton] = []
        for i, (label, command, needs_timeline) in enumerate(specs):
            button = ctk.CTkButton(
                self,
                text=label,
                command=command,
                fg_color=theme.COLOR_PANEL_ALT,
                hover_color=theme.COLOR_BORDER,
            )
            button.grid(
                row=0,
                column=i,
                sticky="ew",
                padx=(theme.PAD if i == 0 else theme.PAD_SMALL, theme.PAD_SMALL),
                pady=theme.PAD_SMALL,
            )
            self.grid_columnconfigure(i, weight=1)
            if needs_timeline:
                self._export_buttons.append(button)

        self.set_enabled(False)

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable buttons that require a finished timeline."""
        state = "normal" if enabled else "disabled"
        for button in self._export_buttons:
            button.configure(state=state)
