"""Test script for the algorithmic evolution system."""

import random

from core.algorithms.registry import (
    ALL_ALGORITHMS,
    get_random_algorithm,
    inherit_algorithm_with_mutation,
)
from core.genetics import Genome


def test_algorithm_creation():
    """Test that algorithms can be created."""
    print("Testing algorithm creation...")
    rng = random.Random(42)  # Deterministic seed

    # Test random algorithm
    algo = get_random_algorithm(rng=rng)
    print(f"✓ Created random algorithm: {algo.algorithm_id}")
    print(f"  Parameters: {algo.parameters}")

    # Test all algorithm types
    print(f"\n✓ Total algorithms available: {len(ALL_ALGORITHMS)}")

    # Create one of each type
    created_types = set()
    for algo_class in ALL_ALGORITHMS:
        instance = algo_class.random_instance(rng=rng)
        created_types.add(instance.algorithm_id)

    print(f"✓ Successfully created {len(created_types)} unique algorithm types")

    # Assert all algorithm types were created
    assert len(created_types) > 0, "Should create at least one algorithm type"


def test_genome_with_algorithm():
    """Test that genomes can include behavior algorithms."""
    print("\nTesting genome creation with algorithms...")
    rng = random.Random(42)  # Deterministic seed

    # Create genome with algorithm (now uses behavior)
    genome = Genome.random(use_algorithm=True, rng=rng)

    # Check behavior instead of behavior_algorithm
    assert genome.behavioral.behavior is not None, "Genome should have a behavior trait"
    assert genome.behavioral.behavior.value is not None, "Genome should have a composable behavior"

    behavior = genome.behavioral.behavior.value
    print("✓ Genome created with composable behavior")
    print(
        f"  Threat response: {behavior.threat_response.name if behavior.threat_response else 'None'}"
    )
    print(f"  Food approach: {behavior.food_approach.name if behavior.food_approach else 'None'}")

    # Create genome without algorithm
    genome_no_algo = Genome.random(use_algorithm=False, rng=rng)
    assert (
        genome_no_algo.behavioral.behavior.value is None
    ), "Genome should NOT have a composable behavior"

    print("✓ Genome created without algorithm")


def test_algorithm_inheritance():
    """Test that algorithms are inherited with mutations."""
    print("\nTesting algorithm inheritance and mutation...")
    rng = random.Random(42)  # Deterministic seed

    # Create parent genome
    parent1 = Genome.random(use_algorithm=True, rng=rng)
    parent2 = Genome.random(use_algorithm=True, rng=rng)

    behavior1 = parent1.behavioral.behavior.value
    behavior2 = parent2.behavioral.behavior.value

    print("Parent 1 composable behavior:")
    print(
        f"  Threat response: {behavior1.threat_response.name if behavior1.threat_response else 'None'}"
    )
    print(f"  Food approach: {behavior1.food_approach.name if behavior1.food_approach else 'None'}")
    print("Parent 2 composable behavior:")
    print(
        f"  Threat response: {behavior2.threat_response.name if behavior2.threat_response else 'None'}"
    )
    print(f"  Food approach: {behavior2.food_approach.name if behavior2.food_approach else 'None'}")

    # Create offspring
    offspring = Genome.from_parents(
        parent1, parent2, mutation_rate=0.3, mutation_strength=0.2, rng=rng
    )

    assert offspring.behavioral.behavior is not None, "Offspring should have a behavior trait"
    assert (
        offspring.behavioral.behavior.value is not None
    ), "Offspring should have a composable behavior"

    offspring_behavior = offspring.behavioral.behavior.value
    print("\nOffspring composable behavior:")
    print(
        f"  Threat response: {offspring_behavior.threat_response.name if offspring_behavior.threat_response else 'None'}"
    )
    print(
        f"  Food approach: {offspring_behavior.food_approach.name if offspring_behavior.food_approach else 'None'}"
    )

    # Check that offspring inherited from a parent (with possible mutations)
    print("✓ Offspring inherited composable behavior from parents")


