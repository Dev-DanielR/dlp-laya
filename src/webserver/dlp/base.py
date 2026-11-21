"""DLP classify result and client protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ClassifyStatus = Literal["ready", "locked", "denied_timeout", "missing"]
DlpPhase = Literal["pending", "classifying", "ready", "denied_timeout", "missing"]


@dataclass
class ClassifyResult:
    status: ClassifyStatus
    hash: str | None = None
    label: str | None = None
    spans: list[dict[str, Any]] = field(default_factory=list)
    laya_version: str | None = None
    cache_hit: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class DlpProgress:
    total: int
    done: int
    classifying: int = 0
    pending: int = 0
    denied_timeout: int = 0
    missing: int = 0
    batch_running: bool = False
    complete: bool = False
    model_ready: bool = True
    model_loading: bool = False
    model_error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_api(self) -> dict[str, Any]:
        out = {
            "total": self.total,
            "done": self.done,
            "classifying": self.classifying,
            "pending": self.pending,
            "denied_timeout": self.denied_timeout,
            "missing": self.missing,
            "batch_running": self.batch_running,
            "complete": self.complete,
            "model_ready": self.model_ready,
            "model_loading": self.model_loading,
            "model_error": self.model_error,
        }
        for key in ("batch_finished", "batch_total"):
            if key in self.raw:
                out[key] = self.raw[key]
        return out


@dataclass
class DlpPathStatus:
    path: str
    phase: DlpPhase
    label: str | None = None


class DlpClient(Protocol):
    def classify(
        self,
        *,
        path: str | None = None,
        content_hash: str | None = None,
    ) -> ClassifyResult:
        """Single classify call (may return locked)."""
        ...

    def progress(self) -> DlpProgress:
        """Warmup / cache fill progress."""
        ...

    def statuses(
        self,
        *,
        paths: list[str] | None = None,
        prefix: str | None = None,
    ) -> list[DlpPathStatus]:
        """Read-only phases for paths (no classify side effects)."""
        ...
