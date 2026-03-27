<#
.SYNOPSIS
    One-click launcher for Tank World: starts the backend, frontend, and opens a browser.
.DESCRIPTION
    Runs the FastAPI simulation backend and the Vite React frontend in
    separate background jobs, then opens http://localhost:3000 in your
    default browser.  Press Ctrl+C to stop everything.
#>

$ErrorActionPreference = "Stop"

# Ensure UTF-8 output for emojis and box drawing characters
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ── paths ──────────────────────────────────────────────────────────
$root     = $PSScriptRoot
$venvAct  = Join-Path $root ".venv\Scripts\Activate.ps1"
$frontend = Join-Path $root "frontend"

# ── pre-flight checks ─────────────────────────────────────────────
if (-not (Test-Path $venvAct)) {
    Write-Host "❌  No .venv found. Run these first:" -ForegroundColor Red
    Write-Host "      python -m venv .venv"
    Write-Host "      .\.venv\Scripts\Activate.ps1"
    Write-Host "      pip install -e .[dev]"
    exit 1
}
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "❌  No node_modules found. Run:" -ForegroundColor Red
    Write-Host "      cd frontend && npm install"
    exit 1
}

# ── start backend (FastAPI + simulation) ───────────────────────────
Write-Host "🐟  Starting backend server..." -ForegroundColor Cyan
$backend_job = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "& '$venvAct'; python '$root\main.py'"
) -PassThru

# ── start frontend (Vite dev server) ──────────────────────────────
Write-Host "⚛️   Starting frontend dev server..." -ForegroundColor Cyan
$frontend_job = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$frontend'; npm run dev"
) -PassThru

# ── open browser after a short delay ──────────────────────────────
Write-Host "🌐  Opening browser in 5 seconds..." -ForegroundColor Green
Start-Sleep -Seconds 5
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Tank World is running!" -ForegroundColor Yellow
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor Yellow
Write-Host "  Backend:   http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Enter to stop both servers..." -ForegroundColor DarkGray
Read-Host

# ── cleanup ────────────────────────────────────────────────────────
Write-Host "🛑  Shutting down..." -ForegroundColor Red
if (!$backend_job.HasExited)  { Stop-Process -Id $backend_job.Id  -Force -ErrorAction SilentlyContinue }
if (!$frontend_job.HasExited) { Stop-Process -Id $frontend_job.Id -Force -ErrorAction SilentlyContinue }
Write-Host "Done." -ForegroundColor Green
