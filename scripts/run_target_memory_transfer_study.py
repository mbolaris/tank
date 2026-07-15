#!/usr/bin/env python3
"""Run the multi-seed target-memory transfer study and write its report.

Examples:
    # Full scaled study (the evidence run; ~10 min/seed single-core, use -j)
    python scripts/run_target_memory_transfer_study.py \
        --output research/target_memory_transfer/study_v1.json -j 6

    # Quick structural smoke at a tiny budget (NOT evidence)
    python scripts/run_target_memory_transfer_study.py --quick \
        --seeds 0,1 --output /tmp/quick_study.json

The report JSON contains per-seed rows plus the aggregate (bootstrap CIs,
median effects, fraction of seeds positive, per-family effects, adaptation
stats and the conservative verdict). A markdown rendering is written next to
the JSON with the same stem.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.behavior.target_memory_transfer_evolution import TransferStudyConfig
from core.behavior.target_memory_transfer_study import (
    DEFAULT_STUDY_SEEDS,
    SCALED_STUDY_CONFIG,
    build_report,
    render_markdown,
    seed_row,
)

# Tiny structural-smoke budget: exercises every code path in minutes of
# nothing, but its numbers are meaningless - never report them as evidence.
QUICK_CONFIG = TransferStudyConfig(
    population_size=4,
    generations=2,
    evolution_runs=1,
    food_train_count=3,
    food_validation_count=2,
    ball_held_out_count=3,
    ball_train_count=3,
    ball_validation_count=2,
)


def _parse_seeds(raw: str) -> list[int]:
    return [int(part) for part in raw.split(",") if part.strip()]


def _worker(args: tuple[int, dict]) -> dict:
    seed, cfg_kwargs = args
    return seed_row(seed, TransferStudyConfig(**cfg_kwargs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--seeds",
        type=_parse_seeds,
        default=list(DEFAULT_STUDY_SEEDS),
        help="Comma-separated outer seeds (default: the fixed 12-seed panel)",
    )
    parser.add_argument("--population", type=int, default=None)
    parser.add_argument("--generations", type=int, default=None)
    parser.add_argument("--runs", type=int, default=None, help="Independent evolution runs per arm")
    parser.add_argument("--quick", action="store_true", help="Tiny smoke budget (not evidence)")
    parser.add_argument("-j", "--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True, help="Report JSON path")
    args = parser.parse_args()

    base = QUICK_CONFIG if args.quick else SCALED_STUDY_CONFIG
    overrides = {
        key: value
        for key, value in (
            ("population_size", args.population),
            ("generations", args.generations),
            ("evolution_runs", args.runs),
        )
        if value is not None
    }
    config = TransferStudyConfig(**{**config_kwargs(base), **overrides})
    cfg_kwargs = config_kwargs(config)

    started = time.perf_counter()
    print(f"Running {len(args.seeds)} seeds with {config} using {args.workers} worker(s)")

    rows = []
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for row in pool.map(_worker, [(seed, cfg_kwargs) for seed in args.seeds]):
                rows.append(row)
                print(
                    f"  seed {row['seed']}: vs_disjoint {row['transfer_vs_disjoint']:+.4f}, "
                    f"vs_neutral {row['transfer_vs_neutral']:+.4f}",
                    flush=True,
                )
    else:
        for seed in args.seeds:
            row = seed_row(seed, config)
            rows.append(row)
            print(
                f"  seed {seed}: vs_disjoint {row['transfer_vs_disjoint']:+.4f}, "
                f"vs_neutral {row['transfer_vs_neutral']:+.4f}",
                flush=True,
            )

    report = build_report(rows, config)
    report["study"]["wall_time_seconds"] = round(time.perf_counter() - started, 1)
    report["study"]["quick_mode_not_evidence"] = bool(args.quick)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path = args.output.with_suffix(".md")
    markdown_path.write_text(render_markdown(report))

    print(f"\nReport: {args.output}\nSummary: {markdown_path}\n")
    print(render_markdown(report))
    return 0


def config_kwargs(config: TransferStudyConfig) -> dict:
    from dataclasses import asdict

    return asdict(config)


if __name__ == "__main__":
    raise SystemExit(main())
