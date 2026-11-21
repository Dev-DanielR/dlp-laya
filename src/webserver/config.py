"""Environment-driven settings for the webserver."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


def _default_acl_path() -> Path:
    return Path(__file__).resolve().parent / "defaults" / "acl_paths.yaml"


@dataclass(frozen=True)
class Settings:
    files_root: Path
    acl_path: Path
    manifest_path: Path
    dex_issuer: str
    dex_client_id: str
    dex_client_secret: str
    dex_jwks_url: str | None
    oidc_redirect_uri: str
    session_secret: str
    app_public_url: str | None
    dlp_url: str | None
    dlp_wait_seconds: float
    audit_log_path: str
    tls_cert: Path
    tls_key: Path
    bind_host: str
    bind_port: int
    cookie_secure: bool

    @classmethod
    def from_env(cls) -> Settings:
        issuer = os.environ.get("DEX_ISSUER", "").strip().rstrip("/")
        client_id = os.environ.get("DEX_CLIENT_ID", "").strip()
        client_secret = os.environ.get("DEX_CLIENT_SECRET", "").strip()
        jwks_raw = os.environ.get("DEX_JWKS_URL", "").strip()
        jwks = jwks_raw or None
        dlp_raw = os.environ.get("DLP_URL", "").strip().rstrip("/")
        dlp = dlp_raw or None
        redirect = os.environ.get("OIDC_REDIRECT_URI", "").strip()
        session_secret = os.environ.get("SESSION_SECRET", "").strip()
        if not session_secret:
            session_secret = secrets.token_urlsafe(32)
        public = os.environ.get("APP_PUBLIC_URL", "").strip().rstrip("/") or None
        cookie_secure = os.environ.get("COOKIE_SECURE", "1").strip() not in {
            "0",
            "false",
            "False",
        }
        return cls(
            files_root=Path(os.environ.get("FILES_ROOT", "/files")),
            acl_path=Path(os.environ.get("ACL_PATH", str(_default_acl_path()))),
            manifest_path=Path(
                os.environ.get("MANIFEST_PATH", "/app/data/manifest.json")
            ),
            dex_issuer=issuer,
            dex_client_id=client_id,
            dex_client_secret=client_secret,
            dex_jwks_url=jwks,
            oidc_redirect_uri=redirect,
            session_secret=session_secret,
            app_public_url=public,
            dlp_url=dlp,
            dlp_wait_seconds=float(os.environ.get("DLP_WAIT_SECONDS", "30")),
            audit_log_path=os.environ.get("AUDIT_LOG_PATH", "-"),
            tls_cert=Path(os.environ.get("TLS_CERT_PATH", "/certs/cert.pem")),
            tls_key=Path(os.environ.get("TLS_KEY_PATH", "/certs/key.pem")),
            bind_host=os.environ.get("BIND_HOST", "0.0.0.0"),
            bind_port=int(os.environ.get("BIND_PORT", "8443")),
            cookie_secure=cookie_secure,
        )

    def require_dex(self) -> None:
        if not self.dex_issuer or not self.dex_client_id:
            raise RuntimeError(
                "DEX_ISSUER and DEX_CLIENT_ID are required for authentication"
            )
        parsed = urlparse(self.dex_issuer)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(
                "DEX_ISSUER must be an absolute http(s) URL, e.g. "
                f"https://dex.example/dex (got {self.dex_issuer!r})"
            )
        if self.dex_jwks_url:
            jwks = urlparse(self.dex_jwks_url)
            if jwks.scheme not in {"http", "https"} or not jwks.netloc:
                raise RuntimeError(
                    "DEX_JWKS_URL must be an absolute http(s) URL "
                    f"(got {self.dex_jwks_url!r})"
                )

    def oidc_login_configured(self) -> bool:
        if not self.dex_client_secret or not self.oidc_redirect_uri:
            return False
        parsed = urlparse(self.oidc_redirect_uri)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def post_logout_redirect_uri(self) -> str:
        """Exact URI registered on the Dex client for RP-initiated logout."""
        if self.app_public_url:
            return f"{self.app_public_url.rstrip('/')}/"
        parsed = urlparse(self.oidc_redirect_uri)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/"
        return "/"
