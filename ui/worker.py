"""Background pipeline execution.

The worker thread runs the pipeline and communicates with the UI thread
exclusively through a thread-safe :class:`queue.Queue` of
:class:`UiEvent` tuples.  The UI drains the queue with ``after()``
polling, so tkinter objects are only ever touched on the main thread and
the window never freezes.
"""
from __future__ import annotations

import logging
import queue
import threading
import traceback
from typing import Any, NamedTuple

from engine import (
    EngineError,
    PipelineCancelled,
    PipelineConfig,
    VoicePipeline,
    WhisperXEngine,
)
from utils.logging_config import CallbackLogHandler

logger = logging.getLogger(__name__)


class UiEvent(NamedTuple):
    """One message from the worker to the UI thread."""

    kind: str  # "log" | "progress" | "done" | "error" | "cancelled"
    payload: tuple[Any, ...]


class PipelineWorker(threading.Thread):
    """Runs :class:`VoicePipeline` off the UI thread."""

    def __init__(self, config: PipelineConfig, events: "queue.Queue[UiEvent]") -> None:
        super().__init__(name="voice-sync-pipeline", daemon=True)
        self._config = config
        self._events = events
        self._cancel_flag = threading.Event()

    # ------------------------------------------------------------------ #
    # control
    # ------------------------------------------------------------------ #

    def cancel(self) -> None:
        """Request cooperative cancellation."""
        self._cancel_flag.set()

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_flag.is_set()

    # ------------------------------------------------------------------ #
    # thread body
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        log_handler = CallbackLogHandler(
            lambda message, level: self._events.put(UiEvent("log", (message, level)))
        )
        log_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(log_handler)
        try:
            pipeline = VoicePipeline(WhisperXEngine())
            timeline = pipeline.run(
                self._config,
                progress=self._on_progress,
                cancel=self._cancel_flag.is_set,
            )
            self._events.put(UiEvent("done", (timeline,)))
        except PipelineCancelled:
            logger.info("Pipeline cancelled by user.")
            self._events.put(UiEvent("cancelled", ()))
        except (EngineError, ValueError) as exc:
            logger.error("%s", exc)
            self._events.put(UiEvent("error", (str(exc),)))
        except Exception as exc:  # noqa: BLE001 - never kill the UI silently
            logger.error("Unexpected failure:\n%s", traceback.format_exc())
            self._events.put(UiEvent("error", (f"Unexpected error: {exc}",)))
        finally:
            logging.getLogger().removeHandler(log_handler)

    def _on_progress(self, fraction: float, message: str) -> None:
        self._events.put(UiEvent("progress", (fraction, message)))
