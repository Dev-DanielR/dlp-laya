#!/usr/bin/env bash
# Run Playwright UC04 against the local dlp-laya container (real NetBird OIDC).
# Usage (inside WSL, with container up on :8443):
#   ./scripts/e2e-uc04.sh
# Credentials come from docker/.env (USER_*_EMAIL / USER_*_PASS).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f docker/.env ]]; then
  echo "Missing docker/.env (need USER_ALTA_*/USER_MEDIA_*/USER_BAJA_*)." >&2
  exit 1
fi

export E2E_BASE_URL="${E2E_BASE_URL:-https://localhost:8443}"

if [[ ! -d node_modules/@playwright/test ]]; then
  npm install
  npx playwright install chromium
  # Shared libs (libglib, etc.) — needs sudo once on a fresh WSL distro.
  if ! ldconfig -p 2>/dev/null | grep -q libglib-2.0.so.0; then
    sudo npx playwright install-deps chromium || true
  fi
fi

echo "E2E_BASE_URL=${E2E_BASE_URL}"
exec npx playwright test tests/e2e/uc04-completo-sanitizado-denegado.spec.ts "$@"
