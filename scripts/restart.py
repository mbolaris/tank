"""Simple script to restart the backend and frontend servers."""
import subprocess
import sys
import time
import os

print("=" * 50)
print("Fish Tank Simulation - Server Restart")
print("=" * 50)
print()

# Kill existing processes
print("Stopping existing servers...")
try:
    subprocess.run(["taskkill", "/F", "/IM", "python.exe"],
                   capture_output=True, check=False)
    subprocess.run(["taskkill", "/F", "/IM", "node.exe"],
                   capture_output=True, check=False)
    time.sleep(2)
    print("[OK] Stopped existing processes")
except Exception as e:
    print(f"[WARN] Warning stopping processes: {e}")

print()

# Get the tank directory
tank_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(tank_dir, "backend")
frontend_dir = os.path.join(tank_dir, "frontend")

# Start backend
print("Starting backend server...")
try:
    backend_process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=backend_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print(f"[OK] Backend started (PID: {backend_process.pid})")
except Exception as e:
    print(f"[ERROR] Failed to start backend: {e}")
    sys.exit(1)

# Wait for backend to initialize
print("Waiting for backend to initialize...")
time.sleep(3)

# Start frontend
print("Starting frontend server...")
try:
    frontend_process = subprocess.Popen(
        ["npm.cmd", "run", "dev"],
        cwd=frontend_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print(f"[OK] Frontend started (PID: {frontend_process.pid})")
except Exception as e:
    print(f"[ERROR] Failed to start frontend: {e}")
    sys.exit(1)

print()
print("=" * 50)
print("Servers started successfully!")
print("=" * 50)
print("Backend:  http://localhost:8000")
print("Frontend: Check the frontend console window")
print("          (Usually http://localhost:3000 or :5173)")
print()
print("Separate console windows have been opened for")
print("backend and frontend. Check them for logs.")
print()
print("To stop servers: Close the console windows or")
print("                 run this script again.")
print("=" * 50)
