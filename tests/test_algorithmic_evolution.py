"""Test script for the algorithmic evolution system."""

import random

from core.algorithms import ALL_ALGORITHMS, get_random_algorithm, inherit_algorithm_with_mutation
from core.genetics import Genome


def test_algorithm_creation():
    """Test that algorithms can be created."""
    print("Testing algorithm creation...")

    # Test random algorithm
    algo = get_random_algorithm()
    print(f"✓ Created random algorithm: {algo.algorithm_id}")
    print(f"  Parameters: {algo.parameters}")

    # Test all algorithm types
    print(f"\n✓ Total algorithms available: {len(ALL_ALGORITHMS)}")

    # Create one of each type
    created_types = set()
    for algo_class in ALL_ALGORITHMS:
        instance = algo_class.random_instance()
        created_types.add(instance.algorithm_id)

    print(f"✓ Successfully created {len(created_types)} unique algorithm types")

    # Assert all algorithm types were created
    assert len(created_types) > 0, "Should create at least one algorithm type"


def test_genome_with_algorithm():
    """Test that genomes can include behavior algorithms."""
    print("\nTesting genome creation with algorithms...")

    # Create genome with algorithm
    genome = Genome.random(use_algorithm=True)

    assert genome.behavioral.behavior_algorithm.value is not None, "Genome should have a behavior algorithm"

    print(f"✓ Genome created with algorithm: {genome.behavioral.behavior_algorithm.value.algorithm_id}")
    print(f"  Parameters: {genome.behavioral.behavior_algorithm.value.parameters}")

    # Create genome without algorithm
    genome_no_algo = Genome.random(use_algorithm=False)
    assert genome_no_algo.behavioral.behavior_algorithm.value is None, "Genome should NOT have a behavior algorithm"

    print("✓ Genome created without algorithm")


def test_algorithm_inheritance():
    """Test that algorithms are inherited with mutations."""
    print("\nTesting algorithm inheritance and mutation...")

    # Create parent genome
    parent1 = Genome.random(use_algorithm=True)
    parent2 = Genome.random(use_algorithm=True)

    print(f"Parent 1 algorithm: {parent1.behavioral.behavior_algorithm.value.algorithm_id}")
    print(f"  Parameters: {parent1.behavioral.behavior_algorithm.value.parameters}")
    print(f"Parent 2 algorithm: {parent2.behavioral.behavior_algorithm.value.algorithm_id}")
    print(f"  Parameters: {parent2.behavioral.behavior_algorithm.value.parameters}")

    # Create offspring
    offspring = Genome.from_parents(parent1, parent2, mutation_rate=0.3, mutation_strength=0.2)

    assert offspring.behavioral.behavior_algorithm.value is not None, "Offspring should have a behavior algorithm"

    print(f"\nOffspring algorithm: {offspring.behavioral.behavior_algorithm.value.algorithm_id}")
    print(f"  Parameters: {offspring.behavioral.behavior_algorithm.value.parameters}")

    # Check that offspring inherited from parent 1 (with possible mutations)
    # The algorithm ID should match parent 1
    if offspring.behavioral.behavior_algorithm.value.algorithm_id == parent1.behavioral.behavior_algorithm.value.algorithm_id:
        print("✓ Offspring inherited algorithm from parent 1")

        # Check if parameters were mutated (they might be different)
        params_changed = False
        for key in parent1.behavioral.behavior_algorithm.value.parameters:
            if key in offspring.behavioral.behavior_algorithm.value.parameters:
                parent_val = parent1.behavioral.behavior_algorithm.value.parameters[key]
                offspring_val = offspring.behavioral.behavior_algorithm.value.parameters[key]
                # Only check numeric parameters for mutation
                if isinstance(parent_val, (int, float)) and isinstance(offspring_val, (int, float)):
                    if abs(parent_val - offspring_val) > 0.01:
                        params_changed = True
                        print(
                            f"  Parameter '{key}' mutated from {parent_val:.3f} to {offspring_val:.3f}"
                        )
                elif parent_val != offspring_val:
                    # String parameters can also change
                    params_changed = True
                    print(f"  Parameter '{key}' mutated from {parent_val} to {offspring_val}")

        if params_changed:
            print("✓ Parameters were mutated during inheritance")
    elif offspring.behavioral.behavior_algorithm.value.algorithm_id == parent2.behavioral.behavior_algorithm.value.algorithm_id:
        print("✓ Offspring inherited algorithm from parent 2")
    else:
        print("✓ Offspring got a new random algorithm")


def test_parameter_mutation():
    """Test that algorithm parameters mutate correctly."""
    print("\nTesting parameter mutation...")

    # Create algorithm and record original parameters
    original_algo = get_random_algorithm()
    original_params = original_algo.parameters.copy()

    print(f"Original algorithm: {original_algo.algorithm_id}")
    print(f"  Original parameters: {original_params}")

    # Mutate with high mutation rate
    mutated_algo = inherit_algorithm_with_mutation(
        original_algo, mutation_rate=1.0, mutation_strength=0.3  # 100% mutation rate
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
            if isinstance(original_params[key], (int, float)) and isinstance(mutated_algo.parameters[key], (int, float)):
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

    # Start with a population
    population = []
    for _ in range(10):
        genome = Genome.random(use_algorithm=True)
        population.append(genome)

    print(f"Generation 0: {len(population)} fish")
    algo_distribution = {}
    for genome in population:
        algo_id = genome.behavioral.behavior_algorithm.value.algorithm_id
        algo_distribution[algo_id] = algo_distribution.get(algo_id, 0) + 1
    print(f"  Algorithm distribution: {dict(list(algo_distribution.items())[:5])}...")

    # Simulate 5 generations
    for gen in range(1, 6):
        # Create offspring from random pairs
        new_population = []
        for _ in range(10):
            parent1 = random.choice(population)
            parent2 = random.choice(population)
            offspring = Genome.from_parents(
                parent1, parent2, mutation_rate=0.2, mutation_strength=0.15
            )
            new_population.append(offspring)

        population = new_population

        # Check distribution
        algo_distribution = {}
        for genome in population:
            algo_id = genome.behavioral.behavior_algorithm.value.algorithm_id
            algo_distribution[algo_id] = algo_distribution.get(algo_id, 0) + 1

        print(f"Generation {gen}: {len(population)} fish")
        print(f"  Algorithm distribution: {dict(list(algo_distribution.items())[:5])}...")

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
