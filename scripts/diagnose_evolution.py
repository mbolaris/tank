"""Diagnose Layer 0 in-world evolution: is natural selection actually moving the
population's traits over time?

Tank World's premise is that fish evolve through natural selection inside a
single simulation (Layer 0). Generation turnover alone does not prove this -
a population can churn through generations while its mean traits stay flat
(pure drift, no selection). This tool measures the *direction and magnitude*
of trait change across a run so we can tell selection from noise.

It samples, at a fixed interval:
  - population and the maximum generation reached (turnover)
  - mean value of the heritable behavioral traits that drive foraging
  - mean speed/size modifiers and the count of unique behavior algorithms

At the end it reports, for each trait, the drift from the first to the last
sample. A consistent, non-trivial drift is direct evidence that selection (not
just reproduction) is shaping the gene pool.

Usage:
    python scripts/diagnose_evolution.py --frames 10000 --seed 42
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.getcwd())

from core.entities import Fish
from core.worlds import WorldRegistry

# Heritable behavioral traits that most directly affect survival/foraging.
BEHAVIORAL_TRAITS = (
    "pursuit_aggression",
    "prediction_skill",
    "hunting_stamina",
    "aggression",
)


def _live_fish(world) -> list[Fish]:
    return [e for e in world.entities_list if isinstance(e, Fish) and not e.is_dead()]


def _trait_means(fish_list: list[Fish]) -> dict[str, float]:
    """Mean of each tracked trait across the living population."""
    means: dict[str, float] = {}
    n = len(fish_list)
    if n == 0:
        return dict.fromkeys(BEHAVIORAL_TRAITS, 0.0) | {"speed": 0.0, "size": 0.0}

    for trait in BEHAVIORAL_TRAITS:
        total = 0.0
        count = 0
        for fish in fish_list:
            attr = getattr(fish.genome.behavioral, trait, None)
            if attr is not None and hasattr(attr, "value"):
                total += float(attr.value)
                count += 1
        means[trait] = total / count if count else 0.0

    means["speed"] = sum(f.genome.speed_modifier for f in fish_list) / n
    means["size"] = sum(f.genome.physical.size_modifier.value for f in fish_list) / n
    return means


def run(frames: int, seed: int, interval: int) -> None:
    config = {
        "headless": True,
        "screen_width": 2000,
        "screen_height": 2000,
        "max_population": 60,
        "soccer_enabled": False,
        "plants_enabled": False,
        "poker_activity_enabled": False,
        "auto_food_spawn_rate": 9,
    }

    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    samples: list[dict] = []
    print("\n" + "=" * 78)
    print("LAYER 0 EVOLUTION DIAGNOSIS")
    print("=" * 78)
    header = (
        f"{'frame':>6} {'pop':>4} {'gen':>4} {'algos':>5} "
        f"{'pursuit':>8} {'predict':>8} {'stamina':>8} {'aggr':>6} {'speed':>6}"
    )
    print(header)
    print("-" * 78)

    for i in range(frames):
        world.step()
        if (i + 1) % interval == 0:
            stats = world.get_stats(include_distributions=False)
            fish_list = _live_fish(world)
            means = _trait_means(fish_list)
            div = stats.get("diversity_stats", {})
            sample = {
                "frame": i + 1,
                "pop": stats.get("fish_count", 0),
                "gen": stats.get("max_generation", 0),
                "algos": div.get("unique_algorithms", 0),
                **means,
            }
            samples.append(sample)
            print(
                f"{sample['frame']:>6} {sample['pop']:>4} {sample['gen']:>4} "
                f"{sample['algos']:>5} {means['pursuit_aggression']:>8.3f} "
                f"{means['prediction_skill']:>8.3f} {means['hunting_stamina']:>8.3f} "
                f"{means['aggression']:>6.3f} {means['speed']:>6.3f}"
            )

    if len(samples) < 2:
        print("\nNot enough samples to assess drift.")
        return

    first, last = samples[0], samples[-1]
    print("\n" + "-" * 78)
    print("TRAIT DRIFT (first sample -> last sample)")
    print("-" * 78)
    drift_traits = list(BEHAVIORAL_TRAITS) + ["speed", "size"]
    selection_detected = False
    for trait in drift_traits:
        start_v = first.get(trait, 0.0)
        end_v = last.get(trait, 0.0)
        delta = end_v - start_v
        rel = (delta / start_v * 100.0) if start_v else 0.0
        marker = ""
        if abs(rel) >= 5.0:
            marker = "  <- selection"
            selection_detected = True
        print(
            f"  {trait:>18}: {start_v:6.3f} -> {end_v:6.3f}  ({delta:+.3f}, {rel:+5.1f}%){marker}"
        )

    print("\n" + "-" * 78)
    print("INTERPRETATION")
    print("-" * 78)
    gens = last["gen"] - first["gen"]
    print(f"  Generations advanced over window: {gens}")
    if gens <= 0:
        print("  WARNING: no generation turnover - population is not reproducing.")
    if selection_detected:
        print("  Directional selection detected: at least one trait drifted >=5%.")
        print("  Layer 0 evolution is active (selection, not just reproduction).")
    else:
        print("  Traits are roughly stable: turnover without strong directional")
        print("  selection (drift-dominated, or already near a fitness optimum).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--interval", type=int, default=1000)
    args = parser.parse_args()
    run(args.frames, args.seed, args.interval)


if __name__ == "__main__":
    main()
