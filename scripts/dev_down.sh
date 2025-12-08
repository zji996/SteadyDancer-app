#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[dev_down] Stopping SteadyDancer dev processes..."

# Stop API (match the uvicorn dev command used in scripts/dev_api.sh)
pkill -f "uv run --project apps/api uvicorn apps.api.main:app --reload" 2>/dev/null || true

# Stop Worker (match the Celery command used in scripts/dev_worker.sh)
pkill -f "uv run --project apps/worker celery -A apps.worker.celery_app worker -l info" 2>/dev/null || true

# Stop Web (match the Vite dev command used in scripts/dev_web.sh)
pkill -f "pnpm --filter @steadydancer/web run dev" 2>/dev/null || true

echo "[dev_down] Stopping local dependencies (docker-compose.dev.yml)..."
docker compose -f "${ROOT_DIR}/infra/docker-compose.dev.yml" down || true

echo "[dev_down] All dev services stopped."
