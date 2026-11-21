#!/usr/bin/env bash
# Show local dlp-laya container state and DLP/web health (no ps/curl needed in image).
# Usage: ./scripts/docker-status.sh
# Optional: CONTAINER_NAME (default dlp-laya), IMAGE (default dlp-laya), PORT (default 8443)
# Do not use bare NAME — WSL exports NAME=<Windows computer name>.

set -euo pipefail

IMAGE="${IMAGE:-dlp-laya}"
PORT="${PORT:-8443}"
CONTAINER_NAME="${CONTAINER_NAME:-dlp-laya}"

if ! docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  # Migration: older scripts used NAME="${NAME:-dlp-laya}" and WSL injects
  # NAME=<Windows computer name>, so the container was often named like user-node.
  renamed=""
  for cand in "${NAME:-}" "$(hostname 2>/dev/null || true)"; do
    [[ -z "$cand" || "$cand" == "$CONTAINER_NAME" ]] && continue
    if docker ps -a --format '{{.Names}}' | grep -qx "$cand" \
      && [[ "$(docker inspect -f '{{.Config.Image}}' "$cand" 2>/dev/null || true)" == "$IMAGE" ]]; then
      echo "Found misnamed container '${cand}' (WSL NAME= collision). Renaming to ${CONTAINER_NAME}."
      docker rename "$cand" "${CONTAINER_NAME}"
      renamed=1
      break
    fi
  done
  if [[ -z "$renamed" ]]; then
    echo "Container ${CONTAINER_NAME}: not found"
    echo "Start with: ./scripts/docker-start.sh"
    exit 1
  fi
fi

echo "=== container (${CONTAINER_NAME}) ==="
docker inspect -f 'name={{.Name}} status={{.State.Status}} image={{.Config.Image}} ports={{json .NetworkSettings.Ports}}' \
  "${CONTAINER_NAME}"

echo
echo "=== env (classify) ==="
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "${CONTAINER_NAME}" \
  | grep -E '^(CLASSIFY_MODE|DLP_|LAYA_|DEX_ISSUER|DEX_CLIENT_ID)=' \
  || true

running=0
if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  running=1
fi

echo
echo "=== recent logs ==="
docker logs --tail 40 "${CONTAINER_NAME}" 2>&1 || true

if [[ "$running" -ne 1 ]]; then
  echo
  echo "Container is not running. Start or recreate: ./scripts/docker-start.sh"
  exit 1
fi

echo
echo "=== DLP loopback /healthz (inside container via python) ==="
classify="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "${CONTAINER_NAME}" | sed -n 's/^CLASSIFY_MODE=//p' | head -1)"
classify="${classify:-stub}"
dlp_port="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "${CONTAINER_NAME}" | sed -n 's/^DLP_PORT=//p' | head -1)"
dlp_port="${dlp_port:-8091}"
if [[ "$classify" == "dlp" ]]; then
  if docker exec "${CONTAINER_NAME}" python -c "
import urllib.request, sys
try:
    r = urllib.request.urlopen('http://127.0.0.1:${dlp_port}/healthz', timeout=3)
    print(r.read().decode())
    sys.exit(0)
except Exception as e:
    print('DLP health check failed:', e, file=sys.stderr)
    sys.exit(1)
"; then
    echo "DLP: ok"
  else
    echo "DLP: DOWN (daemon not answering on 127.0.0.1:${dlp_port})"
    exit 1
  fi
else
  echo "CLASSIFY_MODE=${classify} (stub - no DLP daemon expected)"
fi

echo
echo "=== web /healthz (inside container via python) ==="
bind_port="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "${CONTAINER_NAME}" | sed -n 's/^BIND_PORT=//p' | head -1)"
bind_port="${bind_port:-$PORT}"
if docker exec "${CONTAINER_NAME}" python -c "
import ssl, urllib.request, sys
ctx = ssl._create_unverified_context()
try:
    r = urllib.request.urlopen('https://127.0.0.1:${bind_port}/healthz', context=ctx, timeout=5)
    print(r.read().decode())
except Exception as e:
    print('web health check failed:', e, file=sys.stderr)
    sys.exit(1)
"; then
  echo "web: ok  https://localhost:${bind_port}/"
else
  echo "web: DOWN"
  exit 1
fi
