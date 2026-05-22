"""BackgroundWorker: runs a single callable in a daemon thread."""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Runs a task function in a background daemon thread and reports errors via queue."""

    def __init__(self, result_queue: queue.Queue) -> None:
        self._queue = result_queue
        self._thread: threading.Thread | None = None

    def start(self, task_fn: Callable, *args: Any) -> None:
        """Start *task_fn* in a daemon thread.  Captures unexpected exceptions."""
        if self.is_running():
            logger.warning("BackgroundWorker: already running, ignoring start()")
            return

        def _run() -> None:
            try:
                task_fn(*args)
            except Exception as exc:  # noqa: BLE001
                logger.exception("BackgroundWorker: unexpected error: %s", exc)
                self._queue.put(("update_error", str(exc)))

        self._thread = threading.Thread(target=_run, daemon=True, name="midas-worker")
        self._thread.start()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
