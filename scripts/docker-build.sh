#!/usr/bin/env bash
# Build the local dlp-laya image (docker-in-WSL / Linux).
# Usage:
#   ./scripts/docker-build.sh
#   WITH_DLP=0 ./scripts/docker-build.sh
#   WITH_GPU=1 ./scripts/docker-build.sh   # CUDA torch + baked Laya weights
# Optional: IMAGE (default dlp-laya), WITH_DLP (default 1), WITH_GPU (default 1).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-dlp-laya}"
WITH_DLP="${WITH_DLP:-1}"
WITH_GPU="${WITH_GPU:-1}"

cd "$ROOT"
echo "Building ${IMAGE} (WITH_DLP=${WITH_DLP} WITH_GPU=${WITH_GPU})"
exec docker build \
  --build-arg "WITH_DLP=${WITH_DLP}" \
  --build-arg "WITH_GPU=${WITH_GPU}" \
  -f docker/Dockerfile \
  -t "${IMAGE}" \
  .
