"""Run backend and capture all output to a log file."""
import subprocess
import sys
import os

# Get paths
tank_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(tank_dir, "backend")
log_file = os.path.join(tank_dir, "backend.log")

print("=" * 50)
print("Starting backend with logging...")
print(f"Log file: {log_file}")
print("=" * 50)

# Stop existing
subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True, check=False)
import time
time.sleep(2)

# Start backend with logging
with open(log_file, 'w') as log:
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=backend_dir,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(f"Backend started (PID: {process.pid})")
    print(f"Tailing log file... (Ctrl+C to stop)")
    print("=" * 50)

    # Tail the log file
    import time
    log_path = log_file

    # Wait a bit for initial output
    time.sleep(3)

    # Now read and display
    with open(log_path, 'r') as f:
        while True:
            line = f.readline()
            if line:
                print(line, end='')
            else:
                time.sleep(0.1)
