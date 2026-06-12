#!/usr/bin/env python3
"""Tank World Fast Gate.

Runs ruff, black, and fast/focused unit and contract tests.
Does not run slow benchmarks.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_command(args, cwd=REPO_ROOT, name=""):
    print(f"=== Running {name or ' '.join(args)} ===")
    result = subprocess.run(args, cwd=str(cwd))
    if result.returncode != 0:
        print(f"[FAIL] {name or 'Command'} failed with exit code {result.returncode}")
        return False
    print(f"[PASS] {name or 'Command'} passed.\n")
    return True


def main():
    python_exe = sys.executable

    steps = [
        ([python_exe, "-m", "ruff", "check", "."], "Ruff Linter"),
        (
            [
                python_exe,
                "-m",
                "black",
                "--check",
                "core",
                "tests",
                "tools",
                "backend",
                "main.py",
            ],
            "Black Formatter Check",
        ),
        (
            [
                python_exe,
                "-m",
                "pytest",
                "tests/test_fingerprint_stream.py",
                "tests/test_benchmark_determinism.py",
                "tests/test_run_bench.py",
                "-q",
            ],
            "Focused Determinism & Contract Tests",
        ),
        (
            [python_exe, "-m", "pytest", "-m", "not slow and not integration", "-q"],
            "General Unit Tests",
        ),
    ]

    for args, name in steps:
        if not run_command(args, name=name):
            print("[FAIL] Fast gate FAILED!")
            sys.exit(1)

    print("Success: All fast gate checks PASSED!")
    sys.exit(0)


if __name__ == "__main__":
    main()
