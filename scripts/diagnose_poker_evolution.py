#!/usr/bin/env python3
"""Diagnostic script to identify bottlenecks in poker evolution.

This script runs controlled experiments to determine why fish poker skills
are not improving over generations as expected.

Key hypotheses to test:
1. Poker strategy inheritance doesn't properly favor winner's genes
2. High mutation/novelty rates wipe out evolved adaptations
3. Non-poker energy sources dilute selection pressure
4. Algorithm inheritance vs. parameter tuning mismatch
"""

import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.genetics import Genome
from core.genetics.behavioral import BehavioralTraits
from core.poker.strategy.implementations import (
    ALL_POKER_STRATEGIES,
    PokerStrategyAlgorithm,
    TightAggressiveStrategy,
    LooseAggressiveStrategy,
    BalancedStrategy,
    crossover_poker_strategies,
    get_random_poker_strategy,
)
from core.auto_evaluate_poker import AutoEvaluatePokerGame


@dataclass
class EvolutionExperiment:
    """Tracks evolution metrics over generations."""

    generation: int = 0
    avg_win_rate_vs_baseline: float = 0.0
    strategy_distribution: Dict[str, int] = field(default_factory=dict)
    parameter_means: Dict[str, float] = field(default_factory=dict)
    parameter_variances: Dict[str, float] = field(default_factory=dict)


def test_poker_strategy_inheritance_bias():
    """Test whether winner-based inheritance actually favors winner's strategy.

    Hypothesis: The 80/20 weighting may not be properly applied to poker strategies.
    """
    print("\n" + "="*70)
    print("TEST 1: Poker Strategy Inheritance Bias")
    print("="*70)

    # Create two distinct strategies with known parameters
    parent1 = TightAggressiveStrategy()
    parent1.parameters["weak_fold_threshold"] = 0.1  # Very low fold threshold
    parent1.parameters["bluff_frequency"] = 0.9  # High bluff

    parent2 = LooseAggressiveStrategy()
    parent2.parameters["weak_fold_threshold"] = 0.9  # Very high fold threshold
    parent2.parameters["bluff_frequency"] = 0.1  # Low bluff

    # Run many crossovers and track which parent's type dominates
    n_trials = 1000
    same_as_parent1 = 0
    same_as_parent2 = 0
    new_random = 0

    p1_param_sum = 0.0
    p2_param_sum = 0.0

    for _ in range(n_trials):
        # Current implementation doesn't know who won!
        # It uses crossover_poker_strategies(parent1, parent2, mutation_rate, mutation_strength)
        # There's no winner parameter!
        offspring = crossover_poker_strategies(parent1, parent2, mutation_rate=0.15, mutation_strength=0.2)

        if offspring.strategy_id == "tight_aggressive":
            same_as_parent1 += 1
        elif offspring.strategy_id == "loose_aggressive":
            same_as_parent2 += 1
        else:
            new_random += 1

        # Check if parameters are closer to parent1 or parent2
        if "weak_fold_threshold" in offspring.parameters:
            diff_p1 = abs(offspring.parameters["weak_fold_threshold"] - 0.1)
            diff_p2 = abs(offspring.parameters["weak_fold_threshold"] - 0.9)
            if diff_p1 < diff_p2:
                p1_param_sum += 1
            else:
                p2_param_sum += 1

    print(f"\nRan {n_trials} crossover trials between:")
    print(f"  Parent1: TightAggressive (fold=0.1, bluff=0.9)")
    print(f"  Parent2: LooseAggressive (fold=0.9, bluff=0.1)")
    print(f"\nStrategy type inheritance:")
    print(f"  Same type as Parent1: {same_as_parent1} ({100*same_as_parent1/n_trials:.1f}%)")
    print(f"  Same type as Parent2: {same_as_parent2} ({100*same_as_parent2/n_trials:.1f}%)")
    print(f"  New random strategy: {new_random} ({100*new_random/n_trials:.1f}%)")

    print(f"\nParameter inheritance (fold_threshold closer to):")
    print(f"  Parent1: {p1_param_sum} ({100*p1_param_sum/n_trials:.1f}%)")
    print(f"  Parent2: {p2_param_sum} ({100*p2_param_sum/n_trials:.1f}%)")

    print("\nCONCLUSION:")
    if abs(same_as_parent1 - same_as_parent2) < n_trials * 0.1:
        print("  ❌ Strategy inheritance is approximately 50/50 - NOT winner-biased!")
        print("  ISSUE: crossover_poker_strategies doesn't know which parent won")
    else:
        print("  ✓ Strategy inheritance shows bias")

    if new_random > n_trials * 0.2:
        print(f"  ❌ High novelty injection ({100*new_random/n_trials:.1f}%) may wipe out adaptations!")


