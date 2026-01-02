"""Lightweight helpers for exercising the evolution pipeline.

These utilities intentionally avoid the full simulation stack and instead
run a quick sequence of genome crossovers and mutations. The goal is to
provide a fun, low-friction way to observe evolutionary drift without
needing rendering or the full game loop.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from core.genetics import Genome


def _summarize_population(population: Sequence[Genome]) -> dict[str, float]:
    """Calculate simple metrics for a population snapshot."""
    speeds = [g.speed_modifier for g in population]
    aggression = [g.behavioral.aggression.value for g in population]
    metabolism = [g.metabolism_rate for g in population]

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values)

    def _stdev(values: list[float]) -> float:
        mu = _mean(values)
        return math.sqrt(sum((v - mu) ** 2 for v in values) / len(values))

    return {
        "speed_min": min(speeds),
        "speed_max": max(speeds),
        "speed_mean": _mean(speeds),
        "speed_spread": max(speeds) - min(speeds),
        "speed_stdev": _stdev(speeds),
        "aggression_mean": _mean(aggression),
        "metabolism_mean": _mean(metabolism),
    }


def run_evolution_smoke_test(
    seed: int = 7,
    population_size: int = 12,
    generations: int = 6,
) -> dict[str, object]:
    """Run a playful evolution loop over a handful of generations.

    Returns a report dictionary that can be rendered for humans or asserted
    against in tests.
    """
    rng = random.Random(seed)
    population = [Genome.random(use_algorithm=False, rng=rng) for _ in range(population_size)]
    generation_reports: list[dict[str, float]] = []

    for gen in range(generations):
        snapshot = _summarize_population(population)
        snapshot["generation"] = gen
        generation_reports.append(snapshot)

        next_population: list[Genome] = []
        for _ in range(population_size):
            parent1, parent2 = rng.sample(population, 2)
            child = Genome.from_parents(parent1, parent2, rng=rng)
            next_population.append(child)
        population = next_population

    final_snapshot = _summarize_population(population)
    champions = sorted(population, key=lambda g: g.speed_modifier, reverse=True)[:3]
    champion_speeds = [round(c.speed_modifier, 3) for c in champions]

    return {
        "seed": seed,
        "population_size": population_size,
        "generations": generation_reports,
        "final_population_stats": final_snapshot,
        "champion_speeds": champion_speeds,
    }


def format_report(report: dict[str, object]) -> str:
    """Create a friendly multi-line string showing evolutionary drift."""
    lines = [
        "🚀 Evolution smoke test",
        f"Seed: {report['seed']} | Population: {report['population_size']}",
        "",
        "Gen | speed μ  | spread | σ      | aggression μ",
        "----+---------+--------+--------+--------------",
    ]

    for gen_snapshot in report["generations"]:
        lines.append(
            f"{gen_snapshot['generation']:>3} | "
            f"{gen_snapshot['speed_mean']:.3f} | "
            f"{gen_snapshot['speed_spread']:.3f} | "
            f"{gen_snapshot['speed_stdev']:.3f} | "
            f"{gen_snapshot['aggression_mean']:.3f}"
        )

    lines.extend(
        [
            "",
            "Top speeds in final generation: " + ", ".join(map(str, report["champion_speeds"])),
            "(Higher spreads imply more evolutionary diversity across runs)",
        ]
    )
    return "\n".join(lines)
