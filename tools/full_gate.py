#!/usr/bin/env python3
"""Run strict full validation for maintainers and nightly CI."""

try:
    from tools.gate_common import exit_for_gate, print_gate_header, python_command, run_steps
except ImportError:
    from gate_common import exit_for_gate, print_gate_header, python_command, run_steps  # type: ignore[import-not-found,no-redef]


def main() -> None:
    print_gate_header(
        name="FULL",
        target="unbounded; nightly or explicit maintainer use only",
        includes="pre-PR gate, integration/slow tests, and strict champion reproduction",
        excludes="manual tests",
    )
    steps = [
        (python_command("tools/pre_pr_gate.py"), "Tier 2: pre-PR gate"),
        (
            python_command(
                "-m",
                "pytest",
                "tests",
                "-m",
                "slow or integration",
                "--ignore=tests/test_benchmark_integrity.py",
                "-o",
                "addopts=--strict-markers --tb=short",
                "-q",
            ),
            "Tier 3: slow and integration tests",
        ),
        (
            python_command("tools/validate_champion_provenance.py"),
            "Tier 3: champion provenance",
        ),
        (
            python_command("tools/verify_all_champions.py"),
            "Tier 3: strict champion reproduction",
        ),
    ]
    exit_for_gate("FULL", run_steps(steps))


if __name__ == "__main__":
    main()
