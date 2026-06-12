"""Shared helpers for named validation gates."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def print_gate_header(name: str, target: str, includes: str, excludes: str) -> None:
    print("=" * 72, flush=True)
    print(f"Tank World validation tier: {name}", flush=True)
    print(f"Target runtime: {target}", flush=True)
    print(f"Includes: {includes}", flush=True)
    print(f"Excludes: {excludes}", flush=True)
    print("=" * 72, flush=True)


def run_steps(steps: Sequence[tuple[list[str], str]]) -> bool:
    for args, name in steps:
        print(f"\n=== {name} ===", flush=True)
        result = subprocess.run(args, cwd=str(REPO_ROOT))
        if result.returncode != 0:
            print(f"[FAIL] {name} failed with exit code {result.returncode}", flush=True)
            return False
        print(f"[PASS] {name}", flush=True)
    return True


def exit_for_gate(name: str, passed: bool) -> None:
    if passed:
        print(f"\n[PASS] {name} gate passed.", flush=True)
        raise SystemExit(0)
    print(f"\n[FAIL] {name} gate failed.", flush=True)
    raise SystemExit(1)


def python_command(*args: str) -> list[str]:
    return [sys.executable, *args]
