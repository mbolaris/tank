#!/usr/bin/env python3
"""One-command launcher for Tank World.

Starts the FastAPI backend (:8000) and the Vite React frontend (:3000)
together, streams their logs with colored prefixes, and shuts both down
cleanly on Ctrl-C. Cross-platform replacement for juggling two terminals.

Usage:
    python start.py                 # backend + frontend, opens the browser
    python start.py --no-browser    # don't open a browser tab
    python start.py --backend-only  # run only the backend (no Node required)

Run `python scripts/diagnose.py` first if anything fails to start.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def _info(msg: str) -> None:
    print(_c("36", "[start] ") + msg, flush=True)


def _error(msg: str) -> None:
    print(_c("31", "[start] " + msg), file=sys.stderr, flush=True)


def _stream(proc: subprocess.Popen, label: str, color: str) -> None:
    """Forward a child's combined output to our stdout with a colored prefix."""
    prefix = _c(color, f"[{label}] ")
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(prefix + line)
        sys.stdout.flush()


def _popen(cmd: list[str], cwd: Path) -> subprocess.Popen:
    """Start a child process in its own group so we can stop the whole tree."""
    kwargs: dict = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "bufsize": 1,
        "text": True,
    }
    if os.name == "posix":
        kwargs["start_new_session"] = True
    else:  # Windows: allow sending CTRL_BREAK to the group
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    return subprocess.Popen(cmd, **kwargs)


def _terminate(proc: subprocess.Popen, label: str) -> None:
    if proc.poll() is not None:
        return
    _info(f"stopping {label}...")
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
    except (ProcessLookupError, PermissionError, OSError):
        proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        _info(f"force-killing {label}")
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError:
                proc.kill()
        else:
            proc.kill()


def _preflight(backend_only: bool) -> bool:
    if backend_only:
        return True
    if not (FRONTEND_DIR / "node_modules").is_dir():
        _error("frontend/node_modules is missing. Install it with:")
        _error("    cd frontend && npm install")
        _error("Or run backend only:  python start.py --backend-only")
        return False
    if shutil.which("npm") is None:
        _error("npm is not on PATH. Install Node 20+, or run: python start.py --backend-only")
        return False
    return True


def _open_browser_later(url: str, delay: float = 3.0) -> None:
    def _open() -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Tank World (backend + frontend)")
    parser.add_argument(
        "--backend-only", action="store_true", help="Run only the backend (no Node required)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open a browser tab on startup"
    )
    args = parser.parse_args()

    if not _preflight(args.backend_only):
        return 1

    processes: list[tuple[subprocess.Popen, str]] = []
    threads: list[threading.Thread] = []

    _info("starting backend on " + BACKEND_URL)
    backend = _popen([sys.executable, str(REPO_ROOT / "main.py")], cwd=REPO_ROOT)
    processes.append((backend, "backend"))
    t = threading.Thread(target=_stream, args=(backend, "backend", "32"), daemon=True)
    t.start()
    threads.append(t)

    if not args.backend_only:
        _info("starting frontend on " + FRONTEND_URL)
        npm = shutil.which("npm") or "npm"
        frontend = _popen([npm, "run", "dev"], cwd=FRONTEND_DIR)
        processes.append((frontend, "frontend"))
        t = threading.Thread(target=_stream, args=(frontend, "frontend", "35"), daemon=True)
        t.start()
        threads.append(t)

    target_url = BACKEND_URL if args.backend_only else FRONTEND_URL
    if not args.no_browser:
        _open_browser_later(target_url)

    _info(f"open {target_url} — press Ctrl+C to stop")

    exit_code = 0
    try:
        # Wait until any child exits (which usually signals a crash), or Ctrl-C.
        while True:
            for proc, label in processes:
                code = proc.poll()
                if code is not None:
                    _error(f"{label} exited with code {code}; shutting down")
                    exit_code = code or 1
                    raise KeyboardInterrupt
            time.sleep(0.4)
    except KeyboardInterrupt:
        print()
        _info("shutdown requested")
    finally:
        for proc, label in reversed(processes):
            _terminate(proc, label)

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
