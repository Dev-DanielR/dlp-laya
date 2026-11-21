"""Read-only progress and per-path status helpers for the DLP API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dlp_service.batch import walk_files
from dlp_service.batch_state import BatchState
from dlp_service.state import FilePhase
from dlp_service.store import ClassifyStore

_TERMINAL: set[FilePhase] = {"ready", "denied_timeout", "missing"}


def _model_flags(detector: object | None) -> dict[str, Any]:
    if detector is None:
        return {"model_ready": True, "model_loading": False, "model_error": None}
    ready = bool(getattr(detector, "ready", True))
    loading = bool(getattr(detector, "loading", False))
    # Rules-only has no ready attr → treat as ready.
    if not hasattr(detector, "ensure_loaded"):
        ready = True
        loading = False
    err = getattr(detector, "load_error", None)
    return {
        "model_ready": ready,
        "model_loading": loading or (not ready and err is None),
        "model_error": err,
    }


def build_progress(
    *,
    files_root: Path,
    store: ClassifyStore,
    batch: BatchState,
    detector: object | None = None,
) -> dict[str, Any]:
    rels = walk_files(files_root)
    total = len(rels)
    metas = store.get_path_metas(rels)
    counts: dict[str, int] = {
        "ready": 0,
        "classifying": 0,
        "pending": 0,
        "denied_timeout": 0,
        "missing": 0,
    }
    for rel in rels:
        meta = metas.get(rel)
        if meta is None:
            counts["pending"] += 1
            continue
        _hash, phase, _lock = meta
        if phase in counts:
            counts[phase] += 1
        else:
            counts["pending"] += 1

    snap = batch.snapshot()
    done = counts["ready"]
    terminal = done + counts["denied_timeout"] + counts["missing"]
    model = _model_flags(detector)
    complete = (
        model["model_ready"]
        and not model["model_loading"]
        and (
            (
                total > 0
                and terminal >= total
                and counts["classifying"] == 0
                and not snap.running
            )
            or (total == 0 and not snap.running)
        )
    )

    return {
        "total": total,
        "done": done,
        "classifying": counts["classifying"],
        "pending": counts["pending"],
        "denied_timeout": counts["denied_timeout"],
        "missing": counts["missing"],
        "batch_running": snap.running,
        "batch_finished": snap.finished,
        "batch_total": snap.total,
        "complete": complete,
        **model,
    }


def build_statuses(
    *,
    store: ClassifyStore,
    paths: list[str],
) -> list[dict[str, Any]]:
    metas = store.get_path_metas(paths)
    items: list[dict[str, Any]] = []
    for rel in paths:
        meta = metas.get(rel)
        if meta is None:
            items.append({"path": rel, "phase": "pending", "label": None})
            continue
        content_hash, phase, _lock = meta
        label = None
        if content_hash and phase == "ready":
            cached = store.get_by_hash(content_hash)
            if cached is not None:
                label = cached.label
        items.append({"path": rel, "phase": phase, "label": label})
    return items


def filter_prefix(rels: list[str], prefix: str) -> list[str]:
    """Return rels that are direct children of prefix (one path segment deeper).

    If prefix is empty, return top-level file rels only (no slash) — callers
    usually pass an explicit path list from list_dir instead.
    """
    prefix = prefix.strip("/")
    if not prefix:
        return [r for r in rels if "/" not in r]
    pre = prefix + "/"
    out: list[str] = []
    for r in rels:
        if not r.startswith(pre):
            continue
        rest = r[len(pre) :]
        if "/" not in rest:
            out.append(r)
    return out


def is_terminal_phase(phase: str) -> bool:
    return phase in _TERMINAL
