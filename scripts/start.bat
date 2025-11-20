@echo off
echo Stopping existing servers...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 >nul

echo Starting backend...
cd ..\backend
start "Tank Backend" cmd /k python main.py

timeout /t 3 >nul

echo Starting frontend...
cd ..\frontend
start "Tank Frontend" cmd /k npm run dev

echo.
echo ========================================
echo Servers are starting!
echo ========================================
echo Backend: http://localhost:8000
echo Frontend: Check the frontend window
echo.
echo Backend and frontend windows will show logs.
echo Close those windows to stop the servers.
echo ========================================