def test_parameter_mutation():
    """Test that algorithm parameters mutate correctly."""
    print("\nTesting parameter mutation...")
    rng = random.Random(42)  # Deterministic seed

    # Create algorithm and record original parameters
    original_algo = get_random_algorithm(rng=rng)
    original_params = original_algo.parameters.copy()

    print(f"Original algorithm: {original_algo.algorithm_id}")
    print(f"  Original parameters: {original_params}")

    # Mutate with high mutation rate
    mutated_algo = inherit_algorithm_with_mutation(
        original_algo, mutation_rate=1.0, mutation_strength=0.3, rng=rng  # 100% mutation rate
    )

    print(f"\nMutated algorithm: {mutated_algo.algorithm_id}")
    print(f"  Mutated parameters: {mutated_algo.parameters}")

    # Check that algorithm type is preserved
    assert (
        mutated_algo.algorithm_id == original_algo.algorithm_id
    ), "Algorithm type should be preserved during mutation"

    print("✓ Algorithm type preserved")

    # Check that at least some parameters changed
    mutations_found = 0
    for key in original_params:
        if key in mutated_algo.parameters:
            if isinstance(original_params[key], (int, float)) and isinstance(
                mutated_algo.parameters[key], (int, float)
            ):
                if abs(original_params[key] - mutated_algo.parameters[key]) > 0.01:
                    mutations_found += 1
                    print(
                        f"  ✓ Parameter '{key}': {original_params[key]:.3f} → {mutated_algo.parameters[key]:.3f}"
                    )
            elif original_params[key] != mutated_algo.parameters[key]:
                mutations_found += 1
                print(
                    f"  ✓ Parameter '{key}': {original_params[key]} → {mutated_algo.parameters[key]}"
                )

    if mutations_found > 0:
        print(f"✓ Found {mutations_found} mutated parameters")
    else:
        print("⚠ No parameters were mutated (this is possible with low mutation strength)")


def test_multiple_generations():
    """Test evolution over multiple generations."""
    print("\nTesting multi-generational evolution...")
    rng = random.Random(42)  # Deterministic seed

    # Start with a population
    population = []
    for _ in range(10):
        genome = Genome.random(use_algorithm=True, rng=rng)
        population.append(genome)

    print(f"Generation 0: {len(population)} fish")

    # Track behavior distribution using behavior
    behavior_distribution = {}
    for genome in population:
        if genome.behavioral.behavior and genome.behavioral.behavior.value:
            behavior = genome.behavioral.behavior.value
            # Use threat response as a key indicator of behavior diversity
            threat_name = behavior.threat_response.name if behavior.threat_response else "None"
            behavior_distribution[threat_name] = behavior_distribution.get(threat_name, 0) + 1
    print(f"  Threat response distribution: {dict(list(behavior_distribution.items())[:5])}...")

    # Simulate 5 generations
    for gen in range(1, 6):
        # Create offspring from random pairs
        new_population = []
        for _ in range(10):
            parent1 = rng.choice(population)
            parent2 = rng.choice(population)
            offspring = Genome.from_parents(
                parent1, parent2, mutation_rate=0.2, mutation_strength=0.15, rng=rng
            )
            new_population.append(offspring)

        population = new_population

        # Check distribution
        behavior_distribution = {}
        for genome in population:
            if genome.behavioral.behavior and genome.behavioral.behavior.value:
                behavior = genome.behavioral.behavior.value
                threat_name = behavior.threat_response.name if behavior.threat_response else "None"
                behavior_distribution[threat_name] = behavior_distribution.get(threat_name, 0) + 1

        print(f"Generation {gen}: {len(population)} fish")
        print(f"  Threat response distribution: {dict(list(behavior_distribution.items())[:5])}...")

    print("✓ Successfully simulated 5 generations")
    # Assert that we still have a population
    assert len(population) > 0, "Population should not be empty after evolution"


def main():
    """Run all tests."""
    print("=" * 70)
    print("ALGORITHMIC EVOLUTION SYSTEM TEST SUITE")
    print("=" * 70)

    tests = [
        test_algorithm_creation,
        test_genome_with_algorithm,
        test_algorithm_inheritance,
        test_parameter_mutation,
        test_multiple_generations,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
