#!/usr/bin/env bash
set -euo pipefail

# Starts:
#  - backend (mock mode) on SHENLAB_E2E_BACKEND_PORT (default 5090)
#  - frontend (static) on SHENLAB_E2E_FRONTEND_PORT (default 5180)
#
# This script is meant to be launched by Playwright's webServer and kept running.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "${SHENLAB_FRONTEND_DIR:-}" ]]; then
  FRONTEND_DIR="${SHENLAB_FRONTEND_DIR}"
elif [[ -d "${ROOT_DIR}/../shenlab-web" ]]; then
  FRONTEND_DIR="${ROOT_DIR}/../shenlab-web"
elif [[ -d "${ROOT_DIR}/../17-lab-web" ]]; then
  FRONTEND_DIR="${ROOT_DIR}/../17-lab-web"
else
  FRONTEND_DIR="${ROOT_DIR}/../shenlab-web"
fi

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "ERROR: frontend dir not found: ${FRONTEND_DIR}" >&2
  echo "Set SHENLAB_FRONTEND_DIR to your web checkout (e.g. /path/to/shenlab-web)." >&2
  exit 1
fi

export SHENLAB_MOCK=1
export SHENLAB_DATA_DIR="${SHENLAB_DATA_DIR:-$(mktemp -d)}"
BACKEND_PORT="${SHENLAB_E2E_BACKEND_PORT:-5090}"
FRONTEND_PORT="${SHENLAB_E2E_FRONTEND_PORT:-5180}"

BACKEND_LOG="${SHENLAB_DATA_DIR}/backend.log"
FRONTEND_LOG="${SHENLAB_DATA_DIR}/frontend.log"

cleanup() {
  set +e
  [[ -n "${BACK_PID:-}" ]] && kill "${BACK_PID}" 2>/dev/null || true
  [[ -n "${FRONT_PID:-}" ]] && kill "${FRONT_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"

uvicorn alphafold_multimer_service.api:create_app --factory --host 127.0.0.1 --port "${BACKEND_PORT}" >"${BACKEND_LOG}" 2>&1 &
BACK_PID=$!

python -m http.server "${FRONTEND_PORT}" --bind 127.0.0.1 --directory "${FRONTEND_DIR}" >"${FRONTEND_LOG}" 2>&1 &
FRONT_PID=$!

wait_http() {
  local url="$1"
  local name="$2"
  local deadline_s="${3:-60}"
  local start
  start="$(date +%s)"
  while true; do
    if curl -fsS --max-time 2 "${url}" >/dev/null 2>&1; then
      return 0
    fi
    if [[ "$(date +%s)" -ge "$((start + deadline_s))" ]]; then
      echo "Timed out waiting for ${name} at ${url}" >&2
      echo "--- backend log (${BACKEND_LOG}) ---" >&2
      tail -n 200 "${BACKEND_LOG}" >&2 || true
      echo "--- frontend log (${FRONTEND_LOG}) ---" >&2
      tail -n 200 "${FRONTEND_LOG}" >&2 || true
      return 1
    fi
    sleep 0.2
  done
}

wait_http "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" "backend" 60
wait_http "http://127.0.0.1:${FRONTEND_PORT}/" "frontend" 60

# Keep running for Playwright; child processes are cleaned up via trap.
wait
