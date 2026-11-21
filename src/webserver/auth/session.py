"""Signed httpOnly session cookies for browser OIDC login."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "dlp_session"
PKCE_COOKIE = "dlp_oidc_pkce"
MAX_AGE_SECONDS = 8 * 60 * 60  # 8h
PKCE_MAX_AGE = 600  # 10m


@dataclass
class SessionUser:
    username: str
    sub: str | None = None
    email: str | None = None
    preferred_username: str | None = None
    # Raw id_token for Dex RP-initiated logout (id_token_hint).
    id_token: str | None = None


class SessionStore:
    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("SESSION_SECRET is required")
        self._ser = URLSafeTimedSerializer(secret, salt="dlp-laya-session")
        self._pkce = URLSafeTimedSerializer(secret, salt="dlp-laya-pkce")

    def dump_user(self, user: SessionUser, extra: dict[str, Any] | None = None) -> str:
        payload = {
            "username": user.username,
            "sub": user.sub,
            "email": user.email,
            "preferred_username": user.preferred_username,
            "id_token": user.id_token,
            **(extra or {}),
        }
        return self._ser.dumps(payload)

    def load_user(self, token: str) -> SessionUser | None:
        try:
            data = self._ser.loads(token, max_age=MAX_AGE_SECONDS)
        except (BadSignature, SignatureExpired):
            return None
        username = data.get("username")
        if not isinstance(username, str) or not username.strip():
            return None
        id_token = data.get("id_token")
        return SessionUser(
            username=username.strip(),
            sub=data.get("sub"),
            email=data.get("email"),
            preferred_username=data.get("preferred_username"),
            id_token=id_token if isinstance(id_token, str) and id_token else None,
        )

    def user_from_request(self, request: Request) -> SessionUser | None:
        raw = request.cookies.get(COOKIE_NAME)
        if not raw:
            return None
        return self.load_user(raw)

    def set_session_cookie(
        self, response: Response, user: SessionUser, *, secure: bool = True
    ) -> None:
        response.set_cookie(
            COOKIE_NAME,
            self.dump_user(user),
            httponly=True,
            secure=secure,
            samesite="Lax",
            max_age=MAX_AGE_SECONDS,
            path="/",
        )

    def clear_session_cookie(self, response: Response) -> None:
        response.delete_cookie(COOKIE_NAME, path="/")

    def dump_pkce(self, state: str, verifier: str) -> str:
        return self._pkce.dumps({"state": state, "verifier": verifier})

    def load_pkce(self, token: str) -> tuple[str, str] | None:
        try:
            data = self._pkce.loads(token, max_age=PKCE_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        state = data.get("state")
        verifier = data.get("verifier")
        if not isinstance(state, str) or not isinstance(verifier, str):
            return None
        return state, verifier

    def set_pkce_cookie(
        self, response: Response, state: str, verifier: str, *, secure: bool = True
    ) -> None:
        response.set_cookie(
            PKCE_COOKIE,
            self.dump_pkce(state, verifier),
            httponly=True,
            secure=secure,
            samesite="Lax",
            max_age=PKCE_MAX_AGE,
            path="/",
        )

    def clear_pkce_cookie(self, response: Response) -> None:
        response.delete_cookie(PKCE_COOKIE, path="/")
