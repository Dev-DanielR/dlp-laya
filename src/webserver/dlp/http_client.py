"""HTTP client for the localhost DLP classify API."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from webserver.dlp.base import ClassifyResult


class HttpDlpClient:
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def classify(
        self,
        *,
        path: str | None = None,
        content_hash: str | None = None,
    ) -> ClassifyResult:
        params: dict[str, str] = {}
        if path:
            params["path"] = path
        if content_hash:
            params["hash"] = content_hash
        url = f"{self.base_url}/classify"
        if params:
            url = f"{url}?{urlencode(params)}"
        resp = requests.get(url, timeout=self.timeout)
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
    last = client.classify(path=path, content_hash=content_hash)
    if last.status != "locked":
        return last, 0.0

    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        last = client.classify(path=path, content_hash=content_hash)
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
