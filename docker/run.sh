#!/usr/bin/env bash
# VM / archive entrypoint: run the exported dlp-laya image on a deployment host.
# After `docker load` of the tarball on the VM, copy this script alongside and execute it.
#
# Local WSL/dev workflows: use scripts/docker-{build,start,stop,attach}.sh instead.
#
# Usage (on the VM):
#   ./run.sh
# Optional: IMAGE (default dlp-laya), PORT (default 8443), ENV_FILE, EXTRA_DOCKER_ARGS.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# When shipped as archives/<name>/run.sh next to .env, prefer sibling .env.
if [[ -f "$(dirname "${BASH_SOURCE[0]}")/.env" ]]; then
  ENV_FILE="${ENV_FILE:-$(dirname "${BASH_SOURCE[0]}")/.env}"
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  ENV_FILE="${ENV_FILE:-$ROOT/docker/.env}"
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

IMAGE="${IMAGE:-dlp-laya}"
PORT="${PORT:-8443}"
# WSL exports NAME=<Windows computer name>. Prefer CONTAINER_NAME; accept NAME
# only when it differs from the host name (Knowsyn deploy sets NAME=…).
_default_container=dlp-laya
_host="$(hostname 2>/dev/null || true)"
if [[ -n "${CONTAINER_NAME:-}" ]]; then
  NAME="$CONTAINER_NAME"
elif [[ -z "${NAME:-}" || "$NAME" == "$_host" ]]; then
  NAME="$_default_container"
fi

if [[ -z "${DEX_ISSUER:-}" || -z "${DEX_CLIENT_ID:-}" ]]; then
  echo "Set DEX_ISSUER and DEX_CLIENT_ID (e.g. in .env)." >&2
  exit 1
fi

exec docker run --rm --name "${NAME}" -p "${PORT}:${PORT}" \
  -e "BIND_PORT=${PORT}" \
  -e "DEX_ISSUER=${DEX_ISSUER}" \
  -e "DEX_CLIENT_ID=${DEX_CLIENT_ID}" \
  ${DEX_CLIENT_SECRET:+-e "DEX_CLIENT_SECRET=${DEX_CLIENT_SECRET}"} \
  ${DEX_JWKS_URL:+-e "DEX_JWKS_URL=${DEX_JWKS_URL}"} \
  ${OIDC_REDIRECT_URI:+-e "OIDC_REDIRECT_URI=${OIDC_REDIRECT_URI}"} \
  ${SESSION_SECRET:+-e "SESSION_SECRET=${SESSION_SECRET}"} \
  ${APP_PUBLIC_URL:+-e "APP_PUBLIC_URL=${APP_PUBLIC_URL}"} \
  ${COOKIE_SECURE:+-e "COOKIE_SECURE=${COOKIE_SECURE}"} \
  ${CLASSIFY_MODE:+-e "CLASSIFY_MODE=${CLASSIFY_MODE}"} \
  ${DLP_URL:+-e "DLP_URL=${DLP_URL}"} \
  ${DLP_PORT:+-e "DLP_PORT=${DLP_PORT}"} \
  ${DLP_AUTOSTART:+-e "DLP_AUTOSTART=${DLP_AUTOSTART}"} \
  ${DLP_DETECTOR:+-e "DLP_DETECTOR=${DLP_DETECTOR}"} \
  ${DLP_DEBOUNCE_SECONDS:+-e "DLP_DEBOUNCE_SECONDS=${DLP_DEBOUNCE_SECONDS}"} \
  ${DLP_LOCK_SECONDS:+-e "DLP_LOCK_SECONDS=${DLP_LOCK_SECONDS}"} \
  ${DLP_WAIT_SECONDS:+-e "DLP_WAIT_SECONDS=${DLP_WAIT_SECONDS}"} \
  ${LAYA_DEVICE:+-e "LAYA_DEVICE=${LAYA_DEVICE}"} \
  ${LAYA_THRESHOLD:+-e "LAYA_THRESHOLD=${LAYA_THRESHOLD}"} \
  ${LAYA_REGION:+-e "LAYA_REGION=${LAYA_REGION}"} \
  ${LAYA_CACHE_DIR:+-e "LAYA_CACHE_DIR=${LAYA_CACHE_DIR}"} \
  ${EXTRA_DOCKER_ARGS:-} \
  "${IMAGE}"
