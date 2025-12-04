#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

export $(grep -v '^#' .env 2>/dev/null | xargs -r) || true
export $(grep -v '^#' apps/api/.env 2>/dev/null | xargs -r) || true

echo "[dev_api] Starting SteadyDancer API..."
uv run --project apps/api uvicorn apps.api.main:app --reload

