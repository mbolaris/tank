#!/usr/bin/env python3
"""Re-run a benchmark with one world-config key changed, and report the delta.

Config questions about the tank tend to be argued from the code path rather
than measured: a mechanism plausibly causes an outcome, so it gets written down
as the thing to check first. This runs the benchmark both ways instead.

Its first use refuted a documented suspicion. `CLAUDE.md` said ball pursuit
pre-empts food seeking and to check it first when diagnosing starvation; the
mechanism is real, but turning the practice ball off in `survival_5k` moves the
starvation rate by at most two points and on seed 42 moves it the wrong way.

Example:
    python tools/ablate_world_config.py benchmarks/tank/survival_5k.py \
        --key tank_practice_enabled --off --seeds 42,2,999
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.non_ai_baseline import parse_seeds
from tools.run_bench import load_benchmark_module

# Metadata worth carrying into the report for any tank benchmark.
_REPORTED = (
    "starvation_rate",
    "score_valid",
    "total_deaths",
    "starvation_deaths",
    "max_generation",
)


def _parse_value(raw: str) -> Any:
    """Interpret a CLI override as JSON, falling back to a plain string."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _run(benchmark: Any, seed: int, key: str | None, value: Any) -> dict[str, Any]:
    """Run one seed, optionally with a single world-config key overridden."""
    original = dict(benchmark.WORLD_CONFIG)
    try:
        if key is not None:
            benchmark.WORLD_CONFIG[key] = value
        result = benchmark.run(seed)
    finally:
        benchmark.WORLD_CONFIG.clear()
        benchmark.WORLD_CONFIG.update(original)

    metadata = result.get("metadata")
    reported = {
        name: metadata.get(name)
        for name in _REPORTED
        if isinstance(metadata, dict) and name in metadata
    }
    return {"score": float(result["score"]), **reported}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark_path")
    parser.add_argument("--key", required=True, help="World-config key to override")
    parser.add_argument("--value", help="JSON value for the override")
    parser.add_argument("--off", action="store_true", help="Shorthand for --value false")
    parser.add_argument("--seeds", default="42,2,999")
    parser.add_argument("--out", help="Write the comparison to JSON")
    args = parser.parse_args()

    if args.off and args.value is not None:
        parser.error("pass --off or --value, not both")
    if not args.off and args.value is None:
        parser.error("one of --off or --value is required")
    value = False if args.off else _parse_value(args.value)

    benchmark = load_benchmark_module(args.benchmark_path)
    if args.key not in benchmark.WORLD_CONFIG:
        # Overriding a key the benchmark never sets compares against a default
        # that may not be what the reader assumes, so say so rather than guess.
        print(
            f"note: {args.key!r} is not set in {benchmark.BENCHMARK_ID}'s WORLD_CONFIG; "
            "the baseline arm uses the engine default.",
            file=sys.stderr,
        )

    rows = []
    for seed in parse_seeds(args.seeds):
        baseline = _run(benchmark, seed, None, None)
        changed = _run(benchmark, seed, args.key, value)
        rows.append({"seed": seed, "baseline": baseline, "changed": changed})
        print(f"seed {seed}:")
        for name in ("score", *_REPORTED):
            if name not in baseline:
                continue
            before, after = baseline[name], changed.get(name)
            mark = "" if before == after else "   <-- changed"
            print(f"    {name:<18} {before!s:>12} -> {after!s:>12}{mark}")

    payload = {
        "benchmark_id": str(benchmark.BENCHMARK_ID),
        "key": args.key,
        "value": value,
        "rows": rows,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
