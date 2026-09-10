#!/usr/bin/env python3
"""Run the Theme 10.6 control-arm campaign and publish its evidence.

The campaign design and its preregistered criteria are fixed in
``docs/CONTROL_ARM_PREREGISTRATION.md``, committed before any result existed.

The pre-flight sensitivity probe is not optional decoration: it is what keeps a
benchmark the operator cannot move (``tank/foraging_gym``) from contributing a
0% acceptance rate that reads like a finding about search.  Pass
``--skip-sensitivity`` only to reproduce a published campaign whose probe is
already on record.

Example:
    python tools/run_control_arm_campaign.py benchmarks/tank/survival_5k.py \
        --candidates 40 --heldout benchmarks/heldout/survival_heldout_5k.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.research.control_arm import (
    DEFAULT_PROBES,
    check_reference_validity,
    probe_operator_sensitivity,
    run_campaign,
)
from tools.non_ai_baseline import parse_seeds
from tools.run_bench import load_benchmark_module
from tools.validate_improvement import get_champion_record


def _load_champion(benchmark_id: str, override: str | None) -> dict | None:
    """Return the champion record used as the acceptance reference, if any."""
    path = Path(override) if override else ROOT / "champions" / f"{benchmark_id}.json"
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    return dict(get_champion_record(record))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark_path", help="Tuning benchmark the arm searches on")
    parser.add_argument("--heldout", help="Held-out evaluator for accepted candidates")
    parser.add_argument("--candidates", type=int, default=40)
    parser.add_argument("--seeds", default="42,7,123")
    parser.add_argument("--target", default="composable")
    parser.add_argument("--mutation-rate", type=float, default=0.3)
    parser.add_argument("--mutation-strength", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=9001, help="Mutation RNG base seed")
    parser.add_argument("--probes", type=int, default=DEFAULT_PROBES)
    parser.add_argument("--champion", help="Champion JSON overriding the default lookup")
    parser.add_argument("--results-dir", default="research/control_arm")
    parser.add_argument("--ledger", help="Attempt ledger path")
    parser.add_argument(
        "--skip-sensitivity",
        action="store_true",
        help="Skip the pre-flight probe (only for reproducing a published campaign)",
    )
    args = parser.parse_args()

    if args.candidates < 1:
        parser.error("--candidates must be >= 1")

    seeds = parse_seeds(args.seeds)
    benchmark = load_benchmark_module(args.benchmark_path)
    heldout = load_benchmark_module(args.heldout) if args.heldout else None
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    slug = str(benchmark.BENCHMARK_ID).replace("/", "_")

    sensitivity = None
    if not args.skip_sensitivity:
        sensitivity = probe_operator_sensitivity(
            benchmark,
            seed=seeds[0],
            probes=args.probes,
            target=args.target,
            mutation_rate=args.mutation_rate,
            mutation_strength=args.mutation_strength,
        )
        (results_dir / f"{slug}_sensitivity.json").write_text(
            json.dumps(sensitivity.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        if not sensitivity.responsive:
            print(
                f"REFUSED: {benchmark.BENCHMARK_ID} did not respond to "
                f"{sensitivity.mutations_applied} parameter mutations across "
                f"{args.probes} probes. Spending campaign budget here would "
                "measure the instrument, not the search.",
                file=sys.stderr,
            )
            sys.exit(2)

    # A champion recorded on another platform is not a reference this machine can
    # use. Check it rather than trust it: an unreproducible champion sitting below
    # the local baseline turns the acceptance rate into a measure of platform
    # drift. Falling back to the paired local baseline is the honest comparison.
    champion = _load_champion(str(benchmark.BENCHMARK_ID), args.champion)
    reference_check = None
    if champion is not None:
        reference_check = check_reference_validity(benchmark, champion)
        (results_dir / f"{slug}_reference_check.json").write_text(
            json.dumps(reference_check.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        if not reference_check.reproduces:
            print(
                f"NOTE: champion for {benchmark.BENCHMARK_ID} does not reproduce here "
                f"(recorded {reference_check.champion_score:.6f}, local "
                f"{reference_check.local_score:.6f}, delta {reference_check.delta:+.6f} "
                f"> tolerance {reference_check.tolerance:g}). Using the paired local "
                "baseline as the acceptance reference instead.",
                file=sys.stderr,
            )
            champion = None

    report = run_campaign(
        benchmark,
        candidates=args.candidates,
        seeds=seeds,
        heldout=heldout,
        reference=champion,
        reference_check=reference_check,
        target=args.target,
        mutation_rate=args.mutation_rate,
        mutation_strength=args.mutation_strength,
        mutation_seed=args.seed,
        results_dir=results_dir,
        ledger_path=args.ledger,
    )
    if sensitivity is not None:
        report["sensitivity"] = sensitivity.to_dict()

    (results_dir / f"{slug}_campaign.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    acceptance = report["acceptance"]
    transfer = report["transfer"]
    compute = report["compute"]
    print(f"benchmark        : {report['benchmark_id']}")
    print(f"candidates       : {report['candidates']}")
    print(f"reference        : {report['reference_kind']} @ {report['reference_score']:.6f}")
    print(
        f"accepted         : {acceptance['accepted']}/{report['candidates']} "
        f"({acceptance['rate']:.1%}, 95% CI "
        f"{acceptance['wilson_95'][0]:.1%}-{acceptance['wilson_95'][1]:.1%})"
    )
    print(f"transferred      : {transfer['transferred']}/{transfer['evaluated']}")
    print(
        f"best achieved    : {report['best_achieved']['score']} "
        f"(delta {report['best_achieved']['delta_vs_reference']:+.6f})"
    )
    print(
        f"compute          : {compute['benchmark_runs']} benchmark runs, "
        f"{compute['wall_clock_seconds']:.0f}s wall clock"
    )


if __name__ == "__main__":
    main()
