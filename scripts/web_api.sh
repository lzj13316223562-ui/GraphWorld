#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${GRAPHWORLD_API_PORT:-8010}"

export GRAPHWORLD_DATABASE_URL="${GRAPHWORLD_DATABASE_URL:-postgresql+psycopg://graphworld:graphworld@127.0.0.1:55432/graphworld}"
export GRAPHWORLD_REDIS_URL="${GRAPHWORLD_REDIS_URL:-redis://127.0.0.1:56379/0}"

cd "$ROOT_DIR"
exec .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port "$PORT"
