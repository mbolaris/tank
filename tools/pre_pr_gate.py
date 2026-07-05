#!/usr/bin/env python3
"""Run the contributor pre-PR validation gate.

The broad non-slow suite is split into named shards (see tools/pre_pr_shards.py)
so failures are easy to isolate and cheap to re-run:

    python tools/pre_pr_gate.py                    # smoke gate + every shard
    python tools/pre_pr_gate.py --shard evolution  # smoke gate + one shard
    python tools/pre_pr_gate.py --list-shards      # show shards and file counts
    python tools/pre_pr_gate.py --no-xdist         # run serially (constrained envs)
    python tools/pre_pr_gate.py --timeout 300      # run with a custom per-shard timeout

The default full run executes exactly the same tests as the pre-shard gate did
(the shards partition the suite), just grouped with per-shard summaries.

In sandboxed / CI-constrained environments where pytest-xdist hangs or wedges,
use --no-xdist (or set PRE_PR_NO_XDIST=1) to fall back to serial execution.
The gate auto-detects common xdist failure signals and prints a fallback hint.
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
    from pre_pr_shards import resolve_shards, shard_names  # type: ignore[import-not-found,no-redef]

_MARKER_EXPR = "not slow and not integration and not manual"

# Default per-shard wall-clock timeout in seconds.
# Generous enough for most machines, but prevents indefinite hangs.
_DEFAULT_SHARD_TIMEOUT = 600


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
    parser.add_argument(
        "--no-xdist",
        action="store_true",
        default=False,
        help=(
            "run shards serially instead of in parallel (drops -n auto). "
            "Use in sandboxed / resource-constrained environments where "
            "pytest-xdist hangs. Also honoured via env var PRE_PR_NO_XDIST=1."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_SHARD_TIMEOUT,
        help=(
            "wall-clock timeout in seconds per shard (default: %(default)s). "
            "Set to 0 to disable."
        ),
    )
    return parser.parse_args()


_XDIST_ERROR_SIGNALS = (
    "xdist",
    "gw0",
    "pytest-xdist",
    "Failed to start worker",
    "DoneWithoutBreak",
)


def _run_shard(
    name: str,
    test_files: list[str],
    *,
    no_xdist: bool = False,
    timeout: float | None = None,
) -> bool:
    """Run one named shard, either in parallel (default) or serially (--no-xdist)."""
    import os

    use_serial = no_xdist or os.environ.get("PRE_PR_NO_XDIST", "") not in ("", "0", "false")
    if use_serial:
        label = f"Tier 2 shard '{name}': non-slow tests (serial)"
        cmd = python_command(
            "-m",
            "pytest",
            *test_files,
            "-m",
            _MARKER_EXPR,
            "-q",
            "--durations=25",
        )
    else:
        label = f"Tier 2 shard '{name}': non-slow tests (parallel)"
        cmd = python_command(
            "-m",
            "pytest",
            *test_files,
            "-m",
            _MARKER_EXPR,
            "-n",
            "auto",
            "-q",
            "--durations=25",
        )
    return run_pytest_with_diagnostics(
        cmd,
        label,
        collect_only_args=[*test_files, "-m", _MARKER_EXPR],
        timeout=timeout,
    )


def main() -> None:
    import os

    args = _parse_args()
    shards = resolve_shards()

    if args.list_shards:
        for name in shard_names():
            print(f"{name}: {len(shards[name])} test files")
        raise SystemExit(0)

    no_xdist = args.no_xdist or os.environ.get("PRE_PR_NO_XDIST", "") not in ("", "0", "false")
    selected = [args.shard] if args.shard else shard_names()
    effective_timeout: float | None = args.timeout if args.timeout > 0 else None

    mode_label = "serial" if no_xdist else "parallel"
    timeout_label = f"{int(args.timeout)}s" if effective_timeout else "none"
    print_gate_header(
        name="PRE-PR" if args.shard is None else f"PRE-PR (shard: {args.shard})",
        target="varies by hardware; typically under 3 minutes on multi-core CI, longer on constrained sandboxes",
        includes=(
            f"the smoke gate, then the broad non-slow test suite run {mode_label}, sharded as "
            + ", ".join(selected)
        ),
        excludes="integration/manual/slow tests, champion reproduction, and 5k/10k benchmarks",
    )
    if no_xdist:
        print("[INFO] Running in serial mode (--no-xdist / PRE_PR_NO_XDIST).", flush=True)
    if effective_timeout:
        print(f"[INFO] Per-shard timeout: {timeout_label}.", flush=True)

    passed = run_steps([(python_command("tools/smoke_gate.py"), "Tier 1: smoke gate")])
    for name in selected:
        if not passed:
            break
        passed = _run_shard(name, shards[name], no_xdist=no_xdist, timeout=effective_timeout)
        if not passed:
            if not no_xdist:
                print(
                    f"\nHint: re-run just this shard with:"
                    f"\n  python tools/pre_pr_gate.py --shard {name}"
                    f"\nIf the failure looks like an xdist hang or worker crash, try:"
                    f"\n  python tools/pre_pr_gate.py --shard {name} --no-xdist"
                    f"\nIf the shard timed out, increase the limit with --timeout <seconds>.",
                    flush=True,
                )
            else:
                print(
                    f"\nHint: re-run just this shard with `python tools/pre_pr_gate.py --shard {name} --no-xdist`"
                    f"\nIf the shard timed out, increase the limit with --timeout <seconds>.",
                    flush=True,
                )
    exit_for_gate("PRE-PR", passed)


if __name__ == "__main__":
    main()
