#!/usr/bin/env python3
"""Compare the behavior-graph controller with ComposableBehavior on the foraging gym.

This is the measurement backlog item 12.4 was written around: the graph
substrate landed behind ``tank.graph_behavior_enabled`` with no recorded
head-to-head score against the controller it would replace.

Two comparisons come out of one run:

* ``composable`` vs ``graph`` - the bare controllers, no arbiter, no fallback.
* ``production`` vs ``production_graph`` - the full movement arbiter with the
  flag off and on, i.e. what flipping ``graph_behavior_enabled`` would ship.

Read the bare ``graph`` number with care. The default foraging graph steers
toward social cohesion above its urgency threshold, and the gym has exactly
one fish, so its cohesion vector is always zero: above the threshold the graph
emits nothing and the fish drifts. ``--urgency-threshold 1.0`` pins the graph
on its food branch and is the number to quote when the question is about
foraging skill rather than about the gym's geometry.

Examples::

    python tools/compare_graph_arm.py
    python tools/compare_graph_arm.py --urgency-threshold 1.0 --arms graph
    python tools/compare_graph_arm.py --json results.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.foraging.arms import ARM_NAMES, ArmComparison, compare_arms

# Founder draws to average over. The composable behavior's foraging skill
# swings with the traits a founder happens to roll, while the default graph is
# one fixed topology for everyone, so a single genome measures the draw rather
# than the controllers.
DEFAULT_GENOME_SEEDS = (1, 2, 3, 4, 5, 6, 7, 8)

# The same episode cohort the Skill Observatory's foraging baseline uses, so
# these numbers sit on the scale the rest of the project already reads.
DEFAULT_EPISODE_SEEDS = (42, 7, 31, 38, 1, 5, 0, 41)


def _parse_seeds(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in raw.replace(",", " ").split())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--genome-seeds",
        type=_parse_seeds,
        default=DEFAULT_GENOME_SEEDS,
        help="Founder genome draws to average over (default: 1-8).",
    )
    parser.add_argument(
        "--episode-seeds",
        type=_parse_seeds,
        default=DEFAULT_EPISODE_SEEDS,
        help="Foraging-gym episode seeds (default: the observatory cohort).",
    )
    parser.add_argument(
        "--arms",
        type=lambda raw: tuple(raw.replace(",", " ").split()),
        default=ARM_NAMES,
        help=f"Arms to run (default: {' '.join(ARM_NAMES)}).",
    )
    parser.add_argument(
        "--urgency-threshold",
        type=float,
        default=None,
        help="Override the graph's urgency threshold; 1.0 pins it on food pursuit.",
    )
    parser.add_argument(
        "--no-pursuit-module",
        action="store_true",
        help="Run graph arms without the shared Target Pursuit Module.",
    )
    parser.add_argument("--json", type=Path, default=None, help="Write the full result as JSON.")
    return parser


def _per_genome_means(comparison: ArmComparison) -> dict[str, dict[int, float]]:
    """Mean ratio per (arm, genome), recovering the genome from score order.

    ``compare_arms`` emits scores arm-major then genome-major then
    episode-major, which is what lets a flat score list be regrouped here
    without threading the genome seed through ``ArmScore``.
    """
    episodes = len(comparison.episode_seeds)
    grouped: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    index = 0
    for arm in comparison.arms():
        for genome_seed in comparison.genome_seeds:
            for _ in range(episodes):
                grouped[arm][genome_seed].append(comparison.scores[index].energy_ratio)
                index += 1
    return {
        arm: {seed: statistics.mean(values) for seed, values in per_seed.items()}
        for arm, per_seed in grouped.items()
    }


def _print_report(comparison: ArmComparison, urgency_threshold: float | None) -> None:
    arms = comparison.arms()
    episodes = len(comparison.genome_seeds) * len(comparison.episode_seeds)
    print(
        f"Foraging-gym arm comparison - {len(comparison.genome_seeds)} genomes "
        f"x {len(comparison.episode_seeds)} episode seeds = {episodes} episodes per arm"
    )
    if urgency_threshold is not None:
        print(f"Graph urgency threshold overridden to {urgency_threshold}")
    print()
    print(f"{'arm':>18}  {'mean energy / oracle':>20}")
    for arm in arms:
        print(f"{arm:>18}  {comparison.mean_ratio(arm):>20.6f}")

    per_genome = _per_genome_means(comparison)
    for baseline, candidate in (("composable", "graph"), ("production", "production_graph")):
        if baseline not in per_genome or candidate not in per_genome:
            continue
        deltas = [
            per_genome[candidate][seed] - per_genome[baseline][seed]
            for seed in comparison.genome_seeds
        ]
        wins = sum(1 for delta in deltas if delta > 0)
        print()
        print(f"{candidate} vs {baseline}, per founder genome:")
        for seed, delta in zip(comparison.genome_seeds, deltas, strict=True):
            print(
                f"  genome {seed:>3}: {per_genome[baseline][seed]:.4f} -> "
                f"{per_genome[candidate][seed]:.4f}  ({delta:+.4f})"
            )
        print(f"  wins {wins}/{len(deltas)}, mean delta {statistics.mean(deltas):+.4f}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    comparison = compare_arms(
        tuple(args.genome_seeds),
        tuple(args.episode_seeds),
        arms=tuple(args.arms),
        pursuit_module=not args.no_pursuit_module,
        urgency_threshold=args.urgency_threshold,
    )
    _print_report(comparison, args.urgency_threshold)
    if args.json is not None:
        payload = comparison.to_dict()
        payload["urgency_threshold"] = args.urgency_threshold
        payload["pursuit_module"] = not args.no_pursuit_module
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
