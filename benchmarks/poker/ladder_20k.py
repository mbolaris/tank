"""Poker Ladder Benchmark (20k nominal hands).

Measures the absolute heads-up skill of the evolvable poker substrate
(ComposablePokerStrategy with neutral defaults - what founder fish play) against
a frozen ladder of reference opponents, from a random-legal floor to the GTO
expert ceiling. Because the rungs never change, bb/100 against each rung is an
absolute, longitudinally comparable skill measure: improvements to the
composable strategy's logic or defaults move the score; re-tuning ecosystem
config does not.

Ladder rungs (weak to strong):
    L0 random         - random legal actions (skill floor)
    L1 loose_passive  - calling station
    L2 tight_aggressive - solid rule-based TAG
    L3 gto_expert     - strongest scripted opponent. Despite the strategy id,
                        this is a GTO-inspired heuristic, not a solver-verified
                        GTO agent; it is the best scripted ruler available, not
                        an unexploitable ceiling.

Each rung is evaluated with duplicate deals (same cards, both seats) via
core/poker/evaluation/benchmark_eval.py, which cancels card luck and seat
position. Score is the mean bb/100 across rungs (higher is better; 0 vs a rung
means break-even with it).
"""

import random
import sys
import time
from typing import Any

from core.poker.evaluation.benchmark_eval import (
    BenchmarkEvalConfig,
    evaluate_vs_single_benchmark_duplicate,
)
from core.poker.strategy.composable.strategy import ComposablePokerStrategy
from core.skill import RungResult, SkillLadderSummary, ladder_position_index

SKILL_DOMAIN = "poker"
SKILL_METRIC_NAME = "bb_per_100"

BENCHMARK_ID = "poker/ladder_20k"

# Frozen ruler ladder, weak to strong. Changing a rung's strategy code changes
# what the benchmark measures; treat these as immutable references and add new
# rungs instead of editing existing ones.
LADDER_RUNGS: tuple[str, ...] = (
    "random",
    "loose_passive",
    "tight_aggressive",
    "gto_expert",
)

SMALL_BLIND = 50
BIG_BLIND = 100
STARTING_STACK = 10_000
HANDS_PER_MATCH = 100
NUM_DUPLICATE_SETS = 25  # per rung; x2 seats = 5,000 nominal hands per rung
EXPECTED_RUNTIME_SECONDS = 60

# Effective configuration captured by the champion config hash
# (core/solutions/config_hash.py). Anything that changes the score belongs here.
CONFIG: dict[str, Any] = {
    "ladder_rungs": list(LADDER_RUNGS),
    "small_blind": SMALL_BLIND,
    "big_blind": BIG_BLIND,
    "starting_stack": STARTING_STACK,
    "hands_per_match": HANDS_PER_MATCH,
    "num_duplicate_sets": NUM_DUPLICATE_SETS,
    "hero": "composable_default",
}


def _make_hero(seed: int, rung_index: int) -> ComposablePokerStrategy:
    """Fresh neutral-default hero per rung.

    A fresh instance per rung keeps rung results independent (no opponent-model
    or RNG-state leakage between rungs) and pins the hero to the evolvable
    substrate's defaults - the exact strategy founder fish receive.
    """
    hero_rng = random.Random(seed * 1_000_003 + rung_index)
    return ComposablePokerStrategy(rng=hero_rng)


