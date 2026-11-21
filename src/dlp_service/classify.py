"""Classify pipeline: hash cache, lock, rules + Laya, path index."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from pathlib import Path

from dlp_service.extract import extract_text
from dlp_service.laya_pii import PiiDetector, entities_to_spans
from dlp_service.state import ClassifyRecord
from dlp_service.store import ClassifyStore

log = logging.getLogger("dlp_service.classify")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def to_rel(path: str | None, files_root: Path) -> str | None:
    if not path:
        return None
    p = path.replace("\\", "/").lstrip("/")
    if p.startswith("files/"):
        p = p[len("files/") :]
    root = str(files_root).replace("\\", "/").rstrip("/")
    if p.startswith(root + "/"):
        p = p[len(root) + 1 :]
    elif p == root:
        p = ""
    if p.startswith("/files/"):
        p = p[len("/files/") :]
    elif p.startswith("files/"):
        p = p[len("files/") :]
    return p.lstrip("/")


class Classifier:
    def __init__(
        self,
        *,
        files_root: Path,
        store: ClassifyStore,
        detector: PiiDetector,
        lock_seconds: float = 30.0,
        threshold: float = 0.5,
        region: str = "US",
        laya_version: str = "unknown",
    ) -> None:
        self.files_root = files_root
        self.store = store
        self.detector = detector
        self.lock_seconds = lock_seconds
        self.threshold = threshold
        self.region = region
        self.laya_version = laya_version
        self._inflight: dict[str, threading.Event] = {}
        self._gate = threading.Lock()

    def resolve_path(self, rel: str) -> Path:
        # Prevent escape; files_root is trusted.
        target = (self.files_root / rel).resolve()
        root = self.files_root.resolve()
        if root != target and root not in target.parents:
            raise ValueError("path escape")
        return target

    def classify(
        self,
        *,
        path: str | None = None,
        content_hash: str | None = None,
    ) -> ClassifyRecord:
        rel = to_rel(path, self.files_root)
        if content_hash:
            cached = self.store.get_by_hash(content_hash)
            if cached and cached.status == "ready":
                cached.cache_hit = True
                if rel:
                    cached.path = rel
                return cached

        if rel:
            meta = self.store.get_path_meta(rel)
            if meta:
                h, phase, lock_until = meta
                if phase == "classifying" and lock_until and time.time() < lock_until:
                    return ClassifyRecord(
                        status="locked",
                        hash=h or content_hash,
                        path=rel,
                        phase="classifying",
                        cache_hit=False,
                    )
                if (
                    phase == "classifying"
                    and lock_until
                    and time.time() >= lock_until
                ):
                    rec = ClassifyRecord(
                        status="denied_timeout",
                        hash=h or content_hash,
                        path=rel,
                        phase="denied_timeout",
                        laya_version=self.laya_version,
                        cache_hit=False,
                    )
                    self.store.clear_path_lock(rel, phase="denied_timeout")
                    if h:
                        self.store.put_hash(h, rec)
                    return rec
                if h and phase == "ready":
                    cached = self.store.get_by_hash(h)
                    if cached:
                        cached.path = rel
                        return cached

        if not rel:
            if content_hash:
                cached = self.store.get_by_hash(content_hash)
                if cached:
                    return cached
            return ClassifyRecord(status="missing", hash=content_hash)

        try:
            target = self.resolve_path(rel)
        except ValueError:
            return ClassifyRecord(status="missing", path=rel, hash=content_hash)

        if not target.is_file():
            self.store.set_path(rel, phase="missing")
            return ClassifyRecord(status="missing", path=rel, hash=content_hash)

        return self._classify_file(rel, target, prefer_hash=content_hash)

    def _classify_file(
        self, rel: str, target: Path, *, prefer_hash: str | None
    ) -> ClassifyRecord:
        with self._gate:
            ev = self._inflight.get(rel)
            if ev is None:
                ev = threading.Event()
                self._inflight[rel] = ev
                owner = True
            else:
                owner = False

        if not owner:
            # Another thread is classifying; report locked so Flask polls.
            meta = self.store.get_path_meta(rel)
            h = meta[0] if meta else prefer_hash
            return ClassifyRecord(
                status="locked", hash=h, path=rel, phase="classifying", cache_hit=False
            )

        lock_until = time.time() + self.lock_seconds
        try:
            content_hash = prefer_hash or sha256_file(target)
            cached = self.store.get_by_hash(content_hash)
            if cached and cached.status == "ready":
                cached.cache_hit = True
                cached.path = rel
                self.store.set_path(
                    rel, phase="ready", content_hash=content_hash, lock_until=None
                )
                return cached

            self.store.set_path(
                rel,
                phase="classifying",
                content_hash=content_hash,
                lock_until=lock_until,
            )

            # Always finish the job once started. lock_until only tells waiters
            # when to give up; it must not discard a completed classification
            # (Laya on CPU often exceeds the waiter budget on cold files).
            text = extract_text(target)
            if not text.strip():
                rec = ClassifyRecord(
                    status="ready",
                    hash=content_hash,
                    label="limpio",
                    spans=[],
                    laya_version=self.laya_version,
                    cache_hit=False,
                    path=rel,
                    phase="ready",
                )
            else:
                detection = self.detector.detect(
                    text, threshold=self.threshold, region=self.region
                )
                spans = entities_to_spans(detection.entities)
                label = "con_pii" if spans else "limpio"
                rec = ClassifyRecord(
                    status="ready",
                    hash=content_hash,
                    label=label,
                    spans=spans,
                    laya_version=self.laya_version,
                    cache_hit=False,
                    path=rel,
                    phase="ready",
                )

            elapsed = time.time() - (lock_until - self.lock_seconds)
            if elapsed > self.lock_seconds:
                log.warning(
                    "classify %s finished in %.1fs (waiter budget %.1fs); caching ready",
                    rel,
                    elapsed,
                    self.lock_seconds,
                )

            self.store.put_hash(content_hash, rec)
            self.store.clear_path_lock(rel, phase="ready")
            return rec
        except Exception as exc:  # noqa: BLE001
            log.exception("classify failed for %s", rel)
            rec = ClassifyRecord(
                status="denied_timeout",
                hash=prefer_hash,
                path=rel,
                phase="denied_timeout",
                laya_version=self.laya_version,
                error=str(exc),
                cache_hit=False,
            )
            self.store.clear_path_lock(rel, phase="denied_timeout")
            return rec
        finally:
            with self._gate:
                done = self._inflight.pop(rel, None)
                if done is not None:
                    done.set()

    def invalidate(self, rel: str) -> None:
        self.store.set_path(rel, phase="pending", lock_until=None)
