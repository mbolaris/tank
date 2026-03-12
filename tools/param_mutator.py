"""Parameter mutation engine for composable behavior evolution.

Operates on two parameter spaces:
1. SUB_BEHAVIOR_PARAMS (composable): 28 continuous params shared across all composable behaviors
2. ALGORITHM_PARAMETER_BOUNDS (per-algorithm): 2-5 params per algorithm class

Mutations are gaussian perturbations clamped to defined bounds.
All operations are deterministic given a seed.
"""

import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.algorithms.base import ALGORITHM_PARAMETER_BOUNDS
from core.algorithms.composable.definitions import SUB_BEHAVIOR_PARAMS


@dataclass
class Mutation:
    """Record of a single parameter mutation."""

    target: str  # "composable" or algorithm_id like "greedy_food_seeker"
    param: str
    old_value: float
    new_value: float
    bounds: tuple[float, float]


@dataclass
class MutationPlan:
    """A set of mutations to apply to the codebase."""

    seed: int
    generation: int
    mutations: list[Mutation] = field(default_factory=list)
    strategy: str = "gaussian"

    def summary(self) -> str:
        lines = [f"MutationPlan(gen={self.generation}, seed={self.seed}, n={len(self.mutations)})"]
        for m in self.mutations:
            pct = ((m.new_value - m.old_value) / max(abs(m.old_value), 1e-9)) * 100
            lines.append(
                f"  {m.target}.{m.param}: {m.old_value:.4f} -> {m.new_value:.4f} ({pct:+.1f}%)"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "generation": self.generation,
            "strategy": self.strategy,
            "mutations": [
                {
                    "target": m.target,
                    "param": m.param,
                    "old_value": m.old_value,
                    "new_value": m.new_value,
                    "bounds": list(m.bounds),
                }
                for m in self.mutations
            ],
        }


def _gaussian_mutate(
    value: float,
    low: float,
    high: float,
    strength: float,
    rng: random.Random,
) -> float:
    """Apply gaussian perturbation to a value, clamped to bounds.

    Args:
        value: Current parameter value
        low: Lower bound
        high: Upper bound
        strength: Mutation strength as fraction of parameter range (0.0-1.0)
        rng: Random number generator

    Returns:
        Mutated value within [low, high]
    """
    param_range = high - low
    sigma = param_range * strength
    delta = rng.gauss(0, sigma)
    new_value = value + delta
    return max(low, min(high, new_value))


def mutate_composable_params(
    current_params: dict[str, float] | None = None,
    mutation_rate: float = 0.3,
    mutation_strength: float = 0.15,
    seed: int = 42,
    generation: int = 0,
) -> MutationPlan:
    """Generate mutations for SUB_BEHAVIOR_PARAMS (composable behavior system).

    Args:
        current_params: Current parameter values (defaults to midpoints)
        mutation_rate: Probability each parameter mutates (0.0-1.0)
        mutation_strength: Gaussian sigma as fraction of param range
        seed: RNG seed for reproducibility
        generation: Generation counter for tracking

    Returns:
        MutationPlan with list of mutations to apply
    """
    rng = random.Random(seed)

    if current_params is None:
        current_params = {key: (low + high) / 2 for key, (low, high) in SUB_BEHAVIOR_PARAMS.items()}

    plan = MutationPlan(seed=seed, generation=generation, strategy="gaussian_composable")

    for param_name, (low, high) in SUB_BEHAVIOR_PARAMS.items():
        if rng.random() >= mutation_rate:
            continue

        old_val = current_params.get(param_name, (low + high) / 2)
        new_val = _gaussian_mutate(old_val, low, high, mutation_strength, rng)

        if abs(new_val - old_val) > 1e-9:
            plan.mutations.append(
                Mutation(
                    target="composable",
                    param=param_name,
                    old_value=old_val,
                    new_value=new_val,
                    bounds=(low, high),
                )
            )

    return plan


def mutate_algorithm_params(
    algorithm_id: str,
    current_params: dict[str, float] | None = None,
    mutation_rate: float = 0.5,
    mutation_strength: float = 0.15,
    seed: int = 42,
    generation: int = 0,
) -> MutationPlan:
    """Generate mutations for a specific algorithm's parameters.

    Args:
        algorithm_id: Algorithm identifier (e.g. "greedy_food_seeker")
        current_params: Current values (defaults to midpoints)
        mutation_rate: Per-parameter mutation probability
        mutation_strength: Gaussian sigma as fraction of range
        seed: RNG seed
        generation: Generation counter

    Returns:
        MutationPlan with mutations for this algorithm
    """
    bounds = ALGORITHM_PARAMETER_BOUNDS.get(algorithm_id)
    if bounds is None:
        raise ValueError(
            f"Unknown algorithm: {algorithm_id}. "
            f"Known: {sorted(ALGORITHM_PARAMETER_BOUNDS.keys())}"
        )

    rng = random.Random(seed)

    if current_params is None:
        current_params = {key: (lo + hi) / 2 for key, (lo, hi) in bounds.items()}

    plan = MutationPlan(seed=seed, generation=generation, strategy=f"gaussian_{algorithm_id}")

    for param_name, (low, high) in bounds.items():
        if rng.random() >= mutation_rate:
            continue

        old_val = current_params.get(param_name, (low + high) / 2)
        new_val = _gaussian_mutate(old_val, low, high, mutation_strength, rng)

        if abs(new_val - old_val) > 1e-9:
            plan.mutations.append(
                Mutation(
                    target=algorithm_id,
                    param=param_name,
                    old_value=old_val,
                    new_value=new_val,
                    bounds=(low, high),
                )
            )

    return plan


