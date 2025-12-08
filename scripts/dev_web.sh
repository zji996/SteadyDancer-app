#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# Load root .env if exists
export $(grep -v '^#' .env 2>/dev/null | xargs -r) || true
# Load apps/web/.env if exists
export $(grep -v '^#' apps/web/.env 2>/dev/null | xargs -r) || true

echo "[dev_web] Starting SteadyDancer Web (Vite dev server)..."
pnpm --filter @steadydancer/web run dev
