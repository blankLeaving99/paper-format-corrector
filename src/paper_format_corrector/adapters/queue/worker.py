"""Minimal worker placeholder."""
from __future__ import annotations
import threading
from typing import Any


class Worker:
    """Simple worker that processes tasks from a queue."""

    def __init__(self, task_queue: Any, num_workers: int = 1) -> None:
        self._queue = task_queue
        self._num_workers = num_workers
        self._threads: list[threading.Thread] = []
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
