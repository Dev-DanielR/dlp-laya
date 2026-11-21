"""DLP /progress and /statuses API tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from dlp_service.api import create_app
from dlp_service.batch import recover_missing
from dlp_service.batch_state import BatchState
from dlp_service.classify import Classifier
from dlp_service.laya_pii import RulesOnlyDetector
from dlp_service.store import ClassifyStore


@pytest.fixture
def files_root(tmp_path: Path) -> Path:
    root = tmp_path / "files"
    root.mkdir()
    (root / "a.txt").write_text("limpio\n", encoding="utf-8")
    (root / "b.txt").write_text("limpio\n", encoding="utf-8")
    sub = root / "dir"
    sub.mkdir()
    (sub / "c.txt").write_text("limpio\n", encoding="utf-8")
    return root


@pytest.fixture
def classifier(files_root: Path, tmp_path: Path) -> Classifier:
    store = ClassifyStore(tmp_path / "cache.sqlite3")
    return Classifier(
        files_root=files_root,
        store=store,
        detector=RulesOnlyDetector(),
        lock_seconds=30.0,
        laya_version="rules-only",
    )


def test_progress_pending_then_complete(classifier: Classifier):
    batch = BatchState()
    app = create_app(classifier, batch_state=batch)
    client = app.test_client()

    before = client.get("/progress").get_json()
    assert before["total"] == 3
    assert before["pending"] == 3
    assert before["done"] == 0
    assert before["complete"] is False
    assert before["batch_running"] is False

    recover_missing(classifier, background=False, batch_state=batch)

    after = client.get("/progress").get_json()
    assert after["done"] == 3
    assert after["pending"] == 0
    assert after["complete"] is True
    assert after["batch_running"] is False


def test_statuses_paths_and_prefix(classifier: Classifier):
    batch = BatchState()
    app = create_app(classifier, batch_state=batch)
    client = app.test_client()

    empty = client.get("/statuses?paths=a.txt,dir/c.txt").get_json()
    assert {i["path"]: i["phase"] for i in empty["items"]} == {
        "a.txt": "pending",
        "dir/c.txt": "pending",
    }

    classifier.classify(path="a.txt")
    ready = client.get("/statuses?paths=a.txt,b.txt").get_json()
    by_path = {i["path"]: i for i in ready["items"]}
    assert by_path["a.txt"]["phase"] == "ready"
    assert by_path["a.txt"]["label"] == "limpio"
    assert by_path["b.txt"]["phase"] == "pending"

    top = client.get("/statuses?prefix=").get_json()
    top_paths = {i["path"] for i in top["items"]}
    assert top_paths == {"a.txt", "b.txt"}

    nested = client.get("/statuses?prefix=dir").get_json()
    assert [i["path"] for i in nested["items"]] == ["dir/c.txt"]
