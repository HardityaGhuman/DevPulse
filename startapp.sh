#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "Stopping DevPulse..."

  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting DevPulse backend on http://localhost:8000"
(
  cd "$BACKEND_DIR"
  if [[ -d "venv" ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
  fi
  uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

echo "Starting DevPulse frontend on http://localhost:5173"
(
  cd "$FRONTEND_DIR"
  npm run dev -- --host 0.0.0.0
) &
FRONTEND_PID=$!

echo
echo "DevPulse is starting:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo
echo "Press Ctrl+C to stop both servers."

wait "$BACKEND_PID" "$FRONTEND_PID"
