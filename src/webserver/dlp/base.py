"""DLP classify result and client protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ClassifyStatus = Literal["ready", "locked", "denied_timeout", "missing"]


@dataclass
class ClassifyResult:
    status: ClassifyStatus
    hash: str | None = None
    label: str | None = None
    spans: list[dict[str, Any]] = field(default_factory=list)
    laya_version: str | None = None
    cache_hit: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class DlpClient(Protocol):
    def classify(
        self,
        *,
        path: str | None = None,
        content_hash: str | None = None,
    ) -> ClassifyResult:
        """Single classify call (may return locked)."""
        ...
