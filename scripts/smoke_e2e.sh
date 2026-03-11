#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[smoke] starting backend"
uv run python -m sentinel.main >/tmp/sentinel-smoke.log 2>&1 &
BACKEND_PID=$!

for _ in {1..40}; do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

curl -fsS http://127.0.0.1:8000/api/health >/dev/null
curl -fsS http://127.0.0.1:8000/api/dashboard/state >/dev/null
curl -fsS "http://127.0.0.1:8000/api/map/layers?layers=conflicts,natural,news&hours_back=24" >/dev/null
curl -fsS "http://127.0.0.1:8000/api/brief/history?limit=3" >/dev/null
curl -fsS "http://127.0.0.1:8000/api/infrastructure" >/dev/null
curl -fsS "http://127.0.0.1:8000/api/gdelt?query=Red%20Sea&mode=artlist&max_results=3" >/dev/null

echo "[smoke] frontend install"
npm --prefix frontend install >/tmp/frontend-install.log 2>&1

echo "[smoke] frontend build"
npm --prefix frontend run build >/tmp/frontend-smoke.log 2>&1

echo "[smoke] success"
