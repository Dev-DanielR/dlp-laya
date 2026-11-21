"""Landing, OIDC auth, and file browser UI."""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from webserver.auth.identity import current_session_user
from webserver.auth.session import PKCE_COOKIE
from webserver.browsing import breadcrumbs, list_dir, normalize_rel

bp = Blueprint("ui", __name__)


def _phases_for_entries(entries) -> dict[str, str]:
    """Map file relpaths -> DLP phase for the current listing."""
    dlp = current_app.config.get("DLP")
    if dlp is None or not hasattr(dlp, "statuses"):
        return {}
    file_paths = [e.relpath for e in entries if not e.is_dir]
    if not file_paths:
        return {}
    try:
        items = dlp.statuses(paths=file_paths)
    except Exception:  # noqa: BLE001 — browse still works without glyphs
        return {}
    return {i.path: i.phase for i in items if i.path}



def _secure() -> bool:
    return bool(current_app.config["SETTINGS"].cookie_secure)


@bp.get("/")
def landing():
    user = current_session_user(request)
    if user:
        return redirect(url_for("ui.browse"))
    settings = current_app.config["SETTINGS"]
    return render_template(
        "landing.html",
        oidc_ready=settings.oidc_login_configured(),
        issuer=settings.dex_issuer,
    )


@bp.get("/auth/login")
def auth_login():
    settings = current_app.config["SETTINGS"]
    oidc = current_app.config.get("OIDC")
    if oidc is None or not settings.oidc_login_configured():
        return (
            render_template(
                "landing.html",
                oidc_ready=False,
                issuer=settings.dex_issuer,
                error="OIDC no configurado: faltan DEX_CLIENT_SECRET u OIDC_REDIRECT_URI",
            ),
            503,
        )
    store = current_app.config["SESSION"]
    state, verifier, challenge = oidc.new_pkce()
    url = oidc.authorize_url(state=state, challenge=challenge)
    resp = redirect(url)
    store.set_pkce_cookie(resp, state, verifier, secure=_secure())
    return resp


@bp.get("/auth/callback")
def auth_callback():
    settings = current_app.config["SETTINGS"]
    oidc = current_app.config.get("OIDC")
    store = current_app.config["SESSION"]
    if oidc is None:
        return redirect(url_for("ui.landing"))

    err = request.args.get("error")
    if err:
        return (
            render_template(
                "landing.html",
                oidc_ready=settings.oidc_login_configured(),
                issuer=settings.dex_issuer,
                error=f"OIDC error: {err}",
            ),
            400,
        )

    code = request.args.get("code")
    state = request.args.get("state")
    pkce_raw = request.cookies.get(PKCE_COOKIE)
    if not code or not state or not pkce_raw:
        return (
            render_template(
                "landing.html",
                oidc_ready=True,
                issuer=settings.dex_issuer,
                error="Callback incompleto (code/state)",
            ),
            400,
        )
    loaded = store.load_pkce(pkce_raw)
    if loaded is None or loaded[0] != state:
        return (
            render_template(
                "landing.html",
                oidc_ready=True,
                issuer=settings.dex_issuer,
                error="State OIDC inválido o expirado",
            ),
            400,
        )
    _state, verifier = loaded
    try:
        tokens = oidc.exchange_code(code=code, verifier=verifier)
        user = oidc.session_user_from_tokens(tokens)
    except Exception as exc:  # noqa: BLE001 — surface to landing
        return (
            render_template(
                "landing.html",
                oidc_ready=True,
                issuer=settings.dex_issuer,
                error=f"No se pudo completar el login: {exc}",
            ),
            400,
        )

    resp = redirect(url_for("ui.browse"))
    store.set_session_cookie(resp, user, secure=_secure())
    store.clear_pkce_cookie(resp)
    return resp


@bp.get("/auth/logout")
def auth_logout():
    """Clear app session, then RP-initiated logout at Dex so SSO cookie dies too."""
    settings = current_app.config["SETTINGS"]
    store = current_app.config["SESSION"]
    oidc = current_app.config.get("OIDC")
    user = current_session_user(request)

    target = url_for("ui.landing")
    if oidc is not None and settings.oidc_login_configured():
        try:
            logout = oidc.logout_url(
                id_token=user.id_token if user is not None else None,
                post_logout_redirect_uri=settings.post_logout_redirect_uri(),
            )
        except Exception:  # noqa: BLE001 — fall back to local landing
            logout = None
        if logout:
            target = logout

    resp = redirect(target)
    store.clear_session_cookie(resp)
    store.clear_pkce_cookie(resp)
    return resp


@bp.get("/browse")
def browse():
    user = current_session_user(request)
    if user is None:
        return redirect(url_for("ui.landing"))

    settings = current_app.config["SETTINGS"]
    raw_path = request.args.get("path", "")
    try:
        rel = normalize_rel(raw_path)
        _target, entries = list_dir(settings.files_root, rel)
    except (ValueError, FileNotFoundError, NotADirectoryError):
        if request.headers.get("HX-Request"):
            return "Ruta inválida", 404
        return redirect(url_for("ui.browse"))

    crumbs = breadcrumbs(rel)
    parent = "/".join(rel.split("/")[:-1]) if rel else None
    phases = _phases_for_entries(entries)

    if request.headers.get("HX-Request"):
        return render_template(
            "partials/listing.html",
            entries=entries,
            crumbs=crumbs,
            relpath=rel,
            parent=parent,
            user=user,
            phases=phases,
            classify_mode=settings.classify_mode,
        )

    return render_template(
        "browse.html",
        entries=entries,
        crumbs=crumbs,
        relpath=rel,
        parent=parent,
        user=user,
        phases=phases,
        classify_mode=settings.classify_mode,
    )


@bp.get("/api/dlp/progress")
def dlp_progress():
    user = current_session_user(request)
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    dlp = current_app.config.get("DLP")
    if dlp is None or not hasattr(dlp, "progress"):
        return jsonify({"error": "dlp unavailable"}), 503
    try:
        prog = dlp.progress()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 502
    return jsonify(prog.to_api()), 200


@bp.get("/api/dlp/statuses")
def dlp_statuses():
    user = current_session_user(request)
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    dlp = current_app.config.get("DLP")
    if dlp is None or not hasattr(dlp, "statuses"):
        return jsonify({"error": "dlp unavailable"}), 503

    settings = current_app.config["SETTINGS"]
    raw_path = request.args.get("path", "")
    try:
        rel = normalize_rel(raw_path)
        _target, entries = list_dir(settings.files_root, rel)
    except (ValueError, FileNotFoundError, NotADirectoryError):
        return jsonify({"error": "invalid path"}), 404

    file_paths = [e.relpath for e in entries if not e.is_dir]
    try:
        items = dlp.statuses(paths=file_paths) if file_paths else []
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 502
    return jsonify(
        {
            "path": rel,
            "items": [
                {"path": i.path, "phase": i.phase, "label": i.label} for i in items
            ],
        }
    ), 200
