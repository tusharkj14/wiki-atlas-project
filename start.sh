#!/usr/bin/env bash
set -e

# ── Ensure Docker daemon is running ────────────────────────────────
if ! docker info >/dev/null 2>&1; then
    echo "==> Docker not running, launching Docker Desktop..."
    "/c/Program Files/Docker/Docker/Docker Desktop.exe" &
    for i in $(seq 1 30); do
        docker info >/dev/null 2>&1 && break
        echo "    waiting for Docker daemon... ($i)"
        sleep 2
    done
    docker info >/dev/null 2>&1 || { echo "ERROR: Docker failed to start"; exit 1; }
fi
echo "==> Docker is running"

# ── Start Redis & PostgreSQL ───────────────────────────────────────
echo "==> Starting Redis & PostgreSQL (Docker Compose)..."
docker compose up -d --wait

echo "==> Services ready"
docker compose ps

# ── Start FastAPI server ───────────────────────────────────────────
echo ""
echo "==> Starting FastAPI server on http://127.0.0.1:8000"
uv run python main.py
