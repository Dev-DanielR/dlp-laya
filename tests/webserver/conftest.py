"""Shared fixtures for webserver tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from webserver.acl import AclStore
from webserver.audit import AuditLogger
from webserver.auth.dex import DexValidator
from webserver.auth.session import SessionStore, SessionUser
from webserver.config import Settings
from webserver.dlp.manifest_stub import ManifestDlpStub

ISSUER = "https://dex.test.local"
CLIENT_ID = "dlp-laya-test"
ROOT = Path(__file__).resolve().parents[2]
ACL_PATH = ROOT / "src" / "webserver" / "defaults" / "acl_paths.yaml"
MANIFEST_PATH = ROOT / "data" / "manifest.json"
FILES_ROOT = ROOT / "data" / "files"


@pytest.fixture(scope="session")
def rsa_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return key, private_pem, public_pem


@pytest.fixture(scope="session")
def jwks_and_kid(rsa_keypair):
    key, _priv, _pub = rsa_keypair
    jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    jwk["kid"] = "test-kid"
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return {"keys": [jwk]}, "test-kid"


class StaticPyJWKClient:
    """Minimal stand-in for jwt.PyJWKClient using an in-memory JWKS."""

    def __init__(self, jwks: dict):
        from jwt import PyJWK

        self._keys = {k["kid"]: PyJWK.from_dict(k) for k in jwks["keys"]}

    def get_signing_key_from_jwt(self, token: str):
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if kid not in self._keys:
            raise jwt.PyJWTError(f"unknown kid {kid}")
        return self._keys[kid]


@pytest.fixture
def dex_validator(rsa_keypair, jwks_and_kid):
    jwks, _kid = jwks_and_kid
    return DexValidator(
        issuer=ISSUER,
        client_id=CLIENT_ID,
        jwks_client=StaticPyJWKClient(jwks),
    )


@pytest.fixture
def mint_token(rsa_keypair, jwks_and_kid):
    _key, private_pem, _pub = rsa_keypair
    _jwks, kid = jwks_and_kid

    def _mint(
        username: str = "ana.alta@knowsyn.dev",
        *,
        aud: str = CLIENT_ID,
        issuer: str = ISSUER,
        exp_delta: int = 3600,
        email: str | None = None,
        use_preferred: bool = True,
    ) -> str:
        now = int(time.time())
        claims = {
            "iss": issuer,
            "aud": aud,
            "iat": now,
            "exp": now + exp_delta,
            "sub": f"user-{username}",
        }
        if use_preferred:
            claims["preferred_username"] = username
        if email:
            claims["email"] = email
        return jwt.encode(
            claims,
            private_pem,
            algorithm="RS256",
            headers={"kid": kid},
        )

    return _mint


@pytest.fixture
def acl_store():
    return AclStore.load(ACL_PATH)


@pytest.fixture
def app(dex_validator, tmp_path):
    if not MANIFEST_PATH.is_file() or not FILES_ROOT.is_dir():
        pytest.skip("corpus data/files and manifest.json required")

    settings = Settings(
        files_root=FILES_ROOT,
        acl_path=ACL_PATH,
        manifest_path=MANIFEST_PATH,
        dex_issuer=ISSUER,
        dex_client_id=CLIENT_ID,
        dex_client_secret="test-secret",
        dex_jwks_url=None,
        oidc_redirect_uri="https://localhost:8443/auth/callback",
        session_secret="test-session-secret-not-for-prod",
        app_public_url="https://localhost:8443",
        dlp_url=None,
        dlp_wait_seconds=2.0,
        audit_log_path=str(tmp_path / "audit.jsonl"),
        tls_cert=tmp_path / "cert.pem",
        tls_key=tmp_path / "key.pem",
        bind_host="127.0.0.1",
        bind_port=8443,
        cookie_secure=False,
    )
    from webserver.app import create_app

    application = create_app(settings)
    application.config["DEX"] = dex_validator
    application.config["DLP"] = ManifestDlpStub(MANIFEST_PATH)
    application.config["AUDIT"] = AuditLogger(str(tmp_path / "audit.jsonl"))
    application.config["SESSION"] = SessionStore(settings.session_secret)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session_cookie(app):
    store: SessionStore = app.config["SESSION"]

    def _set(client, username: str = "ana.alta@knowsyn.dev"):
        user = SessionUser(username=username, email=username)
        token = store.dump_user(user)
        client.set_cookie("dlp_session", token)
        return client

    return _set