def mutate_all_algorithms(
    n_algorithms: int = 3,
    mutation_rate: float = 0.5,
    mutation_strength: float = 0.15,
    seed: int = 42,
    generation: int = 0,
) -> MutationPlan:
    """Select N random algorithms and mutate their parameters.

    Args:
        n_algorithms: How many algorithms to mutate
        mutation_rate: Per-parameter mutation probability
        mutation_strength: Gaussian sigma as fraction of range
        seed: RNG seed
        generation: Generation counter

    Returns:
        Combined MutationPlan across selected algorithms
    """
    rng = random.Random(seed)
    all_algo_ids = sorted(ALGORITHM_PARAMETER_BOUNDS.keys())
    selected = rng.sample(all_algo_ids, min(n_algorithms, len(all_algo_ids)))

    combined = MutationPlan(seed=seed, generation=generation, strategy="gaussian_multi_algo")

    for algo_id in selected:
        # Use a derived seed per algorithm for independence
        algo_seed = rng.randint(0, 2**31)
        plan = mutate_algorithm_params(
            algo_id,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            seed=algo_seed,
            generation=generation,
        )
        combined.mutations.extend(plan.mutations)

    return combined


def apply_mutations_to_definitions(plan: MutationPlan) -> dict[str, tuple[float, float]]:
    """Apply composable mutations and return new SUB_BEHAVIOR_PARAMS bounds.

    This shifts the *default values* (midpoints) of parameters by adjusting bounds
    symmetrically. The bounds themselves stay the same width but shift toward the
    mutated value, keeping the new value as the midpoint.

    Actually, for composable params, the right approach is to change the default
    initialization values rather than the bounds. We return a dict of param -> new_default.
    """
    composable_mutations = [m for m in plan.mutations if m.target == "composable"]
    new_defaults: dict[str, float] = {}
    for m in composable_mutations:
        new_defaults[m.param] = m.new_value
    return new_defaults


def apply_mutations_to_algorithm_bounds(
    plan: MutationPlan,
) -> dict[str, dict[str, tuple[float, float]]]:
    """Apply algorithm mutations by shifting bounds to center on new values.

    For each mutated parameter, adjusts the bounds so the new value becomes
    the midpoint while keeping the same range width. The bounds are then
    intersected with the original bounds to stay valid.

    Returns:
        Dict of algorithm_id -> {param -> (new_low, new_high)}
    """
    algo_mutations: dict[str, list[Mutation]] = {}
    for m in plan.mutations:
        if m.target == "composable":
            continue
        algo_mutations.setdefault(m.target, []).append(m)

    result: dict[str, dict[str, tuple[float, float]]] = {}
    for algo_id, mutations in algo_mutations.items():
        new_bounds: dict[str, tuple[float, float]] = {}
        for m in mutations:
            orig_lo, orig_hi = m.bounds
            half_range = (orig_hi - orig_lo) / 2
            # Shift bounds to center on new value
            new_lo = max(orig_lo, m.new_value - half_range)
            new_hi = min(orig_hi, m.new_value + half_range)
            new_bounds[m.param] = (round(new_lo, 6), round(new_hi, 6))
        result[algo_id] = new_bounds

    return result


if __name__ == "__main__":
    # Demo: show what a mutation plan looks like
    import argparse

    parser = argparse.ArgumentParser(description="Generate parameter mutations")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rate", type=float, default=0.3, help="Mutation rate")
    parser.add_argument("--strength", type=float, default=0.15, help="Mutation strength")
    parser.add_argument(
        "--target",
        default="composable",
        help="Target: 'composable', 'all', or algorithm_id",
    )
    args = parser.parse_args()

    if args.target == "composable":
        plan = mutate_composable_params(
            mutation_rate=args.rate, mutation_strength=args.strength, seed=args.seed
        )
    elif args.target == "all":
        plan = mutate_all_algorithms(
            mutation_rate=args.rate, mutation_strength=args.strength, seed=args.seed
        )
    else:
        plan = mutate_algorithm_params(
            args.target, mutation_rate=args.rate, mutation_strength=args.strength, seed=args.seed
        )

    print(plan.summary())
    print()
    print(json.dumps(plan.to_dict(), indent=2))
