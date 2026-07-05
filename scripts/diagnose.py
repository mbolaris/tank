#!/usr/bin/env python3
"""Diagnose whether a checkout is ready to run Tank World.

This is a setup-oriented health check, not a validation gate. It keeps checks
independent so a missing developer tool does not hide whether the simulation
itself can import and run.
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    remedy: str | None = None


Check = Callable[[], CheckResult]
CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _run_command(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        check=False,
    )


def _module_import_check(module_name: str) -> Check:
    def check() -> CheckResult:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            return CheckResult(
                f"Import {module_name}",
                False,
                f"{type(exc).__name__}: {exc}",
                "Install Python dependencies with `pip install -e .[dev]`.",
            )
        return CheckResult(f"Import {module_name}", True, "import succeeded")

    return check


def _dev_tool_check(module_name: str, *, runner: CommandRunner = _run_command) -> Check:
    def check() -> CheckResult:
        try:
            result = runner([sys.executable, "-m", module_name, "--version"])
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CheckResult(
                f"{module_name} resolves",
                False,
                f"{type(exc).__name__}: {exc}",
                "Install developer dependencies with `pip install -e .[dev]`.",
            )

        output = (result.stdout or "").strip().splitlines()
        detail = output[0] if output else f"exit code {result.returncode}"
        if result.returncode != 0:
            return CheckResult(
                f"{module_name} resolves",
                False,
                detail,
                "Install developer dependencies with `pip install -e .[dev]`.",
            )
        return CheckResult(f"{module_name} resolves", True, detail)

    return check


def _headless_smoke_check(*, runner: CommandRunner = _run_command) -> CheckResult:
    command = [
        sys.executable,
        "main.py",
        "--headless",
        "--max-frames",
        "100",
        "--seed",
        "42",
    ]
    try:
        result = runner(command)
    except subprocess.TimeoutExpired as exc:
        return CheckResult(
            "100-frame headless sim",
            False,
            f"timed out after {exc.timeout}s",
            "Run the command directly to inspect the full output.",
        )
    except OSError as exc:
        return CheckResult(
            "100-frame headless sim",
            False,
            f"{type(exc).__name__}: {exc}",
            "Confirm the Python interpreter can launch subprocesses.",
        )

    if result.returncode != 0:
        lines = [line for line in (result.stdout or "").splitlines() if line.strip()]
        detail = lines[-1] if lines else f"exit code {result.returncode}"
        return CheckResult(
            "100-frame headless sim",
            False,
            detail,
            "Run `python main.py --headless --max-frames 100 --seed 42` for details.",
        )
    return CheckResult("100-frame headless sim", True, "ran 100 frames with seed 42")


def _frontend_deps_check() -> CheckResult:
    node_modules = REPO_ROOT / "frontend" / "node_modules"
    if node_modules.exists():
        return CheckResult("Frontend dependencies", True, "frontend/node_modules exists")
    return CheckResult(
        "Frontend dependencies",
        False,
        "frontend/node_modules is missing",
        "Run `cd frontend && npm install`.",
    )


def build_checks() -> list[Check]:
    return [
        _module_import_check("core"),
        _module_import_check("backend"),
        _module_import_check("numpy"),
        _module_import_check("fastapi"),
        _module_import_check("core.simulation.engine"),
        _headless_smoke_check,
        _dev_tool_check("black"),
        _dev_tool_check("ruff"),
        _dev_tool_check("mypy"),
        _frontend_deps_check,
    ]


def run_checks(checks: Sequence[Check]) -> list[CheckResult]:
    return [check() for check in checks]


def print_results(results: Sequence[CheckResult]) -> None:
    print("Tank World checkout diagnosis")
    print("=" * 34)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
        if not result.passed and result.remedy:
            print(f"       Remedy: {result.remedy}")

    passed = sum(1 for result in results if result.passed)
    print(f"\nSummary: {passed}/{len(results)} checks passed.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print a setup health checklist for the Tank World checkout."
    )
    parser.parse_args(argv)

    results = run_checks(build_checks())
    print_results(results)
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
