#!/usr/bin/env bash
# Stop and remove the local dlp-laya container.
# Usage:
#   ./scripts/docker-stop.sh
# Optional: CONTAINER_NAME (default dlp-laya), KEEP=1 to stop without rm.
# Do not use bare NAME — WSL exports NAME=<Windows computer name>.

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-dlp-laya}"
KEEP="${KEEP:-0}"

if ! docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  echo "No container named ${CONTAINER_NAME}."
  exit 0
fi

if docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  echo "Stopping ${CONTAINER_NAME}"
  docker stop "${CONTAINER_NAME}"
fi

if [[ "${KEEP}" == "1" ]]; then
  echo "Kept stopped container ${CONTAINER_NAME} (KEEP=1)."
  exit 0
fi

echo "Removing ${CONTAINER_NAME}"
docker rm "${CONTAINER_NAME}"
