"""Authenticated /api/dlp/progress and /statuses (stub mode)."""


def test_progress_requires_session(client):
    r = client.get("/api/dlp/progress")
    assert r.status_code == 401


def test_statuses_requires_session(client):
    r = client.get("/api/dlp/statuses")
    assert r.status_code == 401


def test_progress_stub_complete(client, session_cookie):
    session_cookie(client, "ana.alta@knowsyn.dev")
    r = client.get("/api/dlp/progress")
    assert r.status_code == 200
    data = r.get_json()
    assert data["complete"] is True
    assert data["done"] == data["total"]
    assert data["total"] > 0
    assert data["batch_running"] is False


def test_statuses_stub_ready(client, session_cookie):
    session_cookie(client, "ana.alta@knowsyn.dev")
    r = client.get("/api/dlp/statuses?path=publico")
    assert r.status_code == 200
    data = r.get_json()
    assert data["path"] == "publico"
    assert isinstance(data["items"], list)
    assert data["items"], "expected files under publico"
    for item in data["items"]:
        assert item["phase"] == "ready"
        assert item["path"].startswith("publico/")


def test_browse_includes_dlp_glyphs(client, session_cookie):
    session_cookie(client, "ana.alta@knowsyn.dev")
    r = client.get("/browse")
    assert r.status_code == 200
    assert b"data-dlp-path" in r.data
    assert b"dlpWarmup" in r.data
    assert b"/api/dlp/progress" in r.data
