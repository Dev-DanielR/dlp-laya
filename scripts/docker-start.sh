#!/usr/bin/env bash
# Start the local dlp-laya container (detached, named, reusable).
# Not the VM archive runner — that is docker/run.sh after tarball load.
# Usage:
#   ./scripts/docker-start.sh
# Optional: IMAGE, CONTAINER_NAME, PORT, ENV_FILE, EXTRA_DOCKER_ARGS,
#           ENABLE_GPU (default 1), LAYA_DEVICE (default cuda when GPU else cpu).
# Do not use bare NAME — WSL exports NAME=<Windows computer name> (e.g. user-node).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-dlp-laya}"
CONTAINER_NAME="${CONTAINER_NAME:-dlp-laya}"
PORT="${PORT:-8443}"
ENV_FILE="${ENV_FILE:-$ROOT/docker/.env}"
ENABLE_GPU="${ENABLE_GPU:-1}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: ${ENV_FILE} (copy docker/.env.example)." >&2
  exit 1
fi

# Source so shell-quoted values in .env work (docker --env-file would keep quotes).
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DEX_ISSUER:-}" || -z "${DEX_CLIENT_ID:-}" ]]; then
  echo "Set DEX_ISSUER and DEX_CLIENT_ID in ${ENV_FILE}." >&2
  exit 1
fi

want_mode="${CLASSIFY_MODE:-stub}"
FORCE="${FORCE:-0}"

_container_env() {
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$1" \
    | sed -n "s/^${2}=//p" | head -1
}

if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  have_mode="$(_container_env "${CONTAINER_NAME}" CLASSIFY_MODE)"
  have_mode="${have_mode:-stub}"
  have_image="$(docker inspect -f '{{.Config.Image}}' "${CONTAINER_NAME}")"
  stale=0
  if [[ "$have_mode" != "$want_mode" ]]; then
    echo "Container ${CONTAINER_NAME} has CLASSIFY_MODE=${have_mode}, .env wants ${want_mode}"
    stale=1
  fi
  if [[ "$have_image" != "$IMAGE" ]]; then
    echo "Container ${CONTAINER_NAME} image is ${have_image}, want ${IMAGE}"
    stale=1
  fi
  if [[ "$FORCE" == "1" ]]; then
    stale=1
  fi
  if [[ "$stale" -eq 1 ]]; then
    echo "Recreating ${CONTAINER_NAME} (FORCE=${FORCE})"
    docker rm -f "${CONTAINER_NAME}" >/dev/null
  elif docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    echo "Container ${CONTAINER_NAME} is already running (CLASSIFY_MODE=${have_mode})."
    docker ps --filter "name=^${CONTAINER_NAME}$"
    echo "Check: ./scripts/docker-status.sh"
    exit 0
  else
    echo "Starting existing container ${CONTAINER_NAME} (CLASSIFY_MODE=${have_mode})"
    docker start "${CONTAINER_NAME}"
    docker ps --filter "name=^${CONTAINER_NAME}$"
    echo "Check: ./scripts/docker-status.sh"
    exit 0
  fi
fi

# Classify SQLite + TLS certs on named volumes. Laya weights are baked at
# /opt/laya-cache in the image — do not mount over that path.
VOL_DLP="${VOL_DLP:-dlp-laya-dlp}"
VOL_CERTS="${VOL_CERTS:-dlp-laya-certs}"
docker volume create "${VOL_DLP}" >/dev/null
docker volume create "${VOL_CERTS}" >/dev/null

GPU_ARGS=()
if [[ "$ENABLE_GPU" == "1" ]] && [[ "${want_mode}" == "dlp" ]]; then
  GPU_ARGS=(--gpus all)
  LAYA_DEVICE="${LAYA_DEVICE:-cuda}"
  echo "GPU passthrough requested (--gpus all); LAYA_DEVICE=${LAYA_DEVICE}"
else
  LAYA_DEVICE="${LAYA_DEVICE:-cpu}"
fi

# Baked cache path inside the image (see docker/Dockerfile).
LAYA_CACHE_DIR="${LAYA_CACHE_DIR:-/opt/laya-cache}"
# Weights are local; skip HF round-trips unless a revision is missing.
HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
DLP_WARMUP_DELAY_SECONDS="${DLP_WARMUP_DELAY_SECONDS:-0}"

_run_container() {
  # shellcheck disable=SC2086
  docker run -d --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    --init \
    "${GPU_ARGS[@]}" \
    -p "${PORT}:${PORT}" \
    -v "${VOL_DLP}:/var/lib/dlp" \
    -v "${VOL_CERTS}:/certs" \
    -e "BIND_PORT=${PORT}" \
    -e "DEX_ISSUER=${DEX_ISSUER}" \
    -e "DEX_CLIENT_ID=${DEX_CLIENT_ID}" \
    -e "HF_HUB_DISABLE_XET=${HF_HUB_DISABLE_XET:-1}" \
    -e "HF_HUB_OFFLINE=${HF_HUB_OFFLINE}" \
    -e "OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}" \
    -e "MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}" \
    -e "TOKENIZERS_PARALLELISM=false" \
    -e "DLP_WARMUP_DELAY_SECONDS=${DLP_WARMUP_DELAY_SECONDS}" \
    -e "LAYA_DEVICE=${LAYA_DEVICE}" \
    -e "LAYA_CACHE_DIR=${LAYA_CACHE_DIR}" \
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
    ${LAYA_THRESHOLD:+-e "LAYA_THRESHOLD=${LAYA_THRESHOLD}"} \
    ${LAYA_REGION:+-e "LAYA_REGION=${LAYA_REGION}"} \
    ${EXTRA_DOCKER_ARGS:-} \
    "${IMAGE}"
}

echo "Creating ${CONTAINER_NAME} from ${IMAGE} on :${PORT} (CLASSIFY_MODE=${want_mode})"
# --restart: NetBird VPN flaps often SIGTERM Docker containers during Sign-in.
# --init: proper PID 1 so the background DLP child cannot orphan awkwardly.
if ! _run_container; then
  if [[ ${#GPU_ARGS[@]} -gt 0 ]]; then
    echo "WARNING: docker run with --gpus failed (NVIDIA Container Toolkit / Docker Desktop GPU?)." >&2
    echo "Retrying without GPU; Laya will use CPU (slow)." >&2
    GPU_ARGS=()
    LAYA_DEVICE=cpu
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    _run_container
  else
    exit 1
  fi
fi

docker ps --filter "name=^${CONTAINER_NAME}$"
echo "https://localhost:${PORT}/"
echo "LAYA_DEVICE=${LAYA_DEVICE}  LAYA_CACHE_DIR=${LAYA_CACHE_DIR}  HF_HUB_OFFLINE=${HF_HUB_OFFLINE}"
echo "Note: if Sign-in flaps NetBird/Docker, --restart unless-stopped brings the container back."
