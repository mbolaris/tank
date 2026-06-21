#!/usr/bin/env python3
"""Run the under-30-second contributor smoke gate."""

try:
    from tools.gate_common import exit_for_gate, print_gate_header, python_command, run_steps
except ImportError:
    from gate_common import exit_for_gate, print_gate_header, python_command, run_steps  # type: ignore[import-not-found,no-redef]


def main() -> None:
    print_gate_header(
        name="SMOKE",
        target="under 30 seconds",
        includes="quick formatting/lint checks and a curated correctness suite",
        excludes="the broad non-slow suite, integration/manual/slow tests, and 5k/10k benchmarks",
    )
    steps = [
        (
            python_command("-m", "ruff", "check", "core", "tests", "tools", "backend", "main.py"),
            "Ruff lint",
        ),
        (
            python_command(
                "-m",
                "black",
                "--check",
                "core",
                "tests",
                "tools",
                "backend",
                "main.py",
            ),
            "Black formatting",
        ),
        (
            python_command(
                "-m",
                "pytest",
                "tests/smoke",
                "tests/test_run_bench.py",
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
