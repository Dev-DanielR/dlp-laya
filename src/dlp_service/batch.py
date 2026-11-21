"""Startup recovery: classify files not yet ready in the cache."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from dlp_service.batch_state import BatchState
from dlp_service.classify import Classifier

log = logging.getLogger("dlp_service.batch")

# How long to wait when another thread owns the file before retrying.
_LOCK_POLL_SECONDS = 0.5


def walk_files(root: Path) -> list[str]:
    out: list[str] = []
    if not root.is_dir():
        return out
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        out.append(rel)
    return sorted(out)


def _classify_until_settled(classifier: Classifier, rel: str) -> None:
    """Run classify, waiting out transient locks from a parallel owner."""
    deadline = time.time() + max(classifier.lock_seconds * 2.0, 60.0)
    while True:
        rec = classifier.classify(path=rel)
        if rec.status != "locked" and rec.phase != "classifying":
            return
        if time.time() >= deadline:
            log.warning("batch gave up waiting on lock for %s (status=%s)", rel, rec.status)
            return
        time.sleep(_LOCK_POLL_SECONDS)


def recover_missing(
    classifier: Classifier,
    *,
    background: bool = True,
    limit: int | None = None,
    batch_state: BatchState | None = None,
) -> None:
    root = classifier.files_root
    rels = walk_files(root)
    if limit is not None:
        rels = rels[:limit]
    state = batch_state or BatchState()

    def _run() -> None:
        state.start(len(rels))
        log.info("batch recovery: %d files under %s", len(rels), root)
        try:
            for rel in rels:
                meta = classifier.store.get_path_meta(rel)
                if meta and meta[1] == "ready" and meta[0]:
                    cached = classifier.store.get_by_hash(meta[0])
                    if cached and cached.status == "ready":
                        state.tick()
                        continue
                try:
                    _classify_until_settled(classifier, rel)
                except Exception:  # noqa: BLE001
                    log.exception("batch classify failed: %s", rel)
                finally:
                    state.tick()
            log.info("batch recovery finished")
        finally:
            state.finish()

    if background:
        threading.Thread(target=_run, name="dlp-batch", daemon=True).start()
    else:
        _run()
