#!/usr/bin/env python3
"""Re-score an accepted control-arm candidate on seeds it was never selected on.

Acceptance ranks candidates on the seeds the campaign searched. Confirmation
asks the stricter question the first campaign showed was needed: does the
candidate ever turn a benchmark run that was valid into one that is not?

Example:
    python tools/confirm_control_arm_candidate.py 27 \
        --benchmark benchmarks/tank/survival_5k.py --seeds 1,2,999
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.research.candidate_confirmation import DEFAULT_CONFIRMATION_SEEDS, confirm_candidate
from tools.non_ai_baseline import _plan_for, parse_seeds
from tools.run_bench import load_benchmark_module


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=int, help="Candidate index from the campaign trace")
    parser.add_argument("--benchmark", default="benchmarks/tank/survival_5k.py")
    parser.add_argument(
        "--seeds", default=",".join(str(seed) for seed in DEFAULT_CONFIRMATION_SEEDS)
    )
    parser.add_argument("--trace", default="research/control_arm/tank_survival_5k_candidates.jsonl")
    parser.add_argument("--mutation-seed", type=int, default=9001)
    parser.add_argument("--mutation-rate", type=float, default=0.3)
    parser.add_argument("--mutation-strength", type=float, default=0.15)
    parser.add_argument("--target", default="composable")
    parser.add_argument("--out", help="Write the confirmation report to JSON")
    args = parser.parse_args()

    # Re-derive the plan from its recorded seed, then check it against the
    # committed trace: a confirmation of a different mutation is worthless.
    plan = _plan_for(
        target=args.target,
        seed=args.mutation_seed + args.candidate,
        generation=args.candidate,
        mutation_rate=args.mutation_rate,
        mutation_strength=args.mutation_strength,
    )
    trace = Path(args.trace)
    if trace.exists():
        rows = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
        recorded = [row for row in rows if row.get("candidate") == args.candidate]
        if recorded and recorded[0].get("mutation_plan") != plan.to_dict():
            parser.error(f"re-derived plan for candidate {args.candidate} does not match {trace}")

    report = confirm_candidate(
        load_benchmark_module(args.benchmark), plan, seeds=parse_seeds(args.seeds)
    )
    payload = report.to_dict()
    payload["candidate"] = args.candidate

    print(f"benchmark : {report.benchmark_id}")
    print(f"candidate : {args.candidate}")
    for outcome in report.outcomes:
        flag = "  INVALIDATED" if outcome.invalidated else ""
        print(
            f"  seed {outcome.seed:>4}: {outcome.baseline_score:10.4f} -> "
            f"{outcome.candidate_score:10.4f}  {outcome.delta:+10.4f}{flag}"
        )
        if outcome.candidate_invalid_reason:
            print(f"             {outcome.candidate_invalid_reason}")
    print(f"mean delta: {report.mean_delta:+.4f}")
    print(f"CONFIRMED : {report.confirmed}")

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    sys.exit(0 if report.confirmed else 1)


if __name__ == "__main__":
    main()
