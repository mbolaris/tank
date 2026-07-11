#!/usr/bin/env python3
"""Run the under-30-second contributor smoke gate."""

import importlib.util
import sys
from pathlib import Path

try:
    from tools.gate_common import exit_for_gate, print_gate_header, python_command, run_steps
except ImportError:
    from gate_common import (  # type: ignore[import-not-found,no-redef]
        exit_for_gate,
        print_gate_header,
        python_command,
        run_steps,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DEV_MODULES = ("pytest", "ruff", "black")


def missing_dev_tools() -> list[str]:
    """Return required smoke-gate modules that are unavailable."""
    return [name for name in REQUIRED_DEV_MODULES if importlib.util.find_spec(name) is None]


def _print_missing_tools(missing: list[str]) -> None:
    print("[FAIL] Smoke gate cannot start; missing development tools: " + ", ".join(missing))
    print(
        "Install them from the repository root with:\n"
        f'  "{sys.executable}" -m pip install -e "{REPO_ROOT}[dev]"'
    )


def main() -> None:
    missing = missing_dev_tools()
    if missing:
        _print_missing_tools(missing)
        exit_for_gate("SMOKE", False)

    print_gate_header(
        name="SMOKE",
        target="under 30 seconds",
        includes="quick formatting/lint checks and a curated correctness suite",
        excludes="the broad non-slow suite, integration/manual/slow tests, and 5k/10k benchmarks",
    )
    steps = [
        (
            python_command(
                "-m", "ruff", "check", "core", "tests", "tools", "backend", "benchmarks", "main.py"
            ),
            "Ruff lint",
        ),
        (
            python_command(
                "-m",
                "black",
                "--check",
                # Single worker: Black's process pool can crash in sandboxed
                # agent environments, and the gate must never fail for
                # reasons unrelated to the code being checked.
                "-W",
                "1",
                "core",
                "tests",
                "tools",
                "backend",
                "benchmarks",
                "main.py",
            ),
            "Black formatting",
        ),
        (
            python_command(
                "-m",
                "pytest",
                "tests/smoke",
                "tests/test_ai_code_evolution_agent.py",
                "tests/test_run_bench.py",
                "tests/test_state_publisher_delta_sparsity.py",
                "tests/test_fingerprint_stream.py",
                "tests/test_benchmark_determinism.py",
                "tests/test_champion_provenance.py",
                "tests/test_validation_tiers.py",
                "tests/test_docs_agent_onboarding.py",
                "-q",
            ),
            "Curated smoke correctness suite",
        ),
    ]
    exit_for_gate("SMOKE", run_steps(steps))


if __name__ == "__main__":
    main()
