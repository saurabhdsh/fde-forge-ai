#!/usr/bin/env bash
# Stop native (non-Docker) FDE Forge AI processes
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT/.run/pids"

stop_pidfile() {
  local name="$1"
  local file="$PID_DIR/$name.pid"
  if [[ -f "$file" ]]; then
    local pid
    pid="$(cat "$file")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping $name (pid $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$file"
  fi
}

stop_pidfile api
stop_pidfile worker
stop_pidfile web
stop_pidfile minio
stop_pidfile redis

pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "celery -A app.worker.celery_app" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true

echo "Native processes stopped."
echo "Docker users: docker compose down"
