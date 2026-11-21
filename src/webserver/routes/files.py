"""GET /files/<path> download pipeline."""

from __future__ import annotations

import json
import mimetypes
import time
import uuid
from io import BytesIO
from pathlib import Path

from flask import Blueprint, current_app, make_response, request, send_file

from webserver.auth.dex import DexAuthError
from webserver.auth.identity import resolve_username
from webserver.browsing import safe_join
from webserver.decision import decide
from webserver.dlp.http_client import wait_for_ready
from webserver.hashing import sha256_file
from webserver.sanitize import apply_spans

bp = Blueprint("files", __name__)


@bp.get("/healthz")
def healthz():
    return {"status": "ok"}, 200


def _wants_htmx() -> bool:
    return bool(request.headers.get("HX-Request"))


def _error(status: int, code: str, detail: str, *, toast: str | None = None):
    """JSON for API; HX-Trigger toast for browser HTMX.

    HTMX download ext only saves a blob when Content-Disposition is attachment
    (or hx-swap=download). Errors must omit attachment and use hx-swap=none
    on the button so the error body is never saved as a file.
    """
    body = {"error": code, "detail": detail}
    if _wants_htmx():
        resp = make_response("", status)
        resp.headers["Content-Type"] = "text/plain; charset=utf-8"
        resp.headers["HX-Reswap"] = "none"
        msg = toast or detail
        kind = "error" if status >= 400 else "success"
        resp.headers["HX-Trigger"] = json.dumps(
            {"toast": {"type": kind, "message": msg}}
        )
        return resp
    return body, status


@bp.get("/files/<path:relpath>")
def get_file(relpath: str):
    app = current_app
    settings = app.config["SETTINGS"]
    audit = app.config["AUDIT"]
    acl = app.config["ACL"]
    dlp = app.config["DLP"]

    request_id = str(uuid.uuid4())
    t0 = time.monotonic()
    user = None
    sensitivity = None
    decision = None
    label = None
    content_hash = None
    lock_wait_ms = 0.0
    laya_version = None
    cache_hit = None

    def _audit(**extra):
        audit.write(
            {
                "request_id": request_id,
                "user": user,
                "path": f"/files/{relpath}",
                "hash": content_hash,
                "label": label,
                "sensitivity": sensitivity,
                "decision": decision or extra.get("decision"),
                "lock_wait_ms": round(lock_wait_ms, 2),
                "classify_ms": extra.get("classify_ms"),
                "duration_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "laya_version": laya_version,
                "cache_hit": cache_hit,
                "http_status": extra.get("http_status"),
                "reason": extra.get("reason"),
            }
        )

    try:
        user = resolve_username(request)
    except DexAuthError as exc:
        decision = "denegado"
        _audit(http_status=401, reason=str(exc), decision="denegado")
        return _error(401, "unauthorized", str(exc), toast="No autorizado")

    abs_api_path = f"/files/{relpath.replace(chr(92), '/')}"
    sensitivity = acl.resolve(user, abs_api_path)
    if sensitivity is None:
        decision = "denegado"
        _audit(http_status=403, reason="acl_miss", decision="denegado")
        return _error(403, "forbidden", "no ACL match", toast="Denegado (ACL)")

    files_root: Path = settings.files_root
    try:
        target = safe_join(files_root, relpath)
    except ValueError:
        decision = "denegado"
        _audit(http_status=404, reason="path_escape", decision="denegado")
        return _error(404, "not_found", "not found", toast="Archivo no encontrado")

    if not target.is_file():
        decision = "denegado"
        _audit(http_status=404, reason="missing_file", decision="denegado")
        return _error(404, "not_found", "not found", toast="Archivo no encontrado")

    content_hash = sha256_file(target)
    classify_t0 = time.monotonic()
    result, lock_wait_ms = wait_for_ready(
        dlp,
        path=abs_api_path,
        content_hash=content_hash,
        wait_seconds=settings.dlp_wait_seconds,
    )
    classify_ms = (time.monotonic() - classify_t0) * 1000.0
    laya_version = result.laya_version
    cache_hit = result.cache_hit

    if result.status in {"missing", "denied_timeout"}:
        decision = "denegado"
        _audit(
            http_status=403,
            reason=result.status,
            decision="denegado",
            classify_ms=round(classify_ms, 2),
        )
        return _error(403, "forbidden", result.status, toast="Denegado (DLP)")

    if result.status != "ready" or not result.label:
        decision = "denegado"
        _audit(
            http_status=403,
            reason=f"classify_{result.status}",
            decision="denegado",
            classify_ms=round(classify_ms, 2),
        )
        return _error(
            403, "forbidden", "classification unavailable", toast="Denegado (DLP)"
        )

    label = result.label
    try:
        decision = decide(sensitivity, label)
    except ValueError as exc:
        decision = "denegado"
        _audit(
            http_status=403,
            reason=str(exc),
            decision="denegado",
            classify_ms=round(classify_ms, 2),
        )
        return _error(403, "forbidden", "invalid classification", toast="Denegado")

    if decision == "denegado":
        _audit(http_status=403, reason="matrix", classify_ms=round(classify_ms, 2))
        return _error(403, "forbidden", "denied by policy", toast="Denegado por política")

    raw = target.read_bytes()
    if decision == "sanitizado":
        body = apply_spans(raw, result.spans)
    else:
        body = raw

    _audit(http_status=200, classify_ms=round(classify_ms, 2))

    mime, _ = mimetypes.guess_type(target.name)
    resp = send_file(
        BytesIO(body),
        mimetype=mime or "application/octet-stream",
        as_attachment=True,
        download_name=target.name,
        etag=False,
        conditional=False,
        max_age=0,
    )
    if _wants_htmx():
        note = "sanitizado" if decision == "sanitizado" else "completo"
        resp.headers["HX-Trigger"] = json.dumps(
            {
                "toast": {
                    "type": "success",
                    "message": f"Descarga ({note}): {target.name}",
                }
            }
        )
    return resp
