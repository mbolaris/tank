#!/usr/bin/env python3
"""Run the contributor pre-PR validation gate.

The broad non-slow suite is split into named shards (see tools/pre_pr_shards.py)
so failures are easy to isolate and cheap to re-run:

    python tools/pre_pr_gate.py                    # smoke gate + every shard
    python tools/pre_pr_gate.py --shard evolution  # smoke gate + one shard
    python tools/pre_pr_gate.py --list-shards      # show shards and file counts

The default full run executes exactly the same tests as the pre-shard gate did
(the shards partition the suite), just grouped with per-shard summaries.
"""

import argparse

try:
    from tools.gate_common import (
        exit_for_gate,
        print_gate_header,
        python_command,
        run_pytest_with_diagnostics,
        run_steps,
    )
    from tools.pre_pr_shards import resolve_shards, shard_names
except ImportError:
    from gate_common import (  # type: ignore[import-not-found,no-redef]
        exit_for_gate,
        print_gate_header,
        python_command,
        run_pytest_with_diagnostics,
        run_steps,
    )
    from pre_pr_shards import (  # type: ignore[import-not-found,no-redef]
        resolve_shards,
        shard_names,
    )

_MARKER_EXPR = "not slow and not integration and not manual"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--shard",
        choices=shard_names(),
        help="run only this shard of the broad suite (plus the smoke gate)",
    )
    parser.add_argument(
        "--list-shards",
        action="store_true",
        help="list shard names with their test-file counts and exit",
    )
    return parser.parse_args()


def _run_shard(name: str, test_files: list[str]) -> bool:
    return run_pytest_with_diagnostics(
        python_command(
            "-m",
            "pytest",
            *test_files,
            "-m",
            _MARKER_EXPR,
            "-n",
            "auto",
            "-q",
            "--durations=25",
        ),
        f"Tier 2 shard '{name}': non-slow tests (parallel)",
        collect_only_args=[*test_files, "-m", _MARKER_EXPR],
    )


def main() -> None:
    args = _parse_args()
    shards = resolve_shards()

    if args.list_shards:
        for name in shard_names():
            print(f"{name}: {len(shards[name])} test files")
        raise SystemExit(0)

    selected = [args.shard] if args.shard else shard_names()
    print_gate_header(
        name="PRE-PR" if args.shard is None else f"PRE-PR (shard: {args.shard})",
        target="varies by hardware; typically under 3 minutes on multi-core CI, longer on constrained sandboxes",
        includes="the smoke gate, then the broad non-slow test suite run in parallel, sharded as "
        + ", ".join(selected),
        excludes="integration/manual/slow tests, champion reproduction, and 5k/10k benchmarks",
    )

    passed = run_steps([(python_command("tools/smoke_gate.py"), "Tier 1: smoke gate")])
    for name in selected:
        if not passed:
            break
        passed = _run_shard(name, shards[name])
        if not passed:
            print(
                f"\nHint: re-run just this shard with `python tools/pre_pr_gate.py --shard {name}`",
                flush=True,
            )
    exit_for_gate("PRE-PR", passed)


if __name__ == "__main__":
    main()
