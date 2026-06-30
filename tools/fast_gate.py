#!/usr/bin/env python3
"""Run the contributor pre-PR fast gate."""

try:
    from tools.gate_common import exit_for_gate, print_gate_header, python_command, run_steps
except ImportError:
    from gate_common import exit_for_gate, print_gate_header, python_command, run_steps  # type: ignore[import-not-found,no-redef]


def main() -> None:
    print_gate_header(
        name="FAST",
        target="under 2-3 minutes on normal developer/CI hardware (parallelized across cores)",
        includes="the smoke gate, then the broad non-slow test suite run in parallel",
        excludes="integration/manual/slow tests, champion reproduction, and 5k/10k benchmarks",
    )
    steps = [
        (python_command("tools/smoke_gate.py"), "Tier 1: smoke gate"),
        (
            python_command(
                "-m",
                "pytest",
                "tests",
                "-m",
                "not slow and not integration and not manual",
                "-n",
                "auto",
                "-q",
                "--durations=25",
            ),
            "Tier 2: broad non-slow tests (parallel)",
        ),
    ]
    exit_for_gate("FAST", run_steps(steps))


if __name__ == "__main__":
    main()
