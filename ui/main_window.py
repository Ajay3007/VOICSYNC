"""Main application window.

Wires the four panels together, owns the worker thread, and drains the
worker's event queue on the UI thread via ``after()`` polling — the only
thread-safe way to update tkinter widgets.
"""
from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import time
from pathlib import Path

import customtkinter as ctk

from engine import PipelineConfig
from exporters import (
    ClaudePromptExporter,
    CsvExporter,
    JsonExporter,
    SrtExporter,
    TimelineExporter,
    export_all,
)
from models import Timeline
from ui import theme
from ui.bottom_bar import BottomBar
from ui.center_panel import CenterPanel
from ui.left_panel import LeftPanel
from ui.right_panel import RightPanel
from ui.worker import PipelineWorker, UiEvent

logger = logging.getLogger(__name__)

_POLL_INTERVAL_MS = 100
_CLOCK_INTERVAL_MS = 500
_MIN_FRACTION_FOR_ETA = 0.05


class MainWindow(ctk.CTk):
    """voice-sync desktop application."""

    def __init__(self, project_root: Path) -> None:
        super().__init__(fg_color=theme.COLOR_BG)
        self._project_root = project_root
        self._default_output = project_root / "output"
        self._default_output.mkdir(parents=True, exist_ok=True)

        self._events: "queue.Queue[UiEvent]" = queue.Queue()
        self._worker: PipelineWorker | None = None
        self._timeline: Timeline | None = None
        self._run_started_at: float | None = None
        self._last_fraction: float = 0.0

        self._configure_window()
        self._build_layout()
        self._poll_events()
        self._tick_clock()

    # ------------------------------------------------------------------ #
    # window setup
    # ------------------------------------------------------------------ #

    def _configure_window(self) -> None:
        self.title("voice-sync — Voiceover Timeline Generator")
        self.geometry("1280x760")
        self.minsize(1080, 640)
        ctk.set_appearance_mode("dark")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=270)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=280)
        self.grid_rowconfigure(0, weight=1)

        self.left = LeftPanel(
            self,
            default_output_dir=self._default_output,
            on_start=self._start_pipeline,
            on_cancel=self._cancel_pipeline,
        )
        self.left.grid(
            row=0, column=0, sticky="nsew", padx=(theme.PAD, 0), pady=theme.PAD
        )

        self.center = CenterPanel(self)
        self.center.grid(
            row=0, column=1, sticky="nsew", padx=theme.PAD, pady=theme.PAD
        )

        self.right = RightPanel(self)
        self.right.grid(
            row=0, column=2, sticky="nsew", padx=(0, theme.PAD), pady=theme.PAD
        )

        self.bottom = BottomBar(
            self,
            on_export_json=lambda: self._export_single(JsonExporter()),
            on_export_csv=lambda: self._export_single(CsvExporter()),
            on_export_srt=lambda: self._export_single(SrtExporter()),
            on_copy_prompt=self._copy_claude_prompt,
            on_open_folder=self._open_output_folder,
        )
        self.bottom.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=theme.PAD,
            pady=(0, theme.PAD),
        )

        self.center.log("voice-sync ready.", "SUCCESS")
        self.center.log(
            "1. Upload an audio file   2. (Optional) upload the script   "
            "3. Pick model + language   4. Start.",
            "DEBUG",
        )

    # ------------------------------------------------------------------ #
    # pipeline control
    # ------------------------------------------------------------------ #

    def _start_pipeline(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        if self.left.audio_path is None:
            self.center.log("Please select an audio file first.", "WARNING")
            self.center.set_status("No audio file selected.", theme.COLOR_WARNING)
            return

        config = PipelineConfig(
            audio_path=self.left.audio_path,
            script_path=self.left.script_path,
            output_dir=self.left.output_dir,
            model_name=self.left.model_name,
            language=self.left.language_code,
        )
        try:
            config.validate()
        except ValueError as exc:
            self.center.log(str(exc), "ERROR")
            self.center.set_status(str(exc), theme.COLOR_ERROR)
            return

        self._timeline = None
        self._last_fraction = 0.0
        self._run_started_at = time.monotonic()
        self.left.set_running(True)
        self.bottom.set_enabled(False)
        self.right.clear()
        self.center.clear_log()
        self.center.reset()
        self.center.log(f"Processing {config.audio_path.name}…", "INFO")

        self._worker = PipelineWorker(config, self._events)
        self._worker.start()

    def _cancel_pipeline(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            self._worker.cancel()
            self.left.set_cancelling()
            self.center.set_status("Cancelling…", theme.COLOR_WARNING)

    # ------------------------------------------------------------------ #
    # event pump (UI thread)
    # ------------------------------------------------------------------ #

    def _poll_events(self) -> None:
        try:
            while True:
                event = self._events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(_POLL_INTERVAL_MS, self._poll_events)

    def _handle_event(self, event: UiEvent) -> None:
        if event.kind == "log":
            message, level = event.payload
            self.center.log(str(message), str(level))
        elif event.kind == "progress":
            fraction, message = event.payload
            self._last_fraction = float(fraction)
            self.center.set_progress(self._last_fraction, str(message))
        elif event.kind == "done":
            (timeline,) = event.payload
            self._finish_run(timeline)
        elif event.kind == "cancelled":
            self._end_run()
            self.center.set_progress(0.0, "Cancelled.")
            self.center.log("Run cancelled.", "WARNING")
        elif event.kind == "error":
            (message,) = event.payload
            self._end_run()
            self.center.set_status(str(message), theme.COLOR_ERROR)
            self.center.log(f"ERROR: {message}", "ERROR")

    def _finish_run(self, timeline: Timeline) -> None:
        self._end_run()
        self._timeline = timeline
        self.center.set_progress(1.0, "Done.")
        self.right.show_analysis(timeline.analysis)
        self.bottom.set_enabled(True)

        # Write every format immediately; buttons re-export on demand.
        try:
            written = export_all(timeline, self.left.output_dir)
            self.center.log("All exports written:", "SUCCESS")
            for path in written:
                self.center.log(f"  • {path}", "INFO")
        except Exception as exc:  # noqa: BLE001 - report, don't crash the UI
            self.center.log(f"Export failed: {exc}", "ERROR")

        self.center.log(
            f"Finished: {timeline.analysis.word_count} words, "
            f"{timeline.analysis.sentence_count} sentences, "
            f"{timeline.analysis.pause_count} pauses.",
            "SUCCESS",
        )

    def _end_run(self) -> None:
        self._run_started_at = None
        self.left.set_running(False)

    # ------------------------------------------------------------------ #
    # clock
    # ------------------------------------------------------------------ #

    def _tick_clock(self) -> None:
        if self._run_started_at is not None:
            elapsed = time.monotonic() - self._run_started_at
            eta: float | None = None
            if self._last_fraction >= _MIN_FRACTION_FOR_ETA:
                eta = elapsed * (1.0 - self._last_fraction) / self._last_fraction
            self.center.update_times(elapsed, eta)
        self.after(_CLOCK_INTERVAL_MS, self._tick_clock)

    # ------------------------------------------------------------------ #
    # export actions
    # ------------------------------------------------------------------ #

    def _export_single(self, exporter: TimelineExporter) -> None:
        if self._timeline is None:
            return
        try:
            path = exporter.export(self._timeline, self.left.output_dir)
            self.center.log(f"{exporter.label} exported: {path}", "SUCCESS")
        except Exception as exc:  # noqa: BLE001
            self.center.log(f"{exporter.label} export failed: {exc}", "ERROR")

    def _copy_claude_prompt(self) -> None:
        if self._timeline is None:
            return
        try:
            prompt = ClaudePromptExporter().render(self._timeline)
            self.clipboard_clear()
            self.clipboard_append(prompt)
            self.center.log(
                f"Claude prompt copied to clipboard ({len(prompt):,} characters).",
                "SUCCESS",
            )
        except Exception as exc:  # noqa: BLE001
            self.center.log(f"Could not copy prompt: {exc}", "ERROR")

    def _open_output_folder(self) -> None:
        folder = self.left.output_dir
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])  # noqa: S603, S607
            else:
                subprocess.Popen(["xdg-open", str(folder)])  # noqa: S603, S607
        except OSError as exc:
            self.center.log(f"Could not open folder: {exc}", "ERROR")

    # ------------------------------------------------------------------ #
    # shutdown
    # ------------------------------------------------------------------ #

    def _on_close(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            self._worker.cancel()
        self.destroy()
