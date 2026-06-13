#!/usr/bin/env python3
"""One-command startup script for Tank World.

Launches the FastAPI backend and Vite React frontend in parallel,
monitors their execution, and opens the app in the default browser.
"""

import os
import sys
import socket
import time
import signal
import subprocess
import threading
import webbrowser

# Enable ANSI escape sequences on Windows Command Prompt
if os.name == "nt":
    os.system("")

# Terminal Styling Colors
CYAN = "\033[36m"
MAGENTA = "\033[35m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_banner():
    """Print the startup banner."""
    width = 60
    print(f"{CYAN}╔{═ * (width - 2)}╗{RESET}")
    print(f"{CYAN}║{BOLD}{' TANK WORLD DEVELOPMENT RUNNER ':^58}{RESET}{CYAN}║{RESET}")
    print(f"{CYAN}╠{═ * (width - 2)}╣{RESET}")
    print(f"{CYAN}║{GRAY}{'Starting FastAPI backend & Vite React frontend...':^58}{RESET}{CYAN}║{RESET}")
    print(f"{CYAN}║{GRAY}{'Press Ctrl+C to terminate both servers cleanly.':^58}{RESET}{CYAN}║{RESET}")
    print(f"{CYAN}╚{═ * (width - 2)}╝{RESET}")
    print()


def get_python_executable():
    """Locate the Python executable in the virtual environment if possible."""
    venv_dir = os.path.join(os.getcwd(), ".venv")
    if sys.platform == "win32":
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")

    if os.path.exists(python_exe):
        return python_exe

    # Fall back to active interpreter
    return sys.executable


def run_preflight_checks(python_exe):
    """Ensure dependencies and frontend node_modules are ready."""
    print(f"{GRAY}[System]{RESET} Python interpreter: {python_exe}")

    # 1. Check if backend dependencies are installed
    try:
        subprocess.run(
            [python_exe, "-c", "import fastapi, uvicorn"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(
            f"{RED}❌ Error: FastAPI/Uvicorn not found in Python environment ({python_exe}).{RESET}"
        )
        print("Please set up the virtual environment first:")
        print(f"  {YELLOW}python -m venv .venv{RESET}")
        if sys.platform == "win32":
            print(f"  {YELLOW}.venv\\Scripts\\activate{RESET}")
        else:
            print(f"  {YELLOW}source .venv/bin/activate{RESET}")
        print(f"  {YELLOW}pip install -e .[dev]{RESET}")
        sys.exit(1)

    # 2. Check if frontend node_modules exist, auto-install if missing
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    node_modules_dir = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules_dir):
        print(
            f"{YELLOW}⚠️  node_modules not found in frontend/. Running 'npm install'...{RESET}"
        )
        try:
            use_shell = sys.platform == "win32"
            subprocess.run(
                ["npm", "install"], cwd=frontend_dir, shell=use_shell, check=True
            )
            print(f"{GREEN}✓ npm install completed successfully.{RESET}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(
                f"{RED}❌ Error: Failed to run 'npm install'. Please ensure Node.js/npm is installed and run it manually in frontend/.{RESET}"
            )
            sys.exit(1)


def stream_output(proc, prefix, color):
    """Stream stdout/stderr from a process with a colored tag prefix."""
    try:
        for line in iter(proc.stdout.readline, b""):
            decoded = line.decode("utf-8", errors="replace").rstrip()
            print(f"{color}{prefix}{RESET} {decoded}")
    except Exception as e:
        print(f"{RED}[Error]{RESET} Failed to read output from {prefix}: {e}")


def wait_for_port(port, timeout=15.0):
    """Wait until a local port is accepting socket connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1.0):
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
    return False


def kill_process(proc):
    """Forcefully kill a process and all of its subprocesses (process tree)."""
    if proc is None:
        return
    try:
        if sys.platform == "win32":
            # On Windows, taskkill /F /T kills the entire process tree recursively
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
            )
        else:
            # On Unix, kill the entire process group
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main():
    print_banner()

    python_exe = get_python_executable()
    run_preflight_checks(python_exe)

    frontend_dir = os.path.join(os.getcwd(), "frontend")
    use_shell = sys.platform == "win32"

    # Start new process groups to handle clean SIGKILL of descendant processes
    popen_kwargs = {}
    if sys.platform != "win32":
        popen_kwargs["start_new_session"] = True

    print(f"{GREEN}🚀 Starting servers...{RESET}")

    # Start backend server
    backend_proc = subprocess.Popen(
        [python_exe, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **popen_kwargs,
    )

    # Start frontend dev server
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=use_shell,
        **popen_kwargs,
    )

    # Start output log streaming threads
    backend_thread = threading.Thread(
        target=stream_output,
        args=(backend_proc, "[Backend]", CYAN),
        daemon=True,
    )
    frontend_thread = threading.Thread(
        target=stream_output,
        args=(frontend_proc, "[Frontend]", MAGENTA),
        daemon=True,
    )

    backend_thread.start()
    frontend_thread.start()

    # Wait for the frontend port (3000) to start accepting connections
    print(f"{GRAY}[System]{RESET} Waiting for Vite dev server on port 3000...")
    if wait_for_port(3000):
        print(f"{GREEN}✓ Port 3000 is open! Launching default browser...{RESET}")
        webbrowser.open("http://localhost:3000")
    else:
        print(f"{YELLOW}⚠️  Port 3000 did not open within timeout. Check console logs above.{RESET}")

    # Main monitoring loop
    try:
        while True:
            # If either process died, abort
            backend_exit = backend_proc.poll()
            if backend_exit is not None:
                print(f"\n{RED}❌ Backend server exited unexpectedly with code {backend_exit}{RESET}")
                break

            frontend_exit = frontend_proc.poll()
            if frontend_exit is not None:
                print(f"\n{RED}❌ Frontend server exited unexpectedly with code {frontend_exit}{RESET}")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}🛑 Received shutdown signal. Terminating servers...{RESET}")
    finally:
        kill_process(backend_proc)
        kill_process(frontend_proc)
        print(f"{GREEN}✓ Shutdown complete. Both servers stopped.{RESET}")


if __name__ == "__main__":
    main()
