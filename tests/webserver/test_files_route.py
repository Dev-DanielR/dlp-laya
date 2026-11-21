"""End-to-end route checks against corpus + manifest stub."""

from __future__ import annotations


def _auth(mint_token, user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_token(user)}"}


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_unauthorized(client):
    r = client.get("/files/publico/catalogo_publico.txt")
    assert r.status_code == 401


def test_limpio_completo(client, mint_token):
    r = client.get(
        "/files/publico/catalogo_publico.txt",
        headers=_auth(mint_token, "carla.baja@knowsyn.dev"),
    )
    assert r.status_code == 200
    body = r.data
    assert len(body) > 0


def test_caso01_baja_denied(client, mint_token):
    r = client.get(
        "/files/casos/caso01_informe_sensible.docx",
        headers=_auth(mint_token, "carla.baja@knowsyn.dev"),
    )
    assert r.status_code == 403


def test_caso02_media_sanitized(client, mint_token):
    path = "/files/casos/caso02_clientes_demo.csv"
    r = client.get(path, headers=_auth(mint_token, "bruno.media@knowsyn.dev"))
    assert r.status_code == 200
    text = r.data.decode("utf-8")
    assert "[REDACTED:" in text


def test_caso02_alta_completo(client, mint_token):
    r = client.get(
        "/files/casos/caso02_clientes_demo.csv",
        headers=_auth(mint_token, "ana.alta@knowsyn.dev"),
    )
    assert r.status_code == 200
    text = r.data.decode("utf-8")
    assert "[REDACTED:" not in text


def test_acl_miss_forbidden(client, mint_token):
    r = client.get(
        "/files/interno/rrhh/planilla_parcial_marzo.csv",
        headers=_auth(mint_token, "carla.baja@knowsyn.dev"),
    )
    assert r.status_code == 403


def test_htmx_denied_no_attachment_download(client, mint_token):
    """Browser HTMX denials must not look like a file download."""
    r = client.get(
        "/files/casos/caso01_informe_sensible.docx",
        headers={
            **_auth(mint_token, "carla.baja@knowsyn.dev"),
            "HX-Request": "true",
        },
    )
    assert r.status_code == 403
    assert r.data == b""
    cd = r.headers.get("Content-Disposition", "")
    assert "attachment" not in cd.lower()
    assert r.headers.get("HX-Reswap") == "none"
    trigger = r.headers.get("HX-Trigger", "")
    assert "Denegado" in trigger
    assert "toast" in trigger


def test_htmx_success_is_attachment(client, mint_token):
    r = client.get(
        "/files/publico/catalogo_publico.txt",
        headers={
            **_auth(mint_token, "carla.baja@knowsyn.dev"),
            "HX-Request": "true",
        },
    )
    assert r.status_code == 200
    assert "attachment" in r.headers.get("Content-Disposition", "").lower()
    assert "toast" in r.headers.get("HX-Trigger", "")


def test_classify_mode_dlp_uses_http_client(app, mint_token):
    """With a live DLP client installed, downloads call classify (not stub)."""
    from unittest.mock import MagicMock

    from webserver.dlp.base import ClassifyResult
    from webserver.dlp.http_client import HttpDlpClient

    fake = MagicMock(spec=HttpDlpClient)
    fake.classify.return_value = ClassifyResult(
        status="ready",
        hash="abc",
        label="limpio",
        spans=[],
        laya_version="mock-laya",
        cache_hit=False,
    )
    app.config["DLP"] = fake
    client = app.test_client()
    r = client.get(
        "/files/publico/catalogo_publico.txt",
        headers=_auth(mint_token, "carla.baja@knowsyn.dev"),
    )
    assert r.status_code == 200
    assert fake.classify.call_count >= 1
