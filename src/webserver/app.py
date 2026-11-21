"""Flask application factory."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from webserver.acl import AclStore
from webserver.audit import AuditLogger
from webserver.auth.dex import DexValidator
from webserver.auth.oidc import OidcClient
from webserver.auth.session import SessionStore
from webserver.config import Settings
from webserver.dlp.http_client import HttpDlpClient
from webserver.dlp.manifest_stub import ManifestDlpStub
from webserver.routes.files import bp as files_bp
from webserver.routes.ui import bp as ui_bp


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings.from_env()
    settings.require_dex()

    pkg = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(pkg / "templates"),
        static_folder=str(pkg / "static"),
    )
    app.config["SETTINGS"] = settings
    app.config["ACL"] = AclStore.load(settings.acl_path)
    app.config["AUDIT"] = AuditLogger(settings.audit_log_path)
    app.config["SESSION"] = SessionStore(settings.session_secret)
    app.config["DEX"] = DexValidator(
        issuer=settings.dex_issuer,
        client_id=settings.dex_client_id,
        jwks_url=settings.dex_jwks_url,
    )
    if settings.oidc_login_configured():
        app.config["OIDC"] = OidcClient(
            issuer=settings.dex_issuer,
            client_id=settings.dex_client_id,
            client_secret=settings.dex_client_secret,
            redirect_uri=settings.oidc_redirect_uri,
            dex=app.config["DEX"],
        )
    else:
        app.config["OIDC"] = None

    # CLASSIFY_MODE=stub keeps ManifestDlpStub for A/B vs live DLP.
    if settings.classify_mode == "dlp":
        if not settings.dlp_url:
            raise RuntimeError("CLASSIFY_MODE=dlp requires DLP_URL")
        app.config["DLP"] = HttpDlpClient(settings.dlp_url)
    else:
        app.config["DLP"] = ManifestDlpStub(settings.manifest_path)

    app.register_blueprint(files_bp)
    app.register_blueprint(ui_bp)

    @app.teardown_appcontext
    def _close_audit(_exc=None):
        return None

    return app
