# PowerShell script to restart servers
Write-Host "Stopping any running servers..." -ForegroundColor Yellow

# Kill backend processes
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*backend*main.py*"} | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill frontend processes
Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*npm*dev*"} | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Waiting for processes to stop..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Starting backend server..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python main.py"

Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Starting frontend server..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Servers are starting!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: Check the frontend window for the port" -ForegroundColor White
Write-Host "(Usually http://localhost:5173)" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
