#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[dev_down] Stopping local dependencies..."
docker compose -f "${ROOT_DIR}/infra/docker-compose.dev.yml" down

echo "[dev_down] Local services stopped."

