#!/bin/sh
set -eu

CERT="${TLS_CERT_PATH:-/certs/cert.pem}"
KEY="${TLS_KEY_PATH:-/certs/key.pem}"
HOST="${BIND_HOST:-0.0.0.0}"
PORT="${BIND_PORT:-8443}"
CLASSIFY_MODE="${CLASSIFY_MODE:-stub}"
DLP_PORT="${DLP_PORT:-8091}"
DLP_AUTOSTART="${DLP_AUTOSTART:-1}"

mkdir -p "$(dirname "$CERT")" "$(dirname "$KEY")"
mkdir -p /var/lib/dlp /var/cache/laya

if [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
  echo "Generating self-signed TLS certificate at $CERT"
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY" \
    -out "$CERT" \
    -days 365 \
    -subj "/CN=dlp-laya"
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

echo "CLASSIFY_MODE=${CLASSIFY_MODE}"

# Unbuffered Python so DLP / gunicorn logs show up under docker logs.
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

DLP_PID=""
if [ "${CLASSIFY_MODE}" = "dlp" ] && [ "${DLP_AUTOSTART}" != "0" ]; then
  export DLP_URL="${DLP_URL:-http://127.0.0.1:${DLP_PORT}}"
  export DLP_BIND_HOST="${DLP_BIND_HOST:-127.0.0.1}"
  echo "Starting DLP daemon on ${DLP_BIND_HOST}:${DLP_PORT} (DLP_URL=${DLP_URL})"
  echo "Laya cache: ${LAYA_CACHE_DIR:-/opt/laya-cache}  device: ${LAYA_DEVICE:-auto}  HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-0}"
  echo "Laya weights load in background after /healthz (watcher paused until startup batch finishes)"
  # Keep DLP on the same stdout/stderr as the container (docker logs).
  python -u -m dlp_service &
  DLP_PID=$!
  # /healthz binds before model download (lazy Laya). Keep this short.
  i=0
  max="${DLP_READY_TIMEOUT:-60}"
  until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${DLP_PORT}/healthz', timeout=2)" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -gt "$max" ]; then
      echo "ERROR: DLP daemon did not become healthy within ${max}s" >&2
      echo "Hint: from host run  docker logs <container>  or  ./scripts/docker-status.sh" >&2
      kill "${DLP_PID}" 2>/dev/null || true
      wait "${DLP_PID}" 2>/dev/null || true
      exit 1
    fi
    if ! kill -0 "${DLP_PID}" 2>/dev/null; then
      wait "${DLP_PID}" 2>/dev/null || true
      echo "ERROR: DLP daemon exited early (see logs above)" >&2
      exit 1
    fi
    if [ $((i % 5)) -eq 0 ]; then
      echo "Still waiting for DLP /healthz ... ${i}s/${max}s"
    fi
    sleep 1
  done
  echo "DLP daemon is healthy (pid ${DLP_PID}) — model may still be loading"
fi

# Ensure child gunicorn inherits DLP_URL when in dlp mode.
if [ "${CLASSIFY_MODE}" = "dlp" ]; then
  export DLP_URL="${DLP_URL:-http://127.0.0.1:${DLP_PORT}}"
  # One worker saves RAM while Laya + torch are resident.
  export WEB_CONCURRENCY="${WEB_CONCURRENCY:-1}"
fi

exec gunicorn \
  --bind "${HOST}:${PORT}" \
  --certfile "$CERT" \
  --keyfile "$KEY" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  "webserver.app:create_app()"