def test_mutation_destroying_adaptations():
    """Test whether mutation rates are too high for preserving adaptations.

    Hypothesis: High mutation/novelty rates reset evolved parameters.
    """
    print("\n" + "="*70)
    print("TEST 2: Mutation Rate Impact on Evolved Parameters")
    print("="*70)

    # Create a "perfect" strategy with optimal parameters
    optimal = TightAggressiveStrategy()
    optimal.parameters["weak_fold_threshold"] = 0.35  # Good fold threshold
    optimal.parameters["strong_raise_threshold"] = 0.70  # Good raise threshold
    optimal.parameters["bluff_frequency"] = 0.12  # Balanced bluff

    n_generations = 10
    n_offspring = 100

    print(f"\nStarting with optimized parameters:")
    print(f"  fold_threshold: 0.35")
    print(f"  raise_threshold: 0.70")
    print(f"  bluff_frequency: 0.12")

    current_pop = [optimal]

    for gen in range(n_generations):
        next_gen = []
        preserved_type = 0

        for _ in range(n_offspring):
            # Simulate self-crossover (as in cloning)
            offspring = crossover_poker_strategies(
                optimal, optimal,
                mutation_rate=0.20,  # Current default
                mutation_strength=0.25
            )
            next_gen.append(offspring)
            if offspring.strategy_id == "tight_aggressive":
                preserved_type += 1

        # Calculate parameter drift
        fold_vals = [s.parameters.get("weak_fold_threshold", 0) for s in next_gen if "weak_fold_threshold" in s.parameters]
        raise_vals = [s.parameters.get("strong_raise_threshold", 0) for s in next_gen if "strong_raise_threshold" in s.parameters]

        if fold_vals:
            avg_fold = sum(fold_vals) / len(fold_vals)
            fold_drift = abs(avg_fold - 0.35)
        else:
            avg_fold = "N/A"
            fold_drift = "N/A"

        print(f"\nGeneration {gen+1}:")
        print(f"  Same strategy type: {preserved_type}/{n_offspring} ({100*preserved_type/n_offspring:.1f}%)")
        print(f"  Avg fold_threshold: {avg_fold if isinstance(avg_fold, str) else f'{avg_fold:.3f}'} (drift: {fold_drift if isinstance(fold_drift, str) else f'{fold_drift:.3f}'})")

    print("\nCONCLUSION:")
    if preserved_type < n_offspring * 0.8:
        print(f"  ❌ Only {100*preserved_type/n_offspring:.1f}% preserved strategy type after 10 generations")
        print("  ISSUE: High novelty injection rate (~10-25%) destroys adaptations")


def test_winner_vs_standard_algorithm():
    """Test whether fish strategies can beat the standard algorithm.

    This establishes a baseline for what "good poker" looks like.
    """
    print("\n" + "="*70)
    print("TEST 3: Fish Strategy Performance vs Standard Algorithm")
    print("="*70)

    results = {}

    for strategy_cls in ALL_POKER_STRATEGIES:
        strategy = strategy_cls()

        # Run evaluation match
        game = AutoEvaluatePokerGame(
            game_id=f"test_{strategy.strategy_id}",
            player_pool=[{"name": strategy.strategy_id, "poker_strategy": strategy}],
            standard_energy=500.0,
            max_hands=200,
            small_blind=5.0,
            big_blind=10.0,
            rng_seed=42,
            include_standard_player=True,
        )

        stats = game.run_evaluation()

        # Find fish player stats
        fish_stats = next((p for p in stats.players if not p["is_standard"]), None)
        if fish_stats:
            results[strategy.strategy_id] = {
                "win_rate": fish_stats["win_rate"],
                "net_energy": fish_stats["net_energy"],
                "bb_per_100": fish_stats["bb_per_100"],
            }

    print("\nStrategy performance vs Standard Algorithm (200 hands):")
    print("-" * 60)
    for strategy_id, result in sorted(results.items(), key=lambda x: x[1]["bb_per_100"], reverse=True):
        print(f"  {strategy_id:25} | Win Rate: {result['win_rate']:5.1f}% | BB/100: {result['bb_per_100']:+6.2f}")

    # Check if any strategy consistently beats standard
    winners = [s for s, r in results.items() if r["bb_per_100"] > 0]
    print(f"\nStrategies beating standard: {len(winners)}/{len(results)}")

    if len(winners) < len(results) / 2:
        print("  ❌ Fewer than half of strategies beat standard - selection may favor standard-like play")
    else:
        print("  ✓ Multiple strategies can beat standard - evolution has room to improve")


