#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[dev_up] Starting local dependencies via docker-compose.dev.yml..."
docker compose -f "${ROOT_DIR}/infra/docker-compose.dev.yml" up -d

echo "[dev_up] Local services are up."
