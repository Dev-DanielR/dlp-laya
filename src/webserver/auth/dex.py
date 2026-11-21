"""Dex OIDC JWT validation via JWKS."""

from __future__ import annotations

import threading
from typing import Any
from urllib.parse import urlparse

import jwt
import requests
from jwt import PyJWKClient


class DexAuthError(Exception):
    """Raised when a Bearer token is missing or invalid."""


def _require_http_url(name: str, url: str) -> str:
    cleaned = (url or "").strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            f"{name} must be an absolute http(s) URL with a host, got {url!r}. "
            "Example: https://dex.example/dex"
        )
    return cleaned


class DexValidator:
    """Validate RS256 JWTs issued by Dex."""

    def __init__(
        self,
        issuer: str,
        client_id: str,
        jwks_url: str | None = None,
        *,
        jwks_client: PyJWKClient | None = None,
        leeway_seconds: float = 30.0,
    ) -> None:
        if not (client_id or "").strip():
            raise ValueError("client_id is required")
        self.issuer = _require_http_url("DEX_ISSUER", issuer)
        self.client_id = client_id.strip()
        if jwks_url:
            self.jwks_url = _require_http_url("DEX_JWKS_URL", jwks_url)
        else:
            self.jwks_url = f"{self.issuer}/keys"
        self._jwks = jwks_client or PyJWKClient(self.jwks_url, cache_keys=True)
        self._leeway = leeway_seconds
        self._lock = threading.Lock()

    def username_from_authorization(self, authorization: str | None) -> str:
        if not authorization:
            raise DexAuthError("missing Authorization header")
        parts = authorization.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise DexAuthError("Authorization must be Bearer <token>")
        return self.username_from_token(parts[1].strip())

    def username_from_token(self, token: str) -> str:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iat", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise DexAuthError(str(exc)) from exc
        return self._username_from_claims(claims)

    @staticmethod
    def _username_from_claims(claims: dict[str, Any]) -> str:
        preferred = claims.get("preferred_username")
        if isinstance(preferred, str) and preferred.strip():
            return preferred.strip()
        email = claims.get("email")
        if isinstance(email, str) and email.strip():
            return email.strip()
        sub = claims.get("sub")
        if isinstance(sub, str) and sub.strip():
            return sub.strip()
        raise DexAuthError("token has no preferred_username, email, or sub")


def fetch_jwks(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Helper for tests / diagnostics."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
