#!/usr/bin/env python3
"""Compare foraging controllers on a school, where cohesion has a price.

The single-fish foraging gym cannot see half of the behavior graph: above its
urgency threshold the graph steers toward social cohesion, and one fish has no
school (see docs/IMPROVEMENT_PROPOSALS.md 12.4). This runs the same four arms
over core.foraging.school_gym, where every wave scatters one food item per
fish and food expires - so a school that stays together loses the items it
did not spread out to reach.

``--urgency-sweep`` is the measurement 12.5 needs before it spends mutation
budget on this topology: it scores the graph across candidate thresholds, so
the 0.35 default can be judged rather than assumed.

Examples::

    python tools/compare_school_arms.py
    python tools/compare_school_arms.py --urgency-sweep "0.0 0.35 0.7 1.0"
    python tools/compare_school_arms.py --arms "composable production_graph" --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.foraging.school_arms import GRAPH, SCHOOL_ARM_NAMES, SchoolComparison, compare_school_arms

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
        default=SCHOOL_ARM_NAMES,
        help=f"Arms to run (default: {' '.join(SCHOOL_ARM_NAMES)}).",
    )
    parser.add_argument(
        "--urgency-sweep",
        type=_parse_floats,
        default=None,
        help="Score the bare graph arm at each of these urgency thresholds.",
    )
    parser.add_argument("--no-pursuit-module", action="store_true")
    parser.add_argument("--json", type=Path, default=None)
    return parser


def _print_table(comparison: SchoolComparison, title: str) -> None:
    print(title)
    print(f"{'arm':>18}  {'energy/ceiling':>14}  {'neighbour px':>12}  {'stations/fish':>13}")
    for arm in comparison.arms():
        print(
            f"{arm:>18}  {comparison.mean_ratio(arm):>14.6f}  "
            f"{comparison.mean_neighbour_distance(arm):>12.1f}  "
            f"{comparison.mean_stations_visited(arm):>13.2f}"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    genome_seeds = tuple(args.genome_seeds)
    episode_seeds = tuple(args.episode_seeds)
    episodes = len(genome_seeds) * len(episode_seeds)
    payload: dict[str, object] = {}

    comparison = compare_school_arms(
        genome_seeds,
        episode_seeds,
        arms=tuple(args.arms),
        pursuit_module=not args.no_pursuit_module,
    )
    _print_table(
        comparison,
        f"School gym - {len(genome_seeds)} genomes x {len(episode_seeds)} episode seeds "
        f"= {episodes} episodes per evolvable arm\n"
        "(reference arms carry no genome and run once per episode seed)\n",
    )
    payload["comparison"] = comparison.to_dict()

    if args.urgency_sweep:
        print()
        print("Graph arm across urgency thresholds")
        print(f"{'threshold':>10}  {'energy/ceiling':>14}  {'neighbour px':>12}")
        sweep: dict[str, object] = {}
        for threshold in args.urgency_sweep:
            swept = compare_school_arms(
                genome_seeds,
                episode_seeds,
                arms=(GRAPH,),
                pursuit_module=not args.no_pursuit_module,
                urgency_threshold=threshold,
            )
            print(
                f"{threshold:>10.2f}  {swept.mean_ratio(GRAPH):>14.6f}  "
                f"{swept.mean_neighbour_distance(GRAPH):>12.1f}"
            )
            sweep[f"{threshold:g}"] = swept.to_dict()["means"]
        payload["urgency_sweep"] = sweep

    if args.json is not None:
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
