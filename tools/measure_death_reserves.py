#!/usr/bin/env python3
"""Report what fish were still holding when they died.

A death mix says how many fish starved. It does not say whether they starved
empty or starved rich, and the difference turned out to be the tank's largest
single energy leak: before fish could draw on their own reserves, 29-51% of
`survival_5k` starvation deaths (seeds 42/2/999) were fish at zero energy holding
a bank they were only allowed to spend on offspring.

Run against the current tree to see the state now; run it in a worktree at an
earlier commit to see the state then:

    python tools/measure_death_reserves.py benchmarks/tank/survival_5k.py --seeds 42
    git worktree add /tmp/before <commit>
    cd /tmp/before && python tools/measure_death_reserves.py \
        benchmarks/tank/survival_5k.py --seeds 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.research.death_reserves import SOLVENT_BANK_THRESHOLD, record_deaths, summarize
from tools.non_ai_baseline import parse_seeds
from tools.run_bench import load_benchmark_module


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark_path")
    parser.add_argument("--seeds", default="42")
    parser.add_argument("--frames", type=int, help="Override the benchmark's frame count")
    parser.add_argument("--out", help="Write the report to JSON")
    parser.add_argument(
        "--records",
        action="store_true",
        help="Include every individual death in the JSON, not just the summaries",
    )
    args = parser.parse_args()

    benchmark = load_benchmark_module(args.benchmark_path)
    seeds = parse_seeds(args.seeds)
    rows: list[dict[str, Any]] = []

    for seed in seeds:
        records = record_deaths(benchmark, seed, frames=args.frames)
        summaries = summarize(records)
        print(f"\nseed {seed}: {len(records)} deaths")
        print(
            f"    {'cause':>12} {'deaths':>7} {'w/ reserves':>12} "
            f"{'mean bank':>10} {'max bank':>10} {'bank lost':>11}"
        )
        for summary in summaries:
            print(
                f"    {summary.cause:>12} {summary.deaths:>7} "
                f"{summary.solvent_deaths:>5} ({summary.solvent_share:>4.0%}) "
                f"{summary.mean_bank:>10.1f} {summary.max_bank:>10.1f} "
                f"{summary.total_bank_destroyed:>11.0f}"
            )
        row: dict[str, Any] = {
            "seed": seed,
            "deaths": len(records),
            "summaries": [s.as_dict() for s in summaries],
        }
        if args.records:
            row["records"] = [r.as_dict() for r in records]
        rows.append(row)

    if args.out:
        payload = {
            "benchmark_id": str(benchmark.BENCHMARK_ID),
            "frames": args.frames or int(benchmark.FRAMES),
            "solvent_bank_threshold": SOLVENT_BANK_THRESHOLD,
            "seeds": rows,
        }
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
