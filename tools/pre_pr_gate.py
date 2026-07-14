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

CI runs each shard as its own concurrent job, so it passes a few extra flags
that contributors normally don't need:

    python tools/pre_pr_gate.py --shard core --skip-smoke   # smoke runs in a sibling job
    python tools/pre_pr_gate.py --shard core --coverage      # write coverage data (honors $COVERAGE_FILE)
    python tools/pre_pr_gate.py --shard core --xdist --workers 2  # cap workers on shared runners
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
        "--xdist",
        action="store_true",
        default=False,
        help="run shards in parallel using pytest-xdist (runs serially by default).",
    )
    parser.add_argument(
        "--no-xdist",
        action="store_true",
        help="explicitly request serial shard execution (the default).",
    )
    parser.add_argument(
        "--workers",
        default="auto",
        help=(
            "pytest-xdist worker count to use with --xdist (default: %(default)s). "
            "When CI runs several shards concurrently as separate jobs, pass a "
            "small fixed number (e.g. 2) instead of 'auto' to avoid each shard "
            "oversubscribing its runner."
        ),
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help=(
            "skip the embedded Tier 1 smoke gate before running shards. Only use "
            "this when an equivalent smoke gate is already running concurrently "
            "elsewhere (e.g. a sibling CI job) - contributors running the gate "
            "standalone before a commit should not pass this."
        ),
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help=(
            "collect core/backend coverage while running shards. Honors the "
            "COVERAGE_FILE env var so concurrent shard jobs can each write a "
            "separate data file for later combination."
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
    workers: str = "auto",
    coverage: bool = False,
) -> bool:
    """Run one named shard, either in parallel (default) or serially (--no-xdist)."""
    import os

    use_serial = no_xdist or os.environ.get("PRE_PR_NO_XDIST", "") not in ("", "0", "false")
    cov_args = ["--cov=core", "--cov=backend", "--cov-report="] if coverage else []
    if use_serial:
        label = f"Tier 2 shard '{name}': non-slow tests (serial)"
        cmd = python_command(
            "-m",
            "pytest",
            *test_files,
            "-m",
            _MARKER_EXPR,
            *cov_args,
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
            workers,
            *cov_args,
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

    no_xdist = (
        args.no_xdist
        or not args.xdist
        or os.environ.get("PRE_PR_NO_XDIST", "") not in ("", "0", "false")
    )
    selected = [args.shard] if args.shard else shard_names()
    effective_timeout: float | None = args.timeout if args.timeout > 0 else None

    mode_label = "serial" if no_xdist else "parallel"
    timeout_label = f"{int(args.timeout)}s" if effective_timeout else "none"
    smoke_clause = "the smoke gate, then " if not args.skip_smoke else ""
    print_gate_header(
        name="PRE-PR" if args.shard is None else f"PRE-PR (shard: {args.shard})",
        target="varies by hardware; typically under 3 minutes on multi-core CI, longer on constrained sandboxes",
        includes=(
            f"{smoke_clause}the broad non-slow test suite run {mode_label}, sharded as "
            + ", ".join(selected)
        ),
        excludes="integration/manual/slow tests, champion reproduction, and 5k/10k benchmarks",
    )
    if no_xdist:
        print("[INFO] Running in serial mode (default / PRE_PR_NO_XDIST).", flush=True)
    if effective_timeout:
        print(f"[INFO] Per-shard timeout: {timeout_label}.", flush=True)
    if args.skip_smoke:
        print(
            "[INFO] Skipping Tier 1 smoke gate (--skip-smoke): assuming an equivalent "
            "check is already running concurrently elsewhere.",
            flush=True,
        )

    passed = (
        True
        if args.skip_smoke
        else run_steps([(python_command("tools/smoke_gate.py"), "Tier 1: smoke gate")])
    )
    for name in selected:
        if not passed:
            break
        passed = _run_shard(
            name,
            shards[name],
            no_xdist=no_xdist,
            timeout=effective_timeout,
            workers=args.workers,
            coverage=args.coverage,
        )
        if not passed and not no_xdist:
            print(
                f"\n[WARNING] Shard '{name}' failed or timed out in parallel mode.",
                f"\n[INFO] Retrying shard '{name}' in serial mode automatically...",
                flush=True,
            )
            passed = _run_shard(
                name,
                shards[name],
                no_xdist=True,
                timeout=effective_timeout,
                coverage=args.coverage,
            )

        if not passed:
            if not no_xdist:
                print(
                    f"\nHint: re-run just this shard with:"
                    f"\n  python tools/pre_pr_gate.py --shard {name} --xdist"
                    f"\nIf the failure looks like an xdist hang or worker crash, run serially instead:"
                    f"\n  python tools/pre_pr_gate.py --shard {name}"
                    f"\nIf the shard timed out, increase the limit with --timeout <seconds>.",
                    flush=True,
                )
            else:
                print(
                    f"\nHint: re-run just this shard with `python tools/pre_pr_gate.py --shard {name}`"
                    f"\nIf the shard timed out, increase the limit with --timeout <seconds>.",
                    flush=True,
                )
    exit_for_gate("PRE-PR", passed)


if __name__ == "__main__":
    main()