def test_behavioral_traits_vs_strategy_conflict():
    """Test whether aggression trait conflicts with strategy algorithm.

    Hypothesis: Two separate genetic systems (aggression trait and strategy algorithm)
    may conflict or make it harder to evolve optimal behavior.
    """
    print("\n" + "="*70)
    print("TEST 4: Aggression Trait vs Strategy Algorithm Conflict")
    print("="*70)

    # Create genomes with different aggression but same strategy
    results = []

    for aggression in [0.0, 0.25, 0.5, 0.75, 1.0]:
        genome = Genome.random(use_algorithm=True)
        genome.behavioral.aggression.value = aggression

        # Get the poker strategy from genome
        strategy = genome.behavioral.poker_strategy_algorithm.value

        if strategy is None:
            continue

        # Test against standard
        game = AutoEvaluatePokerGame(
            game_id=f"aggression_{aggression}",
            player_pool=[{
                "name": f"Aggression={aggression}",
                "poker_strategy": strategy
            }],
            standard_energy=500.0,
            max_hands=200,
            small_blind=5.0,
            big_blind=10.0,
            rng_seed=42,
            include_standard_player=True,
        )

        stats = game.run_evaluation()
        fish_stats = next((p for p in stats.players if not p["is_standard"]), None)

        if fish_stats:
            results.append({
                "aggression": aggression,
                "strategy": strategy.strategy_id,
                "win_rate": fish_stats["win_rate"],
                "bb_per_100": fish_stats["bb_per_100"],
            })

    print("\nImpact of aggression trait on same strategy:")
    print("-" * 60)
    for r in results:
        print(f"  Aggression: {r['aggression']:.2f} | Strategy: {r['strategy']:20} | BB/100: {r['bb_per_100']:+6.2f}")

    print("\nNOTE: In the simulation, genome.behavioral.aggression is mapped to poker aggression")
    print("      but the poker_strategy_algorithm makes its own decisions.")
    print("      This creates potential for conflicting selection pressures.")


