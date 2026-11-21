"""UI / session / browse tests (no live NetBird)."""


def test_landing_anonymous(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Sign in with NetBird" in r.data


def test_browse_requires_session(client):
    r = client.get("/browse")
    assert r.status_code in (302, 303)
    assert "/?" in r.headers.get("Location", "") or r.headers.get("Location", "").endswith(
        "/"
    )


def test_browse_with_session(client, session_cookie):
    session_cookie(client, "ana.alta@knowsyn.dev")
    r = client.get("/browse")
    assert r.status_code == 200
    assert b"Explorador" in r.data or b"publico" in r.data


def test_browse_listing_htmx(client, session_cookie):
    session_cookie(client, "bruno.media@knowsyn.dev")
    r = client.get("/browse?path=publico", headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert b"Descargar" in r.data or b"carpeta" in r.data or b"archivo" in r.data


def test_download_with_session_cookie(client, session_cookie):
    session_cookie(client, "carla.baja@knowsyn.dev")
    r = client.get("/files/publico/catalogo_publico.txt")
    assert r.status_code == 200
    assert len(r.data) > 0


def test_download_session_denied(client, session_cookie):
    session_cookie(client, "carla.baja@knowsyn.dev")
    r = client.get("/files/casos/caso01_informe_sensible.docx")
    assert r.status_code == 403


def test_logout(app, client, session_cookie):
    """Even without id_token, OIDC logout still hits Dex end_session."""
    from unittest.mock import MagicMock

    from webserver.auth.oidc import OidcClient

    oidc = MagicMock(spec=OidcClient)
    oidc.logout_url.return_value = "https://knowsyn.dev/oauth2/logout?client_id=dlp-laya"
    app.config["OIDC"] = oidc

    session_cookie(client, "ana.alta@knowsyn.dev")
    r = client.get("/auth/logout")
    assert r.status_code in (302, 303)
    loc = r.headers.get("Location", "")
    assert "/oauth2/logout" in loc
    kwargs = oidc.logout_url.call_args.kwargs
    assert kwargs["id_token"] is None
    r2 = client.get("/browse")
    assert r2.status_code in (302, 303)


def test_logout_rp_initiated(app, client):
    """With id_token + OIDC, logout redirects to Dex end_session with hint."""
    from unittest.mock import MagicMock

    from webserver.auth.oidc import OidcClient
    from webserver.auth.session import SessionStore, SessionUser

    store: SessionStore = app.config["SESSION"]
    settings = app.config["SETTINGS"]
    oidc = MagicMock(spec=OidcClient)
    oidc.logout_url.return_value = (
        "https://knowsyn.dev/oauth2/logout?id_token_hint=tok"
        f"&post_logout_redirect_uri={settings.post_logout_redirect_uri()}"
    )
    app.config["OIDC"] = oidc

    user = SessionUser(
        username="ana.alta@knowsyn.dev",
        email="ana.alta@knowsyn.dev",
        id_token="header.payload.sig",
    )
    client.set_cookie("dlp_session", store.dump_user(user))
    r = client.get("/auth/logout")
    assert r.status_code in (302, 303)
    loc = r.headers.get("Location", "")
    assert loc.startswith("https://knowsyn.dev/oauth2/logout")
    oidc.logout_url.assert_called_once()
    kwargs = oidc.logout_url.call_args.kwargs
    assert kwargs["id_token"] == "header.payload.sig"
    assert kwargs["post_logout_redirect_uri"] == settings.post_logout_redirect_uri()


def test_post_logout_redirect_uri_from_oidc_redirect(app):
    settings = app.config["SETTINGS"]
    assert settings.post_logout_redirect_uri().endswith("/")
