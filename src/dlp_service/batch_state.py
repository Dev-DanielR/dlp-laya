"""Thread-safe counters for startup batch recovery progress."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class BatchSnapshot:
    running: bool
    total: int
    finished: int


class BatchState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._total = 0
        self._finished = 0

    def start(self, total: int) -> None:
        with self._lock:
            self._running = True
            self._total = max(0, int(total))
            self._finished = 0

    def tick(self) -> None:
        with self._lock:
            self._finished += 1

    def finish(self) -> None:
        with self._lock:
            self._running = False
            if self._finished < self._total:
                self._finished = self._total

    def snapshot(self) -> BatchSnapshot:
        with self._lock:
            return BatchSnapshot(
                running=self._running,
                total=self._total,
                finished=self._finished,
            )
