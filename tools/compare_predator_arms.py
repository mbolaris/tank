#!/usr/bin/env python3
"""Compare foraging controllers under predation, to price cohesion in survival.

core.foraging.school_gym showed the behavior graph's social-cohesion branch is
a monotonic *foraging* cost, and said what it could not test: no predator. This
runs the same four arms over core.foraging.predator_gym, where food spawns
inside a patrolling crab's lane, fish burn energy every frame, and the tank's
own attack cooldown means a tight school can dilute a strike.

Read --urgency-sweep against the school gym's. There, every step away from
cohesion improved the score. If cohesion is protective it must lean the other
way here; if it leans the same way, cohesion has no constituency in this tank.

Examples::

    python tools/compare_predator_arms.py
    python tools/compare_predator_arms.py --urgency-sweep "0.0 0.35 0.7 1.0"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.foraging.predator_arms import (
    GRAPH,
    PREDATOR_ARM_NAMES,
    PredatorComparison,
    compare_predator_arms,
)

DEFAULT_GENOME_SEEDS = (1, 2, 3, 4, 5, 6, 7, 8)
DEFAULT_EPISODE_SEEDS = (42, 7, 31, 38, 1, 5, 0, 41)


def _parse_ints(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in raw.replace(",", " ").split())


def _parse_floats(raw: str) -> tuple[float, ...]:
    return tuple(float(part) for part in raw.replace(",", " ").split())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--genome-seeds", type=_parse_ints, default=DEFAULT_GENOME_SEEDS)
    parser.add_argument("--episode-seeds", type=_parse_ints, default=DEFAULT_EPISODE_SEEDS)
    parser.add_argument(
        "--arms",
        type=lambda raw: tuple(raw.replace(",", " ").split()),
        default=PREDATOR_ARM_NAMES,
    )
    parser.add_argument("--urgency-sweep", type=_parse_floats, default=None)
    parser.add_argument("--no-pursuit-module", action="store_true")
    parser.add_argument("--json", type=Path, default=None)
    return parser


def _print_table(comparison: PredatorComparison) -> None:
    print(f"{'arm':>24}  {'survival':>9}  {'eaten':>6}  {'starved':>8}  {'neighbour px':>12}")
    for arm in comparison.arms():
        print(
            f"{arm:>24}  {comparison.mean_survival(arm):>9.4f}  "
            f"{comparison.mean_predation_deaths(arm):>6.2f}  "
            f"{comparison.mean_starvation_deaths(arm):>8.2f}  "
            f"{comparison.mean_neighbour_distance(arm):>12.1f}"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    genome_seeds = tuple(args.genome_seeds)
    episode_seeds = tuple(args.episode_seeds)
    payload: dict[str, object] = {}

    comparison = compare_predator_arms(
        genome_seeds,
        episode_seeds,
        arms=tuple(args.arms),
        pursuit_module=not args.no_pursuit_module,
    )
    print(
        f"Predator gym - {len(genome_seeds)} genomes x {len(episode_seeds)} episode seeds "
        f"= {len(genome_seeds) * len(episode_seeds)} episodes per evolvable arm"
    )
    print("(deaths are per 4-fish school; reference arms carry no genome)\n")
    _print_table(comparison)
    payload["comparison"] = comparison.to_dict()

    if args.urgency_sweep:
        print()
        print("Graph arm across urgency thresholds")
        print(f"{'threshold':>10}  {'survival':>9}  {'eaten':>6}  {'starved':>8}  {'nbr px':>8}")
        sweep: dict[str, object] = {}
        for threshold in args.urgency_sweep:
            swept = compare_predator_arms(
                genome_seeds,
                episode_seeds,
                arms=(GRAPH,),
                pursuit_module=not args.no_pursuit_module,
                urgency_threshold=threshold,
            )
            print(
                f"{threshold:>10.2f}  {swept.mean_survival(GRAPH):>9.4f}  "
                f"{swept.mean_predation_deaths(GRAPH):>6.2f}  "
                f"{swept.mean_starvation_deaths(GRAPH):>8.2f}  "
                f"{swept.mean_neighbour_distance(GRAPH):>8.1f}"
            )
            sweep[f"{threshold:g}"] = {
                "survival": swept.mean_survival(GRAPH),
                "deaths_predation": swept.mean_predation_deaths(GRAPH),
                "deaths_starvation": swept.mean_starvation_deaths(GRAPH),
                "mean_neighbour_distance": swept.mean_neighbour_distance(GRAPH),
            }
        payload["urgency_sweep"] = sweep

    if args.json is not None:
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
