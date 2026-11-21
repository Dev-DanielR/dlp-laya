"""HTTP client for the localhost DLP classify API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from webserver.dlp.base import ClassifyResult, DlpPathStatus, DlpProgress

_PHASES = {"pending", "classifying", "ready", "denied_timeout", "missing"}


class HttpDlpClient:
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def classify(
        self,
        *,
        path: str | None = None,
        content_hash: str | None = None,
        timeout: float | None = None,
    ) -> ClassifyResult:
        params: dict[str, str] = {}
        if path:
            params["path"] = path
        if content_hash:
            params["hash"] = content_hash
        url = f"{self.base_url}/classify"
        if params:
            url = f"{url}?{urlencode(params)}"
        # Owner requests block inside DLP until Laya finishes; allow a long read.
        resp = requests.get(url, timeout=timeout if timeout is not None else self.timeout)
        if resp.status_code == 404:
            return ClassifyResult(status="missing", hash=content_hash)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        status = str(payload.get("status", "missing"))
        if status not in {"ready", "locked", "denied_timeout", "missing"}:
            status = "missing"
        return ClassifyResult(
            status=status,  # type: ignore[arg-type]
            hash=payload.get("hash") or content_hash,
            label=payload.get("label"),
            spans=list(payload.get("spans") or []),
            laya_version=payload.get("laya_version"),
            cache_hit=payload.get("cache_hit"),
            raw=payload,
        )

    def progress(self) -> DlpProgress:
        resp = requests.get(f"{self.base_url}/progress", timeout=self.timeout)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        return DlpProgress(
            total=int(payload.get("total") or 0),
            done=int(payload.get("done") or 0),
            classifying=int(payload.get("classifying") or 0),
            pending=int(payload.get("pending") or 0),
            denied_timeout=int(payload.get("denied_timeout") or 0),
            missing=int(payload.get("missing") or 0),
            batch_running=bool(payload.get("batch_running")),
            complete=bool(payload.get("complete")),
            model_ready=bool(payload.get("model_ready", True)),
            model_loading=bool(payload.get("model_loading", False)),
            model_error=payload.get("model_error"),
            raw=payload,
        )

    def statuses(
        self,
        *,
        paths: list[str] | None = None,
        prefix: str | None = None,
    ) -> list[DlpPathStatus]:
        params: dict[str, str] = {}
        if paths:
            params["paths"] = ",".join(paths)
        elif prefix is not None:
            params["prefix"] = prefix
        url = f"{self.base_url}/statuses"
        if params:
            url = f"{url}?{urlencode(params)}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        items: list[DlpPathStatus] = []
        for raw in payload.get("items") or []:
            phase = str(raw.get("phase") or "pending")
            if phase not in _PHASES:
                phase = "pending"
            items.append(
                DlpPathStatus(
                    path=str(raw.get("path") or ""),
                    phase=phase,  # type: ignore[arg-type]
                    label=raw.get("label"),
                )
            )
        return items



def wait_for_ready(
    client: Any,
    *,
    path: str | None,
    content_hash: str | None,
    wait_seconds: float,
    poll_interval: float = 0.25,
) -> tuple[ClassifyResult, float]:
    """Poll classify until ready / denied_timeout / missing or budget exhausted.

    Returns (result, lock_wait_ms).
    """
    import time

    deadline = time.monotonic() + max(0.0, wait_seconds)
    started = time.monotonic()
    # First call may own the classify job and block until Laya returns.
    owner_timeout = max(5.0, wait_seconds + 5.0)
    classify_kw = {"path": path, "content_hash": content_hash}
    if hasattr(client, "classify"):
        try:
            last = client.classify(**classify_kw, timeout=owner_timeout)
        except TypeError:
            last = client.classify(**classify_kw)
    else:
        last = client.classify(**classify_kw)
    if last.status != "locked":
        return last, 0.0

    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            last = client.classify(**classify_kw, timeout=min(5.0, max(1.0, deadline - time.monotonic())))
        except TypeError:
            last = client.classify(**classify_kw)
        if last.status != "locked":
            wait_ms = (time.monotonic() - started) * 1000.0
            return last, wait_ms

    wait_ms = (time.monotonic() - started) * 1000.0
    if last.status == "locked":
        return (
            ClassifyResult(
                status="denied_timeout",
                hash=content_hash,
                label=last.label,
                spans=last.spans,
                laya_version=last.laya_version,
                cache_hit=last.cache_hit,
                raw=last.raw,
            ),
            wait_ms,
        )
    return last, wait_ms
