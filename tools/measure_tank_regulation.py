#!/usr/bin/env python3
"""Report what a tank benchmark holds constant while one config key is swept.

The tank's death mix is dominated by starvation - 86-97% of `survival_5k`
deaths across sampled seeds - and the reflex reading is that food-seeking is
failing. Before tuning foraging, it is worth knowing whether the quantity being
tuned is free to move at all: `max_population` caps the fish count, and
`FoodSpawningSystem._calculate_spawn_rate` is a closed loop on total fish
energy, so both terms of the `survival_5k` score are under regulation.

This sweeps a world-config key and prints the steady state at each value, with
raw energy (which the food controller reads and regulates) kept apart from
banked reproduction energy (which it does not).

Example:
    python tools/measure_tank_regulation.py benchmarks/tank/survival_5k.py \
        --key auto_food_spawn_rate --values 2,3,9,18,36 --seeds 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.research.regulation import sweep_world_config
from tools.ablate_world_config import _parse_value
from tools.non_ai_baseline import parse_seeds
from tools.run_bench import load_benchmark_module

_COLUMNS = (
    ("population", "pop"),
    ("raw_energy", "raw_E"),
    ("raw_energy_per_fish", "raw_E/fish"),
    ("banked_energy", "banked_E"),
    ("food_stock", "food"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark_path")
    parser.add_argument("--key", required=True, help="World-config key to sweep")
    parser.add_argument("--values", required=True, help="Comma-separated values for the key")
    parser.add_argument("--seeds", default="42")
    parser.add_argument("--frames", type=int, help="Override the benchmark's frame count")
    parser.add_argument("--out", help="Write the sweep to JSON")
    args = parser.parse_args()

    benchmark = load_benchmark_module(args.benchmark_path)
    if args.key not in benchmark.WORLD_CONFIG:
        # Sweeping a key the benchmark never pins compares against an engine
        # default the reader may not expect, so say so rather than imply the
        # benchmark chose it.
        print(
            f"note: {args.key!r} is not set in {benchmark.BENCHMARK_ID}'s WORLD_CONFIG; "
            "its unswept behaviour comes from the engine default.",
            file=sys.stderr,
        )

    values: list[object] = [_parse_value(v.strip()) for v in args.values.split(",") if v.strip()]
    sweep = sweep_world_config(
        benchmark,
        args.key,
        values,
        parse_seeds(args.seeds),
        **({"frames": args.frames} if args.frames else {}),
    )

    header = f"{args.key:>22} {'seed':>6}" + "".join(f"{label:>12}" for _, label in _COLUMNS)
    print(header)
    print("-" * len(header))
    for point in sweep.points:
        row = f"{point.value!s:>22} {point.seed:>6}"
        for field, _ in _COLUMNS:
            row += f"{float(getattr(point.steady, field)):>12.1f}"
        print(row)

    print(f"\nswept {args.key} over a {sweep.input_spread():.1f}x range; steady-state spread:")
    for field, label in _COLUMNS:
        print(f"    {label:>12}  {sweep.field_spread(field):.3f}x")
    drifts = [abs(p.steady.drift) for p in sweep.points]
    print(f"\nlargest within-window drift in raw energy: {max(drifts, default=0.0):.1%}")

    if args.out:
        Path(args.out).write_text(json.dumps(sweep.as_dict(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
