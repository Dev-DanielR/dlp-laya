"""Cascading ACL: (user, path) → sensibilidad; longest prefix wins."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

Sensitivity = Literal["alta", "media", "baja"]


@dataclass(frozen=True)
class AclRule:
    path: str
    sensitivity: Sensitivity


@dataclass
class AclStore:
    """In-memory rules keyed by username."""

    users: dict[str, list[AclRule]]

    @classmethod
    def load(cls, path: Path) -> AclStore:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        users_raw = raw.get("users") or {}
        users: dict[str, list[AclRule]] = {}
        for username, body in users_raw.items():
            rules: list[AclRule] = []
            for item in body.get("rules") or []:
                p = _normalize_path(str(item["path"]))
                sens = str(item["sensitivity"]).strip().lower()
                if sens not in {"alta", "media", "baja"}:
                    raise ValueError(
                        f"invalid sensitivity {sens!r} for {username} path {p}"
                    )
                rules.append(AclRule(path=p, sensitivity=sens))  # type: ignore[arg-type]
            users[str(username)] = rules
        return cls(users=users)

    def resolve(self, username: str, request_path: str) -> Sensitivity | None:
        """Return sensibilidad for the longest matching prefix, or None on miss."""
        rules = self.users.get(username)
        if not rules:
            return None
        path = _normalize_path(request_path)
        best: AclRule | None = None
        best_len = -1
        for rule in rules:
            if _path_matches(rule.path, path) and len(rule.path) > best_len:
                best = rule
                best_len = len(rule.path)
        return best.sensitivity if best else None


def _normalize_path(path: str) -> str:
    p = path.replace("\\", "/").strip()
    if not p.startswith("/"):
        p = "/" + p
    # Collapse duplicate slashes; strip trailing slash except root
    parts = [x for x in p.split("/") if x != ""]
    return "/" + "/".join(parts) if parts else "/"


def _path_matches(prefix: str, path: str) -> bool:
    """True if path equals prefix or is under prefix as a path segment boundary."""
    if path == prefix:
        return True
    if prefix == "/":
        return path.startswith("/")
    return path.startswith(prefix + "/")
