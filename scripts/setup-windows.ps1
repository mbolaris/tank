# Tank World - Windows Setup Script
# This script sets up the Python environment and installs dependencies

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Tank World - Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in a virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment detected: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "WARNING: No virtual environment detected!" -ForegroundColor Yellow
    Write-Host "It's recommended to use a virtual environment." -ForegroundColor Yellow
    Write-Host "Activate your .venv with:" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host ""

    $response = Read-Host "Continue anyway? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Setup cancelled." -ForegroundColor Red
        exit 1
    }
}

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Cyan
$pythonVersion = python --version 2>&1
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install the package in development mode
Write-Host ""
Write-Host "Installing Tank World and dependencies..." -ForegroundColor Cyan
python -m pip install -e .

# Install development dependencies (optional)
Write-Host ""
$installDev = Read-Host "Install development dependencies (pytest, mypy, black, ruff)? (Y/n)"
if ($installDev -ne 'n' -and $installDev -ne 'N') {
    Write-Host "Installing development dependencies..." -ForegroundColor Cyan
    python -m pip install -e ".[dev]"
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "To run the web server:" -ForegroundColor Cyan
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "To run in headless mode:" -ForegroundColor Cyan
Write-Host "  python main.py --headless --max-frames 1000" -ForegroundColor White
Write-Host ""
