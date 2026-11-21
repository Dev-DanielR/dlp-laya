#!/bin/sh
set -eu

CERT="${TLS_CERT_PATH:-/certs/cert.pem}"
KEY="${TLS_KEY_PATH:-/certs/key.pem}"
HOST="${BIND_HOST:-0.0.0.0}"
PORT="${BIND_PORT:-8443}"

mkdir -p "$(dirname "$CERT")" "$(dirname "$KEY")"

if [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
  echo "Generating self-signed TLS certificate at $CERT"
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY" \
    -out "$CERT" \
    -days 365 \
    -subj "/CN=dlp-laya-web"
fi

if [ -z "${DEX_ISSUER:-}" ] || [ -z "${DEX_CLIENT_ID:-}" ]; then
  echo "ERROR: DEX_ISSUER and DEX_CLIENT_ID are required" >&2
  exit 1
fi

case "${DEX_ISSUER}" in
  http://*|https://*) ;;
  *)
    echo "ERROR: DEX_ISSUER must start with http:// or https:// (got: ${DEX_ISSUER})" >&2
    echo "Example: DEX_ISSUER=https://127.0.0.1:5556/dex" >&2
    exit 1
    ;;
esac

if [ -n "${DEX_JWKS_URL:-}" ]; then
  case "${DEX_JWKS_URL}" in
    http://*|https://*) ;;
    *)
      echo "ERROR: DEX_JWKS_URL must start with http:// or https:// (got: ${DEX_JWKS_URL})" >&2
      exit 1
      ;;
  esac
  echo "Dex JWKS: ${DEX_JWKS_URL}"
else
  echo "Dex issuer: ${DEX_ISSUER} (JWKS default ${DEX_ISSUER%/}/keys)"
fi

exec gunicorn \
  --bind "${HOST}:${PORT}" \
  --certfile "$CERT" \
  --keyfile "$KEY" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  "webserver.app:create_app()"
