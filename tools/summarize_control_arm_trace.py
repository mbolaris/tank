#!/usr/bin/env python3
"""Rebuild a control-arm campaign summary from its committed trace.

``summarize_campaign`` is a pure function of the candidate outcomes, so the
published report can be regenerated from ``*_candidates.jsonl`` without
re-running the campaign — which matters when a campaign costs hours and a
correction is needed to how its *reference* was checked rather than to any
score it measured.

Example:
    python tools/summarize_control_arm_trace.py tank/survival_5k \
        --baseline-score 687.1077318101328
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.research.control_arm import CandidateOutcome, check_reference_validity, summarize_campaign
from tools.run_bench import load_benchmark_module
from tools.validate_improvement import get_champion_record


def _outcomes(trace_path: Path) -> list[CandidateOutcome]:
    outcomes: list[CandidateOutcome] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        outcomes.append(
            CandidateOutcome(
                index=int(row["candidate"]),
                accepted=bool(row["accepted"]),
                score=float(row["score"]),
                per_seed={str(k): float(v) for k, v in row.get("per_seed", {}).items()},
                mutation_digest=row.get("mutation_digest"),
                runtime_seconds=float(row.get("runtime_seconds", 0.0)),
                heldout_score=row.get("heldout_score"),
                heldout_per_seed={
                    str(k): float(v) for k, v in (row.get("heldout_per_seed") or {}).items()
                },
                heldout_transferred=row.get("heldout_transferred"),
            )
        )
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark_id", help="e.g. tank/survival_5k")
    parser.add_argument("--results-dir", default="research/control_arm")
    parser.add_argument("--benchmark-path", help="Defaults to benchmarks/<benchmark_id>.py")
    parser.add_argument("--heldout-id")
    parser.add_argument("--baseline-score", type=float, required=True)
    parser.add_argument("--seeds", default="42,7,123")
    parser.add_argument("--wall-clock-seconds", type=float, default=0.0)
    parser.add_argument("--benchmark-runs", type=int, default=0)
    parser.add_argument(
        "--recheck-reference",
        action="store_true",
        help="Re-measure whether the champion reproduces here, and record it",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    slug = args.benchmark_id.replace("/", "_")
    outcomes = _outcomes(results_dir / f"{slug}_candidates.jsonl")
    seeds = tuple(int(part) for part in args.seeds.split(",") if part.strip())

    reference_check = None
    if args.recheck_reference:
        bench_path = args.benchmark_path or f"benchmarks/{args.benchmark_id}.py"
        champion_path = ROOT / "champions" / f"{args.benchmark_id}.json"
        champion = dict(get_champion_record(json.loads(champion_path.read_text(encoding="utf-8"))))
        reference_check = check_reference_validity(load_benchmark_module(bench_path), champion)

    report = summarize_campaign(
        benchmark_id=args.benchmark_id,
        heldout_id=args.heldout_id,
        seeds=seeds,
        baseline={"score": args.baseline_score},
        comparison={"score": args.baseline_score},
        reference_kind="local-paired-baseline",
        outcomes=outcomes,
        wall_clock_seconds=args.wall_clock_seconds,
        benchmark_runs=args.benchmark_runs,
        trace_path=results_dir / f"{slug}_candidates.jsonl",
        reference_check=reference_check,
    )
    out = results_dir / f"{slug}_campaign.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} from {len(outcomes)} traced candidates")


if __name__ == "__main__":
    main()
