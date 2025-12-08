#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/log"

cd "${ROOT_DIR}"

echo "[dev_up] Stopping existing SteadyDancer dev services (if any)..."
bash "${ROOT_DIR}/scripts/dev_down.sh" || true

echo "[dev_up] Preparing log directory at ${LOG_DIR}..."
mkdir -p "${LOG_DIR}"
rm -f "${LOG_DIR}"/*.log 2>/dev/null || true

echo "[dev_up] Starting local dependencies via infra/docker-compose.dev.yml..."
docker compose -f "${ROOT_DIR}/infra/docker-compose.dev.yml" up -d

echo "[dev_up] Starting SteadyDancer API (logs -> log/api.log)..."
bash "${ROOT_DIR}/scripts/dev_api.sh" >"${LOG_DIR}/api.log" 2>&1 &

echo "[dev_up] Starting SteadyDancer Worker (logs -> log/worker.log)..."
bash "${ROOT_DIR}/scripts/dev_worker.sh" >"${LOG_DIR}/worker.log" 2>&1 &

echo "[dev_up] Starting SteadyDancer Web (logs -> log/web.log)..."
bash "${ROOT_DIR}/scripts/dev_web.sh" >"${LOG_DIR}/web.log" 2>&1 &

echo "[dev_up] All dev services started."
echo "[dev_up] Tail logs with: tail -f log/api.log log/worker.log log/web.log"
