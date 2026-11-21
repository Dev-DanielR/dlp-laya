"""Resolve request identity from Bearer JWT or session cookie."""

from __future__ import annotations

from flask import Request, current_app

from webserver.auth.dex import DexAuthError
from webserver.auth.session import SessionUser


def resolve_username(request: Request) -> str:
    """Return ACL username or raise DexAuthError."""
    auth = request.headers.get("Authorization")
    if auth:
        return current_app.config["DEX"].username_from_authorization(auth)

    store = current_app.config["SESSION"]
    user: SessionUser | None = store.user_from_request(request)
    if user is None:
        raise DexAuthError("missing Authorization header and session cookie")
    return user.username


def current_session_user(request: Request) -> SessionUser | None:
    return current_app.config["SESSION"].user_from_request(request)
