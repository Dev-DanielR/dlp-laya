#!/usr/bin/env bash
# Attach an interactive shell to the local dlp-laya container.
# Usage:
#   ./scripts/docker-attach.sh
# Optional: CONTAINER_NAME (default dlp-laya).
# Do not use bare NAME — WSL exports NAME=<Windows computer name>.

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-dlp-laya}"

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  echo "Container ${CONTAINER_NAME} is not running. Start it with ./scripts/docker-start.sh" >&2
  exit 1
fi

if docker exec "${CONTAINER_NAME}" sh -c 'command -v bash' >/dev/null 2>&1; then
  exec docker exec -it "${CONTAINER_NAME}" bash
fi
exec docker exec -it "${CONTAINER_NAME}" sh
