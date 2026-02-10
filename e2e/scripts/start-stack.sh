#!/usr/bin/env bash
set -euo pipefail

# Starts:
#  - backend (mock mode) on :5090
#  - frontend (static) on :5180
#
# This script is meant to be launched by Playwright's webServer and kept running.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="/home/robot/workspace/shenlab/17-lab-web"

export SHENLAB_MOCK=1
export SHENLAB_DATA_DIR="${SHENLAB_DATA_DIR:-$(mktemp -d)}"

BACKEND_LOG="${SHENLAB_DATA_DIR}/backend.log"
FRONTEND_LOG="${SHENLAB_DATA_DIR}/frontend.log"

cleanup() {
  set +e
  [[ -n "${BACK_PID:-}" ]] && kill "${BACK_PID}" 2>/dev/null || true
  [[ -n "${FRONT_PID:-}" ]] && kill "${FRONT_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"

uvicorn shenlab_services.api:create_app --factory --host 127.0.0.1 --port 5090 >"${BACKEND_LOG}" 2>&1 &
BACK_PID=$!

python -m http.server 5180 --bind 127.0.0.1 --directory "${FRONTEND_DIR}" >"${FRONTEND_LOG}" 2>&1 &
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

wait_http "http://127.0.0.1:5090/api/v1/health" "backend" 60
wait_http "http://127.0.0.1:5180/" "frontend" 60

# Keep running for Playwright; child processes are cleaned up via trap.
wait
