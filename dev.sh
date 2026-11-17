#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "[dev] starting backend on http://localhost:8000 ..."
(cd "$ROOT/backend" && uv run uvicorn s4web.presentation.app:app --reload --port 8000) &
BACKEND_PID=$!

echo "[dev] starting frontend on http://localhost:3000 ..."
(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

trap 'echo; echo "[dev] stopping..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT INT TERM

echo "[dev] ready. open http://localhost:3000  (Ctrl+C to stop both)"
wait
