#!/usr/bin/env python3
"""Run the contributor pre-PR validation gate."""

try:
    from tools.gate_common import (
        exit_for_gate,
        print_gate_header,
        python_command,
        run_pytest_with_diagnostics,
        run_steps,
    )
except ImportError:
    from gate_common import (  # type: ignore[import-not-found,no-redef]
        exit_for_gate,
        print_gate_header,
        python_command,
        run_pytest_with_diagnostics,
        run_steps,
    )

_MARKER_EXPR = "not slow and not integration and not manual"


def main() -> None:
    print_gate_header(
        name="PRE-PR",
        target="varies by hardware; typically under 3 minutes on multi-core CI, longer on constrained sandboxes",
        includes="the smoke gate, then the broad non-slow test suite run in parallel",
        excludes="integration/manual/slow tests, champion reproduction, and 5k/10k benchmarks",
    )
    passed = run_steps([(python_command("tools/smoke_gate.py"), "Tier 1: smoke gate")])
    if passed:
        passed = run_pytest_with_diagnostics(
            python_command(
                "-m",
                "pytest",
                "tests",
                "-m",
                _MARKER_EXPR,
                "-n",
                "auto",
                "-q",
                "--durations=25",
            ),
            "Tier 2: broad non-slow tests (parallel)",
            collect_only_args=["tests", "-m", _MARKER_EXPR],
        )
    exit_for_gate("PRE-PR", passed)


if __name__ == "__main__":
    main()
