"""Structured audit log lines (no file body / no span text)."""

from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


class AuditLogger:
    def __init__(self, path: str = "-") -> None:
        self._path = path
        self._lock = threading.Lock()
        self._fp: TextIO | None = None
        if path != "-":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._fp = open(path, "a", encoding="utf-8")  # noqa: SIM115

    def close(self) -> None:
        with self._lock:
            if self._fp is not None:
                self._fp.close()
                self._fp = None

    def write(self, event: dict[str, Any]) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        # Hard strip accidental sensitive keys
        for banned in ("body", "spans", "content", "token", "authorization"):
            payload.pop(banned, None)
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            dest = self._fp if self._fp is not None else sys.stdout
            dest.write(line + "\n")
            dest.flush()
