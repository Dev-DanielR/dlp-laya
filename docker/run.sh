#!/usr/bin/env bash
# Run the self-contained dlp-laya-web image.
# Loads docker/.env when present (DEX_*, OIDC_*, SESSION_SECRET, …).
# Usage:
#   ./docker/run.sh
# Optional: IMAGE, PORT (default 8443), EXTRA_DOCKER_ARGS.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/docker/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

IMAGE="${IMAGE:-dlp-laya-web}"
PORT="${PORT:-8443}"

if [[ -z "${DEX_ISSUER:-}" || -z "${DEX_CLIENT_ID:-}" ]]; then
  echo "Set DEX_ISSUER and DEX_CLIENT_ID (e.g. in docker/.env)." >&2
  exit 1
fi

exec docker run --rm -p "${PORT}:${PORT}" \
  -e "BIND_PORT=${PORT}" \
  -e "DEX_ISSUER=${DEX_ISSUER}" \
  -e "DEX_CLIENT_ID=${DEX_CLIENT_ID}" \
  ${DEX_CLIENT_SECRET:+-e "DEX_CLIENT_SECRET=${DEX_CLIENT_SECRET}"} \
  ${DEX_JWKS_URL:+-e "DEX_JWKS_URL=${DEX_JWKS_URL}"} \
  ${OIDC_REDIRECT_URI:+-e "OIDC_REDIRECT_URI=${OIDC_REDIRECT_URI}"} \
  ${SESSION_SECRET:+-e "SESSION_SECRET=${SESSION_SECRET}"} \
  ${APP_PUBLIC_URL:+-e "APP_PUBLIC_URL=${APP_PUBLIC_URL}"} \
  ${COOKIE_SECURE:+-e "COOKIE_SECURE=${COOKIE_SECURE}"} \
  ${DLP_URL:+-e "DLP_URL=${DLP_URL}"} \
  ${EXTRA_DOCKER_ARGS:-} \
  "${IMAGE}"
