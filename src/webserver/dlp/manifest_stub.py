"""Manifest-backed DLP stub for lab runs without a live DLP service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from webserver.dlp.base import ClassifyResult, DlpPathStatus, DlpProgress


class ManifestDlpStub:
    def __init__(self, manifest_path: Path, *, content_hash: str | None = None) -> None:
        self._manifest_path = manifest_path
        self._by_path: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        for rec in data.get("files") or []:
            rel = str(rec.get("path", "")).replace("\\", "/").lstrip("/")
            if rel:
                self._by_path[rel] = rec

    def classify(
        self,
        *,
        path: str | None = None,
        content_hash: str | None = None,
    ) -> ClassifyResult:
        rel = _to_rel(path)
        if not rel or rel not in self._by_path:
            return ClassifyResult(status="missing", hash=content_hash)
        rec = self._by_path[rel]
        spans = list(rec.get("expected_spans") or [])
        return ClassifyResult(
            status="ready",
            hash=content_hash,
            label=str(rec.get("label", "limpio")),
            spans=spans,
            laya_version="manifest-stub",
            cache_hit=True,
            raw={"id": rec.get("id"), "path": rel},
        )

    def progress(self) -> DlpProgress:
        total = len(self._by_path)
        return DlpProgress(
            total=total,
            done=total,
            classifying=0,
            pending=0,
            denied_timeout=0,
            missing=0,
            batch_running=False,
            complete=True,
            model_ready=True,
            model_loading=False,
            model_error=None,
            raw={"mode": "stub"},
        )

    def statuses(
        self,
        *,
        paths: list[str] | None = None,
        prefix: str | None = None,
    ) -> list[DlpPathStatus]:
        if paths is not None:
            wanted = paths
        else:
            pref = (prefix or "").strip("/")
            wanted = []
            for rel in sorted(self._by_path):
                if not pref:
                    if "/" not in rel:
                        wanted.append(rel)
                elif rel.startswith(pref + "/") and "/" not in rel[len(pref) + 1 :]:
                    wanted.append(rel)
        items: list[DlpPathStatus] = []
        for rel in wanted:
            rec = self._by_path.get(rel)
            if rec is None:
                items.append(DlpPathStatus(path=rel, phase="pending", label=None))
            else:
                items.append(
                    DlpPathStatus(
                        path=rel,
                        phase="ready",
                        label=str(rec.get("label", "limpio")),
                    )
                )
        return items


def _to_rel(path: str | None) -> str | None:
    if not path:
        return None
    p = path.replace("\\", "/")
    if p.startswith("/files/"):
        p = p[len("/files/") :]
    elif p == "/files":
        p = ""
    return p.lstrip("/")
