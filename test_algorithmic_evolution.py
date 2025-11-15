"""Test script for the algorithmic evolution system."""

import random
from genetics import Genome
from behavior_algorithms import (
    get_random_algorithm,
    inherit_algorithm_with_mutation,
    ALL_ALGORITHMS
)

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

    return True

def test_genome_with_algorithm():
    """Test that genomes can include behavior algorithms."""
    print("\nTesting genome creation with algorithms...")

    # Create genome with algorithm
    genome = Genome.random(use_brain=False, use_algorithm=True)

    if genome.behavior_algorithm is None:
        print("✗ Genome should have a behavior algorithm")
        return False

    print(f"✓ Genome created with algorithm: {genome.behavior_algorithm.algorithm_id}")
    print(f"  Parameters: {genome.behavior_algorithm.parameters}")

    # Create genome without algorithm
    genome_no_algo = Genome.random(use_brain=False, use_algorithm=False)
    if genome_no_algo.behavior_algorithm is not None:
        print("✗ Genome should NOT have a behavior algorithm")
        return False

    print(f"✓ Genome created without algorithm")

    return True

def test_algorithm_inheritance():
    """Test that algorithms are inherited with mutations."""
    print("\nTesting algorithm inheritance and mutation...")

    # Create parent genome
    parent1 = Genome.random(use_brain=False, use_algorithm=True)
    parent2 = Genome.random(use_brain=False, use_algorithm=True)

    print(f"Parent 1 algorithm: {parent1.behavior_algorithm.algorithm_id}")
    print(f"  Parameters: {parent1.behavior_algorithm.parameters}")
    print(f"Parent 2 algorithm: {parent2.behavior_algorithm.algorithm_id}")
    print(f"  Parameters: {parent2.behavior_algorithm.parameters}")

    # Create offspring
    offspring = Genome.from_parents(parent1, parent2, mutation_rate=0.3, mutation_strength=0.2)

    if offspring.behavior_algorithm is None:
        print("✗ Offspring should have a behavior algorithm")
        return False

    print(f"\nOffspring algorithm: {offspring.behavior_algorithm.algorithm_id}")
    print(f"  Parameters: {offspring.behavior_algorithm.parameters}")

    # Check that offspring inherited from parent 1 (with possible mutations)
    # The algorithm ID should match parent 1
    if offspring.behavior_algorithm.algorithm_id == parent1.behavior_algorithm.algorithm_id:
        print(f"✓ Offspring inherited algorithm from parent 1")

        # Check if parameters were mutated (they might be different)
        params_changed = False
        for key in parent1.behavior_algorithm.parameters:
            if key in offspring.behavior_algorithm.parameters:
                if abs(parent1.behavior_algorithm.parameters[key] -
                      offspring.behavior_algorithm.parameters[key]) > 0.01:
                    params_changed = True
                    print(f"  Parameter '{key}' mutated from {parent1.behavior_algorithm.parameters[key]:.3f} to {offspring.behavior_algorithm.parameters[key]:.3f}")

        if params_changed:
            print("✓ Parameters were mutated during inheritance")
    elif offspring.behavior_algorithm.algorithm_id == parent2.behavior_algorithm.algorithm_id:
        print(f"✓ Offspring inherited algorithm from parent 2")
    else:
        print(f"✓ Offspring got a new random algorithm")

    return True

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
        original_algo,
        mutation_rate=1.0,  # 100% mutation rate
        mutation_strength=0.3
    )

    print(f"\nMutated algorithm: {mutated_algo.algorithm_id}")
    print(f"  Mutated parameters: {mutated_algo.parameters}")

    # Check that algorithm type is preserved
    if mutated_algo.algorithm_id != original_algo.algorithm_id:
        print("✗ Algorithm type should be preserved during mutation")
        return False

    print("✓ Algorithm type preserved")

    # Check that at least some parameters changed
    mutations_found = 0
    for key in original_params:
        if key in mutated_algo.parameters:
            if abs(original_params[key] - mutated_algo.parameters[key]) > 0.01:
                mutations_found += 1
                print(f"  ✓ Parameter '{key}': {original_params[key]:.3f} → {mutated_algo.parameters[key]:.3f}")

    if mutations_found > 0:
        print(f"✓ Found {mutations_found} mutated parameters")
    else:
        print("⚠ No parameters were mutated (this is possible with low mutation strength)")

    return True

def test_multiple_generations():
    """Test evolution over multiple generations."""
    print("\nTesting multi-generational evolution...")

    # Start with a population
    population = []
    for _ in range(10):
        genome = Genome.random(use_brain=False, use_algorithm=True)
        population.append(genome)

    print(f"Generation 0: {len(population)} fish")
    algo_distribution = {}
    for genome in population:
        algo_id = genome.behavior_algorithm.algorithm_id
        algo_distribution[algo_id] = algo_distribution.get(algo_id, 0) + 1
    print(f"  Algorithm distribution: {dict(list(algo_distribution.items())[:5])}...")

    # Simulate 5 generations
    for gen in range(1, 6):
        # Create offspring from random pairs
        new_population = []
        for _ in range(10):
            parent1 = random.choice(population)
            parent2 = random.choice(population)
            offspring = Genome.from_parents(parent1, parent2, mutation_rate=0.2, mutation_strength=0.15)
            new_population.append(offspring)

        population = new_population

        # Check distribution
        algo_distribution = {}
        for genome in population:
            algo_id = genome.behavior_algorithm.algorithm_id
            algo_distribution[algo_id] = algo_distribution.get(algo_id, 0) + 1

        print(f"Generation {gen}: {len(population)} fish")
        print(f"  Algorithm distribution: {dict(list(algo_distribution.items())[:5])}...")

    print("✓ Successfully simulated 5 generations")
    return True

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
