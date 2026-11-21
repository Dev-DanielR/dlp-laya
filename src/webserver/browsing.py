"""Safe directory listing under FILES_ROOT."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DirEntry:
    name: str
    relpath: str  # posix relative to files root
    is_dir: bool
    size: int | None


def normalize_rel(path: str | None) -> str:
    if not path:
        return ""
    p = path.replace("\\", "/").strip("/")
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        raise ValueError("invalid path")
    return "/".join(parts)


def safe_join(root: Path, relpath: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root / relpath).resolve() if relpath else root_resolved
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("path escapes files root") from exc
    return candidate


def list_dir(root: Path, relpath: str = "") -> tuple[Path, list[DirEntry]]:
    rel = normalize_rel(relpath)
    target = safe_join(root, rel)
    if not target.exists():
        raise FileNotFoundError(rel)
    if not target.is_dir():
        raise NotADirectoryError(rel)
    entries: list[DirEntry] = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        child_rel = f"{rel}/{child.name}" if rel else child.name
        entries.append(
            DirEntry(
                name=child.name,
                relpath=child_rel.replace("\\", "/"),
                is_dir=child.is_dir(),
                size=None if child.is_dir() else child.stat().st_size,
            )
        )
    return target, entries


def breadcrumbs(relpath: str) -> list[tuple[str, str]]:
    """Return [(label, relpath), ...] including root."""
    rel = normalize_rel(relpath)
    crumbs: list[tuple[str, str]] = [("files", "")]
    if not rel:
        return crumbs
    parts = rel.split("/")
    acc: list[str] = []
    for part in parts:
        acc.append(part)
        crumbs.append((part, "/".join(acc)))
    return crumbs
