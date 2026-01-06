@echo off
echo Killing process on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    echo Killing PID: %%a
    taskkill /F /PID %%a
)
echo Done.
