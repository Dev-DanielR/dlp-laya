"""DLP classify pipeline tests (rules-only detector, no Laya weights)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dlp_service.api import create_app
from dlp_service.classify import Classifier, sha256_file
from dlp_service.laya_pii import RulesOnlyDetector
from dlp_service.rules import candidates
from dlp_service.store import ClassifyStore


@pytest.fixture
def files_root(tmp_path: Path) -> Path:
    root = tmp_path / "files"
    root.mkdir()
    (root / "limpio.txt").write_text(
        "Boletín interno. SKU 87654321. Proyección estable.\n", encoding="utf-8"
    )
    (root / "pii.txt").write_text(
        "Contacto: ana.alta@knowsyn.dev DNI 45678901 tel +51 987 654 321 "
        "RUC 20123456789 CCI 002-1-123456789012\n",
        encoding="utf-8",
    )
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


def test_rules_find_pe_surfaces():
    text = "correo ana@x.com dni 45678901 ruc 20123456789"
    fams = {f for c in candidates(text) for f in c.families}
    assert "EMAIL" in fams
    assert "PE_DNI" in fams
    assert "PE_RUC" in fams


def test_classify_limpio(classifier: Classifier, files_root: Path):
    rec = classifier.classify(path="limpio.txt")
    assert rec.status == "ready"
    assert rec.label == "limpio"
    assert rec.spans == []
    assert rec.laya_version == "rules-only"


def test_classify_con_pii_and_cache(classifier: Classifier, files_root: Path):
    rec = classifier.classify(path="pii.txt")
    assert rec.status == "ready"
    assert rec.label == "con_pii"
    assert rec.cache_hit is False
    assert any(s.type == "email address" for s in rec.spans)
    assert any("@" in s.text for s in rec.spans)

    h = sha256_file(files_root / "pii.txt")
    hit = classifier.classify(path="pii.txt", content_hash=h)
    assert hit.status == "ready"
    assert hit.cache_hit is True
    assert hit.label == "con_pii"


def test_missing_file(classifier: Classifier):
    rec = classifier.classify(path="nope.txt")
    assert rec.status == "missing"


def test_api_classify(classifier: Classifier):
    app = create_app(classifier)
    client = app.test_client()
    r = client.get("/healthz")
    assert r.status_code == 200
    r = client.get("/classify", query_string={"path": "pii.txt"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ready"
    assert body["label"] == "con_pii"
    assert body["spans"]
