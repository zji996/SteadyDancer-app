#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

export $(grep -v '^#' .env 2>/dev/null | xargs -r) || true
export $(grep -v '^#' apps/worker/.env 2>/dev/null | xargs -r) || true

echo "[dev_worker] Starting SteadyDancer Celery worker..."
uv run --project apps/worker celery -A apps.worker.celery_app worker -l info

