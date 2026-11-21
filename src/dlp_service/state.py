"""Classification record shapes shared by store and API."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ClassifyStatus = Literal["ready", "locked", "denied_timeout", "missing"]
FilePhase = Literal["pending", "classifying", "ready", "denied_timeout", "missing"]


@dataclass
class Span:
    type: str
    text: str
    start: int | None = None
    end: int | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type, "text": self.text}
        if self.start is not None and self.end is not None:
            out["start"] = self.start
            out["end"] = self.end
        return out


@dataclass
class ClassifyRecord:
    status: ClassifyStatus
    hash: str | None = None
    label: str | None = None
    spans: list[Span] = field(default_factory=list)
    laya_version: str | None = None
    cache_hit: bool | None = None
    path: str | None = None
    phase: FilePhase | None = None
    error: str | None = None

    def to_api(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "hash": self.hash,
            "label": self.label,
            "spans": [s.as_dict() for s in self.spans],
            "laya_version": self.laya_version,
            "cache_hit": self.cache_hit,
            "path": self.path,
        }

    def to_json(self) -> str:
        payload = asdict(self)
        payload["spans"] = [s.as_dict() for s in self.spans]
        return json.dumps(payload)

    @classmethod
    def from_json(cls, raw: str) -> ClassifyRecord:
        data = json.loads(raw)
        spans = [
            Span(
                type=str(s.get("type") or "pii"),
                text=str(s.get("text") or ""),
                start=s.get("start") if isinstance(s.get("start"), int) else None,
                end=s.get("end") if isinstance(s.get("end"), int) else None,
            )
            for s in (data.get("spans") or [])
            if s.get("text")
        ]
        return cls(
            status=data.get("status") or "missing",
            hash=data.get("hash"),
            label=data.get("label"),
            spans=spans,
            laya_version=data.get("laya_version"),
            cache_hit=data.get("cache_hit"),
            path=data.get("path"),
            phase=data.get("phase"),
            error=data.get("error"),
        )
