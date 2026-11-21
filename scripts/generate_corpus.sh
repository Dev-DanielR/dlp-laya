#!/usr/bin/env bash
# Generate Andes Advisory corpus (DAP Laya).
# Usage:
#   ./scripts/generate_corpus.sh --dry-run
#   ./scripts/generate_corpus.sh --seed 20261114
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
elif [[ -x "${ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON="${ROOT}/.venv/Scripts/python.exe"
else
  echo "Local venv not found under ${ROOT}/.venv. Create it with: python -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
exec "$PYTHON" -m corpus_gen "$@"
