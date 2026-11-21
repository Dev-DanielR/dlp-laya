"""Startup batch vs watcher pause / lock-wait behaviour."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from dlp_service.batch import _classify_until_settled, recover_missing
from dlp_service.batch_state import BatchState
from dlp_service.classify import Classifier
from dlp_service.laya_pii import RulesOnlyDetector
from dlp_service.store import ClassifyStore
from dlp_service.watcher import DebouncedWatcher


def _classifier(tmp_path: Path, files_root: Path) -> Classifier:
    return Classifier(
        files_root=files_root,
        store=ClassifyStore(tmp_path / "cache.sqlite3"),
        detector=RulesOnlyDetector(),
        lock_seconds=5.0,
        laya_version="rules-only",
    )


def test_watcher_starts_paused(tmp_path: Path):
    root = tmp_path / "files"
    root.mkdir()
    (root / "a.txt").write_text("x@y.z\n", encoding="utf-8")
    clf = _classifier(tmp_path, root)
    w = DebouncedWatcher(files_root=root, classifier=clf, debounce_seconds=0.05)
    assert w.paused is True
    # While paused, _run must not invalidate / classify (no watchdog needed).
    w._run("a.txt")
    assert clf.store.get_path_meta("a.txt") is None
    w.resume()
    assert w.paused is False
    w._run("a.txt")
    deadline = time.time() + 3
    meta = None
    while time.time() < deadline:
        meta = clf.store.get_path_meta("a.txt")
        if meta and meta[1] == "ready":
            break
        time.sleep(0.05)
    assert meta is not None and meta[1] == "ready"


def test_batch_waits_out_lock(tmp_path: Path):
    root = tmp_path / "files"
    root.mkdir()
    (root / "a.txt").write_text("contact me@x.com please\n", encoding="utf-8")
    clf = _classifier(tmp_path, root)

    started = threading.Event()
    release = threading.Event()

    real_detect = clf.detector.detect

    def slow_detect(text, *, threshold=0.5, region="US"):
        started.set()
        release.wait(timeout=5)
        return real_detect(text, threshold=threshold, region=region)

    clf.detector.detect = slow_detect  # type: ignore[method-assign]

    def owner():
        clf.classify(path="a.txt")

    t = threading.Thread(target=owner, daemon=True)
    t.start()
    assert started.wait(timeout=2)
    # Parallel batch-style wait should block until owner finishes.
    waiter = threading.Thread(
        target=_classify_until_settled, args=(clf, "a.txt"), daemon=True
    )
    waiter.start()
    time.sleep(0.2)
    assert waiter.is_alive()
    release.set()
    waiter.join(timeout=5)
    t.join(timeout=5)
    assert not waiter.is_alive()
    meta = clf.store.get_path_meta("a.txt")
    assert meta is not None and meta[1] == "ready"


def test_recover_missing_completes(tmp_path: Path):
    root = tmp_path / "files"
    root.mkdir()
    (root / "a.txt").write_text("hi\n", encoding="utf-8")
    (root / "b.txt").write_text("x@y.z\n", encoding="utf-8")
    clf = _classifier(tmp_path, root)
    batch = BatchState()
    recover_missing(clf, background=False, batch_state=batch)
    snap = batch.snapshot()
    assert snap.running is False
    assert snap.finished == 2
    assert clf.store.get_path_meta("a.txt")[1] == "ready"
    assert clf.store.get_path_meta("b.txt")[1] == "ready"
