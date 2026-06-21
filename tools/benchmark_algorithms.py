"""Standalone analysis harness for the monolithic food-seeking algorithms.

Measures how well each monolithic food-seeking algorithm (from
``core/algorithms/food_seeking/``) performs as the *sole* movement controller
of every fish in a short headless tank world, compared against the composable
behavior baseline that production fish actually use.

How pinning works
-----------------
The live simulation never selects monolithic algorithms for fish movement:
fish execute their genome's ComposableBehavior (or a code-pool movement
policy).  Patching ``core.algorithms.registry.ALL_ALGORITHMS`` therefore
would not change what fish do.  Instead, this harness uses the priority-1
``Fish.movement_policy`` override (see ``core/movement_strategy.py``) to pin
every fish - including newborns - to a fresh instance of the algorithm under
test.  The same pinning mechanism is used for the ``composable_baseline``
run (each fish is pinned to its own genome ComposableBehavior), so all
candidates are compared through an identical execution path that bypasses
the ball-pursuit and code-pool-policy confounds.

This is an analysis tool only: it changes nothing about selection,
inheritance, or champion reproduction.  See
docs/adr/006-deprecate-monolithic-food-seekers.md for the decision this
harness informed.

Usage:
    python tools/benchmark_algorithms.py --out results.json
    python tools/benchmark_algorithms.py --algorithms greedy_food_seeker --seeds 42 --frames 2000

Determinism: each (algorithm, seed) run executes in a fresh worker process
with a fixed world seed and a dedicated parameter RNG, so results are exactly
reproducible run-to-run.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from multiprocessing import Pool
from typing import Any

# Frames per run. ~2000 frames is enough for starvation/reproduction dynamics
# to differentiate algorithms while keeping 45 runs under ~15 minutes.
DEFAULT_FRAMES = 2000
DEFAULT_SEEDS = (42, 43, 44)

# Pseudo-algorithm name for the production composable behavior baseline.
COMPOSABLE_BASELINE = "composable_baseline"

# World configuration, mirroring benchmarks/tank/survival_5k.py so results
# are comparable with the survival benchmark environment.
WORLD_CONFIG: dict[str, Any] = {
    "headless": True,
    "screen_width": 2000,
    "screen_height": 2000,
    "max_population": 60,
    "critical_population_threshold": 5,
    "emergency_spawn_cooldown": 90,
    "poker_activity_enabled": False,
    "plants_enabled": False,
    "auto_food_spawn_rate": 9,
    "soccer_enabled": False,
}


def _food_seeker_classes() -> dict[str, type]:
    """Map algorithm_id -> class for all monolithic food-seeking algorithms."""
    import core.algorithms.food_seeking as fs

    classes: dict[str, type] = {}
    for class_name in fs.__all__:
        algo_class = getattr(fs, class_name)
        # algorithm_id is assigned in __init__; instantiate with a throwaway
        # RNG purely to read the ID (no simulation state involved).
        instance = algo_class.random_instance(rng=random.Random(0))
        classes[instance.algorithm_id] = algo_class
    return classes


class _PinnedPolicy:
    """Adapts a behavior object with ``execute(fish)`` to a MovementPolicy."""

    def __init__(self, behavior: Any, fish: Any, policy_id: str):
        self._behavior = behavior
        self._fish = fish
        self._policy_id = policy_id

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def __call__(self, observation: dict[str, Any], rng: random.Random) -> tuple[float, float]:
        return self._behavior.execute(self._fish)  # type: ignore[no-any-return]


def _pin_fish(
    world: Any, algorithm_id: str, algo_class: type | None, param_rng: random.Random
) -> None:
    """Pin any not-yet-pinned fish (initial population and newborns).

    For monolithic algorithms each fish gets its own instance (random
    parameters drawn from ``param_rng``), matching how evolution samples
    parameter space via ``random_instance``.  For the composable baseline
    each fish is pinned to its own genome behavior.
    """
    from core.entities import Fish

    for entity in world.entities_list:
        if not isinstance(entity, Fish) or getattr(entity, "_bench_pinned", False):
            continue
        if algo_class is None:
            behavior_trait = entity.genome.behavioral.behavior
            behavior = behavior_trait.value if behavior_trait is not None else None
            if behavior is None:
                continue  # No genome behavior: leave default movement in place
        else:
            behavior = algo_class.random_instance(rng=param_rng)  # type: ignore[attr-defined]
        entity.movement_policy = _PinnedPolicy(behavior, entity, f"pinned:{algorithm_id}")
        entity._bench_pinned = True  # type: ignore[attr-defined]


def run_single(algorithm_id: str, seed: int, frames: int) -> dict[str, Any]:
    """Run one pinned simulation and return its metrics."""
    from core.entities import Fish
    from core.worlds import WorldRegistry

    algo_class: type | None
    if algorithm_id == COMPOSABLE_BASELINE:
        algo_class = None
    else:
        algo_class = _food_seeker_classes()[algorithm_id]

    start = time.time()
    config = dict(WORLD_CONFIG)
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    # Dedicated RNG for per-fish algorithm parameters (independent of the
    # world RNG so pinning does not perturb the simulation's random stream).
    param_rng = random.Random(seed)

    fish_count_sum = 0
    fish_energy_sum = 0.0  # Sum of per-frame mean fish energy
    energy_samples = 0
    min_fish_count = sys.maxsize

    for _ in range(frames):
        _pin_fish(world, algorithm_id, algo_class, param_rng)
        world.step()

        fish = [e for e in world.entities_list if isinstance(e, Fish)]
        count = len(fish)
        fish_count_sum += count
        min_fish_count = min(min_fish_count, count)
        if count > 0:
            fish_energy_sum += sum(f.energy for f in fish) / count
            energy_samples += 1

    stats = world.get_stats(include_distributions=False)
    death_causes = stats.get("death_causes", {}) or {}
    total_deaths = int(stats.get("total_deaths", 0))
    starvation_deaths = int(death_causes.get("starvation", 0))

    avg_fish_count = fish_count_sum / frames
    avg_fish_energy = fish_energy_sum / energy_samples if energy_samples else 0.0
    # Survival score: sustained population weighted by how well-fed it is.
    # Same shape as survival_5k's (avg_energy * avg_pop) but fish-only, so
    # food items lying around do not inflate the score.
    survival_score = avg_fish_count * avg_fish_energy / 100.0

    return {
        "algorithm": algorithm_id,
        "seed": seed,
        "frames": frames,
        "avg_fish_count": round(avg_fish_count, 2),
        "min_fish_count": min_fish_count,
        "final_fish_count": len([e for e in world.entities_list if isinstance(e, Fish)]),
        "avg_fish_energy": round(avg_fish_energy, 2),
        "total_births": int(stats.get("total_births", 0)),
        "total_deaths": total_deaths,
        "starvation_deaths": starvation_deaths,
        "starvation_fraction": round(starvation_deaths / total_deaths, 3) if total_deaths else 0.0,
        "survival_score": round(survival_score, 2),
        "runtime_seconds": round(time.time() - start, 1),
    }


def _run_single_star(args: tuple[str, int, int]) -> dict[str, Any]:
    return run_single(*args)


def aggregate(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate per-run metrics into per-algorithm summaries."""
    by_algo: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_algo.setdefault(run["algorithm"], []).append(run)

    summary: dict[str, dict[str, Any]] = {}
    for algo, algo_runs in by_algo.items():
        scores = [r["survival_score"] for r in algo_runs]
        summary[algo] = {
            "seeds": [r["seed"] for r in algo_runs],
            "mean_survival_score": round(statistics.mean(scores), 2),
            "stdev_survival_score": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0.0,
            "mean_avg_fish_count": round(
                statistics.mean(r["avg_fish_count"] for r in algo_runs), 2
            ),
            "mean_avg_fish_energy": round(
                statistics.mean(r["avg_fish_energy"] for r in algo_runs), 2
            ),
            "mean_total_births": round(statistics.mean(r["total_births"] for r in algo_runs), 1),
            "mean_total_deaths": round(statistics.mean(r["total_deaths"] for r in algo_runs), 1),
            "mean_starvation_fraction": round(
                statistics.mean(r["starvation_fraction"] for r in algo_runs), 3
            ),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--algorithms",
        nargs="*",
        default=None,
        help=f"Algorithm IDs to test (default: all food seekers + {COMPOSABLE_BASELINE})",
    )
    parser.add_argument("--seeds", nargs="*", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAMES)
    parser.add_argument("--jobs", type=int, default=4, help="Parallel worker processes")
    parser.add_argument("--out", default=None, help="Write results JSON to this path")
    args = parser.parse_args()

    available = list(_food_seeker_classes()) + [COMPOSABLE_BASELINE]
    algorithms = args.algorithms if args.algorithms else available
    unknown = [a for a in algorithms if a not in available]
    if unknown:
        print(f"Unknown algorithm(s): {unknown}\nAvailable: {available}", file=sys.stderr)
        return 1

    tasks = [(algo, seed, args.frames) for algo in algorithms for seed in args.seeds]
    print(
        f"Running {len(tasks)} simulations "
        f"({len(algorithms)} algorithms x {len(args.seeds)} seeds x {args.frames} frames, "
        f"{args.jobs} workers)...",
        file=sys.stderr,
    )

    start = time.time()
    if args.jobs > 1:
        # maxtasksperchild=1 gives every run a pristine process for exact
        # reproducibility (no cross-run module state).
        with Pool(processes=args.jobs, maxtasksperchild=1) as pool:
            runs = pool.map(_run_single_star, tasks)
    else:
        runs = [_run_single_star(task) for task in tasks]

    summary = aggregate(runs)
    results = {
        "config": {
            "frames": args.frames,
            "seeds": args.seeds,
            "world_config": WORLD_CONFIG,
        },
        "runs": runs,
        "summary": summary,
        "total_runtime_seconds": round(time.time() - start, 1),
    }

    # Human-readable ranking table
    ranked = sorted(summary.items(), key=lambda kv: kv[1]["mean_survival_score"], reverse=True)
    header = (
        f"{'algorithm':<28} {'score':>8} {'±sd':>7} {'fish':>6} "
        f"{'energy':>7} {'births':>7} {'deaths':>7} {'starve%':>8}"
    )
    print(header)
    print("-" * len(header))
    for algo, s in ranked:
        print(
            f"{algo:<28} {s['mean_survival_score']:>8.1f} {s['stdev_survival_score']:>7.1f} "
            f"{s['mean_avg_fish_count']:>6.1f} {s['mean_avg_fish_energy']:>7.1f} "
            f"{s['mean_total_births']:>7.1f} {s['mean_total_deaths']:>7.1f} "
            f"{s['mean_starvation_fraction'] * 100:>7.1f}%"
        )

    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
