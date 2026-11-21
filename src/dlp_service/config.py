"""Environment-driven settings for the DLP daemon."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DlpSettings:
    files_root: Path
    bind_host: str
    bind_port: int
    cache_path: Path
    debounce_seconds: float
    lock_seconds: float
    laya_model: str
    laya_subfolder: str
    laya_device: str | None
    laya_threshold: float
    laya_region: str
    laya_cache_dir: Path | None
    batch_on_start: bool

    @classmethod
    def from_env(cls) -> DlpSettings:
        cache_raw = os.environ.get("DLP_CACHE_PATH", "/var/lib/dlp/cache.sqlite3")
        laya_cache = os.environ.get("LAYA_CACHE_DIR", "").strip()
        device = os.environ.get("LAYA_DEVICE", "").strip() or None
        return cls(
            files_root=Path(os.environ.get("FILES_ROOT", "/files")),
            bind_host=os.environ.get("DLP_BIND_HOST", "127.0.0.1"),
            bind_port=int(os.environ.get("DLP_PORT", "8091")),
            cache_path=Path(cache_raw),
            debounce_seconds=float(os.environ.get("DLP_DEBOUNCE_SECONDS", "2")),
            # Laya CPU inference on large docs can exceed 30s; waiters use this budget.
            lock_seconds=float(os.environ.get("DLP_LOCK_SECONDS", "120")),
            laya_model=os.environ.get("LAYA_MODEL", "goku-san/laya-experts"),
            laya_subfolder=os.environ.get("LAYA_SUBFOLDER", "pii"),
            laya_device=device,
            laya_threshold=float(os.environ.get("LAYA_THRESHOLD", "0.5")),
            laya_region=os.environ.get("LAYA_REGION", "US"),
            laya_cache_dir=Path(laya_cache) if laya_cache else None,
            batch_on_start=os.environ.get("DLP_BATCH_ON_START", "1").strip()
            not in {"0", "false", "False"},
        )
