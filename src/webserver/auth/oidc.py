"""OIDC authorization-code + PKCE against Dex / NetBird embedded IdP."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import jwt
import requests

from webserver.auth.dex import DexValidator
from webserver.auth.session import SessionUser


@dataclass
class OidcDiscovery:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    end_session_endpoint: str | None = None


class OidcClient:
    def __init__(
        self,
        *,
        issuer: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        dex: DexValidator,
        timeout: float = 10.0,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.dex = dex
        self.timeout = timeout
        self._discovery: OidcDiscovery | None = None

    def discovery(self) -> OidcDiscovery:
        if self._discovery is not None:
            return self._discovery
        url = f"{self.issuer}/.well-known/openid-configuration"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        end = data.get("end_session_endpoint")
        self._discovery = OidcDiscovery(
            issuer=str(data["issuer"]).rstrip("/"),
            authorization_endpoint=str(data["authorization_endpoint"]),
            token_endpoint=str(data["token_endpoint"]),
            jwks_uri=str(data["jwks_uri"]),
            end_session_endpoint=str(end) if isinstance(end, str) and end else None,
        )
        return self._discovery

    @staticmethod
    def new_pkce() -> tuple[str, str, str]:
        """Return (state, verifier, challenge)."""
        state = secrets.token_urlsafe(24)
        verifier = secrets.token_urlsafe(48)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return state, verifier, challenge

    def authorize_url(self, *, state: str, challenge: str) -> str:
        disc = self.discovery()
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            # Lab: always re-prompt so Sign-in after Sign-out cannot reuse SSO silently.
            "prompt": "login",
        }
        return f"{disc.authorization_endpoint}?{urlencode(params)}"

    def logout_url(
        self,
        *,
        post_logout_redirect_uri: str,
        id_token: str | None = None,
        state: str | None = None,
    ) -> str | None:
        """Build Dex RP-initiated logout URL, or None if IdP has no end_session.

        Dex honors post_logout_redirect_uri only with a valid id_token_hint.
        Without a hint, still hit /logout so the IdP session cookie is cleared.
        """
        disc = self.discovery()
        endpoint = disc.end_session_endpoint or f"{self.issuer}/logout"
        params: dict[str, str] = {"client_id": self.client_id}
        if id_token:
            params["id_token_hint"] = id_token
            params["post_logout_redirect_uri"] = post_logout_redirect_uri
        if state:
            params["state"] = state
        return f"{endpoint}?{urlencode(params)}"

    def exchange_code(self, *, code: str, verifier: str) -> dict[str, Any]:
        disc = self.discovery()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code_verifier": verifier,
        }
        resp = requests.post(disc.token_endpoint, data=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def session_user_from_tokens(self, token_response: dict[str, Any]) -> SessionUser:
        id_token = token_response.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise ValueError("token response missing id_token")
        # Validate signature + iss/aud via Dex JWKS
        username = self.dex.username_from_token(id_token)
        # Also pull claims without trusting unverified payload for auth — already verified
        signing_key = self.dex._jwks.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=self.issuer,
            leeway=30.0,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
        return SessionUser(
            username=username,
            sub=claims.get("sub"),
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            preferred_username=(
                claims.get("preferred_username")
                if isinstance(claims.get("preferred_username"), str)
                else None
            ),
            id_token=id_token,
        )
