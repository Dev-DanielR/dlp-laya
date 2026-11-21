"""python -m webserver — development entry (HTTP; TLS via gunicorn in Docker)."""

from __future__ import annotations

import os

from webserver.app import create_app
from webserver.config import Settings


def main() -> None:
    settings = Settings.from_env()
    app = create_app(settings)
    # Dev convenience: plain HTTP unless TLS paths exist and USE_TLS=1
    use_tls = os.environ.get("USE_TLS", "0") == "1"
    ssl_ctx = None
    if use_tls and settings.tls_cert.is_file() and settings.tls_key.is_file():
        ssl_ctx = (str(settings.tls_cert), str(settings.tls_key))
    app.run(
        host=settings.bind_host,
        port=settings.bind_port if use_tls else int(os.environ.get("PORT", "8080")),
        ssl_context=ssl_ctx,
    )


if __name__ == "__main__":
    main()
