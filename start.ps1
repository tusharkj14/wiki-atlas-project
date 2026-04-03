# ── Ensure Docker daemon is running ────────────────────────────────
docker info *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "==> Docker not running, launching Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 2
        docker info *>$null
        if ($LASTEXITCODE -eq 0) { break }
        Write-Host "    waiting for Docker daemon... ($i)"
    }
    docker info *>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker failed to start" -ForegroundColor Red
        exit 1
    }
}
Write-Host "==> Docker is running" -ForegroundColor Green

# ── Start Redis & PostgreSQL ───────────────────────────────────────
Write-Host "==> Starting Redis & PostgreSQL (Docker Compose)..."
docker compose up -d --wait
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "==> Services ready" -ForegroundColor Green
docker compose ps

# ── Start FastAPI server ───────────────────────────────────────────
Write-Host ""
Write-Host "==> Starting FastAPI server on http://127.0.0.1:8000" -ForegroundColor Green
uv run python main.py