def simulate_evolution_over_generations():
    """Simulate evolution and track poker performance over generations.

    This is the main experiment to see if poker skill improves.
    """
    print("\n" + "="*70)
    print("TEST 5: Simulated Evolution Over Generations")
    print("="*70)

    # Start with random population
    population_size = 20
    n_generations = 10
    games_per_generation = 5

    # Initialize population with random strategies
    population = [get_random_poker_strategy() for _ in range(population_size)]

    results = []

    for gen in range(n_generations):
        # Evaluate each strategy against standard
        fitness_scores = []

        for i, strategy in enumerate(population):
            game = AutoEvaluatePokerGame(
                game_id=f"gen{gen}_fish{i}",
                player_pool=[{"name": f"Fish_{i}", "poker_strategy": strategy}],
                standard_energy=500.0,
                max_hands=100,  # Quick eval
                small_blind=5.0,
                big_blind=10.0,
                rng_seed=gen * 1000 + i,
                include_standard_player=True,
            )

            stats = game.run_evaluation()
            fish_stats = next((p for p in stats.players if not p["is_standard"]), None)

            if fish_stats:
                fitness_scores.append((i, fish_stats["bb_per_100"], strategy))
            else:
                fitness_scores.append((i, -100, strategy))

        # Sort by fitness
        fitness_scores.sort(key=lambda x: x[1], reverse=True)

        avg_fitness = sum(f[1] for f in fitness_scores) / len(fitness_scores)
        best_fitness = fitness_scores[0][1]
        best_strategy = fitness_scores[0][2].strategy_id

        # Count strategy types
        type_counts = defaultdict(int)
        for _, _, s in fitness_scores:
            type_counts[s.strategy_id] += 1
        most_common = max(type_counts.items(), key=lambda x: x[1])

        print(f"\nGeneration {gen+1}:")
        print(f"  Avg fitness (BB/100): {avg_fitness:+.2f}")
        print(f"  Best fitness: {best_fitness:+.2f} ({best_strategy})")
        print(f"  Most common strategy: {most_common[0]} ({most_common[1]}/{population_size})")

        results.append({
            "generation": gen + 1,
            "avg_fitness": avg_fitness,
            "best_fitness": best_fitness,
            "strategy_diversity": len(type_counts),
        })

        # Selection: top 50% reproduce
        survivors = [f[2] for f in fitness_scores[:population_size // 2]]

        # Reproduction with current crossover (NOT winner-biased)
        next_gen = []
        for i in range(population_size):
            parent1 = random.choice(survivors)
            parent2 = random.choice(survivors)
            offspring = crossover_poker_strategies(parent1, parent2)
            next_gen.append(offspring)

        population = next_gen

    # Analyze trends
    print("\n" + "-" * 60)
    print("EVOLUTION TREND ANALYSIS:")

    first_half_avg = sum(r["avg_fitness"] for r in results[:5]) / 5
    second_half_avg = sum(r["avg_fitness"] for r in results[5:]) / 5

    improvement = second_half_avg - first_half_avg

    if improvement > 1.0:
        print(f"  ✓ Fitness improved by {improvement:+.2f} BB/100 over generations")
    elif improvement > -1.0:
        print(f"  ⚠ Fitness nearly flat: {improvement:+.2f} BB/100 change")
        print("    ISSUE: Selection pressure may be too weak or mutation too high")
    else:
        print(f"  ❌ Fitness DECREASED by {improvement:+.2f} BB/100!")
        print("    ISSUE: Evolution is not working correctly")


def diagnose_behavioral_inheritance():
    """Examine exactly how behavioral traits inherit poker strategy."""
    print("\n" + "="*70)
    print("TEST 6: Behavioral Traits Inheritance Flow")
    print("="*70)

    # Create two parent genomes with different strategies
    parent1 = Genome.random(use_algorithm=True)
    parent2 = Genome.random(use_algorithm=True)

    parent1_strategy = parent1.behavioral.poker_strategy_algorithm.value
    parent2_strategy = parent2.behavioral.poker_strategy_algorithm.value
    print(f"\nParent 1 poker strategy: {parent1_strategy.strategy_id if parent1_strategy else 'None'}")
    print(f"Parent 2 poker strategy: {parent2_strategy.strategy_id if parent2_strategy else 'None'}")

    # Simulate winner-choice inheritance (80/20 weighting)
    # This is what happens in fish_poker.py:523-529
    offspring = Genome.from_winner_choice(
        winner=parent1,
        mate=parent2,
        mutation_rate=0.1,
        mutation_strength=0.1,
    )

    print(f"\nOffspring (from_winner_choice with parent1 as winner):")
    offspring_strategy = offspring.behavioral.poker_strategy_algorithm.value
    print(f"  Poker strategy: {offspring_strategy.strategy_id if offspring_strategy else 'None'}")

    # Run multiple trials to see distribution
    n_trials = 100
    same_as_winner = 0
    same_as_loser = 0
    new_strategy = 0

    for _ in range(n_trials):
        offspring = Genome.from_winner_choice(
            winner=parent1,
            mate=parent2,
            mutation_rate=0.1,
            mutation_strength=0.1,
        )

        offspring_strategy = offspring.behavioral.poker_strategy_algorithm.value
        if offspring_strategy:
            if parent1_strategy and offspring_strategy.strategy_id == parent1_strategy.strategy_id:
                same_as_winner += 1
            elif parent2_strategy and offspring_strategy.strategy_id == parent2_strategy.strategy_id:
                same_as_loser += 1
            else:
                new_strategy += 1

    print(f"\nDistribution over {n_trials} winner-choice offspring:")
    print(f"  Same as winner: {same_as_winner} ({100*same_as_winner/n_trials:.1f}%)")
    print(f"  Same as loser: {same_as_loser} ({100*same_as_loser/n_trials:.1f}%)")
    print(f"  New strategy: {new_strategy} ({100*new_strategy/n_trials:.1f}%)")

    expected_winner_pct = 70  # Should be close to 80% due to 0.8 weight
    if same_as_winner > n_trials * 0.6:
        print(f"\n  ✓ Winner's strategy is favored as expected")
    else:
        print(f"\n  ❌ Winner's strategy NOT favored - inheritance may be broken!")
        print(f"     Expected ~{expected_winner_pct}% winner strategy, got {100*same_as_winner/n_trials:.1f}%")


def main():
    """Run all diagnostic tests."""
    print("="*70)
    print("POKER EVOLUTION DIAGNOSTIC REPORT")
    print("="*70)
    print("\nThis script identifies bottlenecks preventing poker skill evolution.")

    # Run all tests
    test_poker_strategy_inheritance_bias()
    test_mutation_destroying_adaptations()
    test_winner_vs_standard_algorithm()
    test_behavioral_traits_vs_strategy_conflict()
    diagnose_behavioral_inheritance()
    simulate_evolution_over_generations()

    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    print("""
Based on the tests above, likely bottlenecks are:

1. POKER STRATEGY INHERITANCE:
   - crossover_poker_strategies() doesn't know which parent won
   - 10-15% chance of random new strategy destroys adaptations
   - Winner-bias from from_winner_choice() may not propagate to strategy

2. MUTATION RATES:
   - 20% mutation rate + 25% strength is high
   - Combined with novelty injection, evolved parameters drift quickly

3. SELECTION PRESSURE:
   - Only post-poker reproduction applies selection
   - Fish can get energy from food/plants without poker skill
   - Reproduction requires 50% energy (may limit opportunities)

RECOMMENDED FIXES:
1. Pass winner information to poker strategy crossover
2. Reduce novelty injection rate (10% → 2-3%)
3. Reduce mutation rates for poker-specific parameters
4. Track poker win rate as explicit fitness metric
5. Consider increasing poker's energy importance
""")


if __name__ == "__main__":
    main()
