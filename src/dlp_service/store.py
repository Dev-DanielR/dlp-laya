"""SQLite KV cache keyed by content hash, with path index."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from dlp_service.state import ClassifyRecord, FilePhase


class ClassifyStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS by_hash (
                    content_hash TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS by_path (
                    rel_path TEXT PRIMARY KEY,
                    content_hash TEXT,
                    phase TEXT NOT NULL,
                    lock_until REAL,
                    updated_at REAL NOT NULL
                );
                """
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def get_by_hash(self, content_hash: str) -> ClassifyRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT record_json FROM by_hash WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
        if not row:
            return None
        rec = ClassifyRecord.from_json(row["record_json"])
        rec.cache_hit = True
        return rec

    def put_hash(self, content_hash: str, record: ClassifyRecord) -> None:
        record.hash = content_hash
        payload = record.to_json()
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO by_hash(content_hash, record_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    record_json = excluded.record_json,
                    updated_at = excluded.updated_at
                """,
                (content_hash, payload, now),
            )
            self._conn.commit()

    def get_path_meta(
        self, rel_path: str
    ) -> tuple[str | None, FilePhase, float | None] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT content_hash, phase, lock_until FROM by_path WHERE rel_path = ?",
                (rel_path,),
            ).fetchone()
        if not row:
            return None
        return row["content_hash"], row["phase"], row["lock_until"]

    def get_path_metas(
        self, rel_paths: list[str]
    ) -> dict[str, tuple[str | None, FilePhase, float | None]]:
        if not rel_paths:
            return {}
        # Chunk IN queries to stay under SQLite variable limits.
        out: dict[str, tuple[str | None, FilePhase, float | None]] = {}
        chunk_size = 400
        with self._lock:
            for i in range(0, len(rel_paths), chunk_size):
                chunk = rel_paths[i : i + chunk_size]
                placeholders = ",".join("?" * len(chunk))
                rows = self._conn.execute(
                    f"SELECT rel_path, content_hash, phase, lock_until "
                    f"FROM by_path WHERE rel_path IN ({placeholders})",
                    chunk,
                ).fetchall()
                for row in rows:
                    out[row["rel_path"]] = (
                        row["content_hash"],
                        row["phase"],
                        row["lock_until"],
                    )
        return out

    def set_path(
        self,
        rel_path: str,
        *,
        phase: FilePhase,
        content_hash: str | None = None,
        lock_until: float | None = None,
    ) -> None:
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO by_path(rel_path, content_hash, phase, lock_until, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(rel_path) DO UPDATE SET
                    content_hash = COALESCE(excluded.content_hash, by_path.content_hash),
                    phase = excluded.phase,
                    lock_until = excluded.lock_until,
                    updated_at = excluded.updated_at
                """,
                (rel_path, content_hash, phase, lock_until, now),
            )
            self._conn.commit()

    def clear_path_lock(self, rel_path: str, *, phase: FilePhase) -> None:
        self.set_path(rel_path, phase=phase, lock_until=None)

    def list_paths(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute("SELECT rel_path FROM by_path").fetchall()
        return [r["rel_path"] for r in rows]