def run(
    seed: int,
    *,
    num_duplicate_sets: int = NUM_DUPLICATE_SETS,
    hands_per_match: int = HANDS_PER_MATCH,
) -> dict[str, Any]:
    """Run the benchmark deterministically.

    Args:
        seed: Base seed for card dealing and all strategy RNGs
        num_duplicate_sets: Duplicate-deal sets per rung (default: full config)
        hands_per_match: Hands per duplicate set per seat (default: full config)

    Returns:
        Result dictionary with score, per-rung metrics, and metadata
    """
    start_time = time.time()

    per_rung: list[dict[str, Any]] = []
    rung_results: list[RungResult] = []
    rung_scores: dict[str, float] = {}
    rungs_beaten = 0
    total_hands = 0

    for rung_index, rung_id in enumerate(LADDER_RUNGS):
        cfg = BenchmarkEvalConfig(
            small_blind=SMALL_BLIND,
            big_blind=BIG_BLIND,
            starting_stack=STARTING_STACK,
            hands_per_match=hands_per_match,
            num_duplicate_sets=num_duplicate_sets,
            base_seed=seed,
        )
        hero = _make_hero(seed, rung_index)

        print(
            f"  Rung L{rung_index} ({rung_id}): "
            f"{num_duplicate_sets} duplicate sets x {hands_per_match} hands x 2 seats...",
            file=sys.stderr,
        )
        result = evaluate_vs_single_benchmark_duplicate(hero, rung_id, cfg)

        # "Beaten" = the 95% CI on bb/100 sits entirely above zero.
        beaten = result.is_statistically_significant and result.bb_per_100 > 0.0
        if beaten:
            rungs_beaten += 1

        total_hands += result.hands_played
        rung_scores[rung_id] = result.bb_per_100
        per_rung.append(
            {
                "rung": f"L{rung_index}",
                "rung_id": rung_id,
                "bb_per_100": result.bb_per_100,
                "bb_per_100_ci_95": list(result.bb_per_100_ci_95),
                "hands_played": result.hands_played,
                "sample_variance": result.sample_variance,
                "statistically_significant": result.is_statistically_significant,
                "beaten": beaten,
            }
        )
        rung_results.append(
            RungResult(
                rung=f"L{rung_index}",
                rung_id=rung_id,
                metric=result.bb_per_100,
                ci_95=result.bb_per_100_ci_95,
                beaten=beaten,
                detail={"hands_played": result.hands_played},
            )
        )

    score = sum(rung_scores.values()) / max(len(rung_scores), 1)
    runtime = time.time() - start_time

    skill = SkillLadderSummary(
        domain=SKILL_DOMAIN,
        benchmark_id=BENCHMARK_ID,
        metric_name=SKILL_METRIC_NAME,
        skill_index=ladder_position_index(tuple(rung_results)),
        rungs=tuple(rung_results),
        notes=(
            "Ladder-position index: 100 = beats every current rung (ceiling "
            "saturated, add a taller rung). gto_expert is a GTO-inspired "
            "scripted heuristic, not solver-verified GTO."
        ),
    )

    return {
        "benchmark_id": BENCHMARK_ID,
        "seed": seed,
        "score": score,
        "score_breakdown": dict(rung_scores),
        "runtime_seconds": runtime,
        "metadata": {
            "hero": "composable_default",
            "ladder_rungs": list(LADDER_RUNGS),
            "rungs_beaten": rungs_beaten,
            "total_rungs": len(LADDER_RUNGS),
            "total_hands": total_hands,
            "num_duplicate_sets": num_duplicate_sets,
            "hands_per_match": hands_per_match,
            "small_blind": SMALL_BLIND,
            "big_blind": BIG_BLIND,
            "starting_stack": STARTING_STACK,
            "score_mode": "mean bb/100 across ladder rungs (duplicate-deal HU)",
            "top_rung_note": (
                "gto_expert is a GTO-inspired scripted heuristic, not a "
                "solver-verified GTO agent; treat it as the strongest scripted "
                "ruler, not an unexploitable ceiling."
            ),
            "vs_top_rung_bb_per_100": rung_scores.get(LADDER_RUNGS[-1], 0.0),
            "per_rung_results": per_rung,
            "skill": skill.to_dict(),
        },
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()

    if args.verify_determinism:
        res1 = run(args.seed)
        res2 = run(args.seed)
        score_diff = abs(res1["score"] - res2["score"])
        if score_diff > 1e-9:
            print(f"DETERMINISM FAILED: {res1['score']} != {res2['score']}", file=sys.stderr)
            sys.exit(1)
        print(f"DETERMINISM PASSED: {res1['score']}")
    else:
        result = run(args.seed)
        print(json.dumps(result, indent=2))
