"""Filesystem watcher with debounce before classify."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from dlp_service.classify import Classifier, to_rel

log = logging.getLogger("dlp_service.watcher")


class DebouncedWatcher:
    def __init__(
        self,
        *,
        files_root: Path,
        classifier: Classifier,
        debounce_seconds: float = 2.0,
    ) -> None:
        self.files_root = files_root.resolve()
        self.classifier = classifier
        self.debounce_seconds = debounce_seconds
        self._pending: dict[str, float] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._paused = threading.Event()
        # Start paused so startup batch owns classification without invalidate races.
        self._paused.set()
        self._observer = None
        self._timer_thread: threading.Thread | None = None

    def pause(self) -> None:
        self._paused.set()
        with self._lock:
            self._pending.clear()
        log.info("watcher paused")

    def resume(self) -> None:
        self._paused.clear()
        log.info("watcher resumed")

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    def start(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError as exc:
            raise RuntimeError(
                "watchdog is required for DLP file watching; pip install watchdog"
            ) from exc

        root = self.files_root
        classifier = self.classifier
        pending = self._pending
        lock = self._lock

        paused = self._paused

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):  # noqa: ANN001
                if paused.is_set():
                    return
                if event.is_directory:
                    return
                src = getattr(event, "dest_path", None) or event.src_path
                path = Path(src)
                try:
                    rel = str(path.resolve().relative_to(root)).replace("\\", "/")
                except ValueError:
                    return
                if path.name.startswith(".") or path.suffix == ".tmp":
                    return
                with lock:
                    pending[rel] = time.time()

        observer = Observer()
        observer.schedule(Handler(), str(self.files_root), recursive=True)
        observer.daemon = True
        observer.start()
        self._observer = observer
        self._timer_thread = threading.Thread(
            target=self._loop, name="dlp-debounce", daemon=True
        )
        self._timer_thread.start()
        log.info("watching %s (debounce=%.1ss)", self.files_root, self.debounce_seconds)

    def stop(self) -> None:
        self._stop.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
        if self._timer_thread is not None:
            self._timer_thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.wait(0.25):
            if self._paused.is_set():
                with self._lock:
                    self._pending.clear()
                continue
            due: list[str] = []
            now = time.time()
            with self._lock:
                for rel, ts in list(self._pending.items()):
                    if now - ts >= self.debounce_seconds:
                        due.append(rel)
                        self._pending.pop(rel, None)
            for rel in due:
                self._run(rel)

    def _run(self, rel: str) -> None:
        if self._paused.is_set():
            return
        self.classifier.invalidate(rel)
        path = self.files_root / rel
        if not path.is_file():
            return
        log.info("classify after debounce: %s", rel)
        threading.Thread(
            target=self._safe_classify,
            args=(rel,),
            name=f"dlp-cls-{rel[:32]}",
            daemon=True,
        ).start()

    def _safe_classify(self, rel: str) -> None:
        try:
            self.classifier.classify(path=rel)
        except Exception:  # noqa: BLE001
            log.exception("background classify failed: %s", rel)


def enqueue_path(watcher: DebouncedWatcher, abs_or_rel: str) -> None:
    rel = to_rel(abs_or_rel, watcher.files_root) or abs_or_rel
    with watcher._lock:
        watcher._pending[rel] = time.time()
