#!/usr/bin/env python3
"""Run the under-90-second curated agent gate.

This sits between the smoke gate and the pre-PR gate:
  smoke (under 30s) -> agent (under 90s) -> pre-PR (broad suite) -> full (nightly)

Use agent gate before a local commit. It runs the smoke gate first, then a
curated set of architecture, determinism, energy, genetics, protocol, and
import-boundary tests - broader than smoke, but much cheaper than the full
non-slow suite that the pre-PR gate runs.
"""

try:
    from tools.gate_common import exit_for_gate, print_gate_header, python_command, run_steps
except ImportError:
    from gate_common import exit_for_gate, print_gate_header, python_command, run_steps  # type: ignore[import-not-found,no-redef]


# Curated test modules for the agent gate (beyond what smoke already covers).
# Selected to catch the most common breakages from algorithm, config, and
# infrastructure changes without running the full 1700+ non-slow suite.
_AGENT_CURATED_TESTS = [
    "tests/test_determinism.py",
    "tests/test_energy_integration.py",
    "tests/test_energy_accounting.py",
    "tests/test_protocol_conformance.py",
    "tests/test_config_hash.py",
    "tests/test_architecture_patterns.py",
    "tests/test_soccer_engine_api.py",
    "tests/test_import_boundaries.py",
    "tests/test_engine_phase_order.py",
    "tests/test_simulation_contract_invariants.py",
    "tests/test_trait_invariants.py",
    "tests/test_mutation_enforcement.py",
    "tests/test_genetics_refactor.py",
    "tests/test_genome_compatibility.py",
    "tests/test_rng_policy.py",
    "tests/test_engine_no_tank_imports.py",
    "tests/test_behavioral_trait_wiring.py",
    "tests/test_algorithm_decoupling.py",
]


def main() -> None:
    print_gate_header(
        name="AGENT",
        target="under 90 seconds",
        includes="smoke gate, then curated architecture/determinism/energy/genetics tests",
        excludes=(
            "the broad non-slow suite, integration/manual/slow tests, " "and 5k/10k benchmarks"
        ),
    )
    steps = [
        (python_command("tools/smoke_gate.py"), "Tier 1: smoke gate"),
        (
            python_command(
                "-m",
                "pytest",
                *_AGENT_CURATED_TESTS,
                "-m",
                "not slow and not integration and not manual",
                "-q",
            ),
            "Tier 1.5: curated agent correctness suite",
        ),
    ]
    exit_for_gate("AGENT", run_steps(steps))


if __name__ == "__main__":
    main()
