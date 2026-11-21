#!/usr/bin/env bash
# Build the local dlp-laya image (docker-in-WSL / Linux).
# Usage:
#   ./scripts/docker-build.sh
#   WITH_DLP=0 ./scripts/docker-build.sh
# Optional: IMAGE (default dlp-laya), WITH_DLP (default 1).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-dlp-laya}"
WITH_DLP="${WITH_DLP:-1}"

cd "$ROOT"
echo "Building ${IMAGE} (WITH_DLP=${WITH_DLP})"
exec docker build \
  --build-arg "WITH_DLP=${WITH_DLP}" \
  -f docker/Dockerfile \
  -t "${IMAGE}" \
  .
