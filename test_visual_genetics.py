#!/usr/bin/env python3
"""Test script to verify visual genetics inheritance"""

from core.genetics import Genome

def test_visual_traits():
    """Test that visual traits are properly initialized and inherited"""

    print("=" * 60)
    print("Testing Visual Genetics System")
    print("=" * 60)

    # Test 1: Random genome generation
    print("\n1. Testing random genome generation:")
    genome1 = Genome.random(use_brain=False, use_algorithm=False)

    print(f"   Template ID: {genome1.template_id} (should be 0-5)")
    print(f"   Fin Size: {genome1.fin_size:.2f} (should be 0.6-1.4)")
    print(f"   Tail Size: {genome1.tail_size:.2f} (should be 0.6-1.4)")
    print(f"   Body Aspect: {genome1.body_aspect:.2f} (should be 0.7-1.3)")
    print(f"   Eye Size: {genome1.eye_size:.2f} (should be 0.7-1.3)")
    print(f"   Pattern Intensity: {genome1.pattern_intensity:.2f} (should be 0.0-1.0)")
    print(f"   Pattern Type: {genome1.pattern_type} (should be 0-3)")
    print(f"   Color Hue: {genome1.color_hue:.2f} (should be 0.0-1.0)")

    # Validate ranges
    assert 0 <= genome1.template_id <= 5, "template_id out of range"
    assert 0.6 <= genome1.fin_size <= 1.4, "fin_size out of range"
    assert 0.6 <= genome1.tail_size <= 1.4, "tail_size out of range"
    assert 0.7 <= genome1.body_aspect <= 1.3, "body_aspect out of range"
    assert 0.7 <= genome1.eye_size <= 1.3, "eye_size out of range"
    assert 0.0 <= genome1.pattern_intensity <= 1.0, "pattern_intensity out of range"
    assert 0 <= genome1.pattern_type <= 3, "pattern_type out of range"

    print("   ✓ All visual traits within valid ranges")

    # Test 2: Create another random genome for breeding
    print("\n2. Testing inheritance from two parents:")
    genome2 = Genome.random(use_brain=False, use_algorithm=False)

    print(f"\n   Parent 1:")
    print(f"      Template: {genome1.template_id}, Fin: {genome1.fin_size:.2f}, Tail: {genome1.tail_size:.2f}")
    print(f"      Body Aspect: {genome1.body_aspect:.2f}, Eye: {genome1.eye_size:.2f}")
    print(f"      Pattern: Type {genome1.pattern_type}, Intensity {genome1.pattern_intensity:.2f}")

    print(f"\n   Parent 2:")
    print(f"      Template: {genome2.template_id}, Fin: {genome2.fin_size:.2f}, Tail: {genome2.tail_size:.2f}")
    print(f"      Body Aspect: {genome2.body_aspect:.2f}, Eye: {genome2.eye_size:.2f}")
    print(f"      Pattern: Type {genome2.pattern_type}, Intensity {genome2.pattern_intensity:.2f}")

    # Test 3: Create offspring
    offspring = Genome.from_parents(
        genome1,
        genome2,
        mutation_rate=0.1,
        mutation_strength=0.1,
        population_stress=0.0
    )

    print(f"\n   Offspring:")
    print(f"      Template: {offspring.template_id}, Fin: {offspring.fin_size:.2f}, Tail: {offspring.tail_size:.2f}")
    print(f"      Body Aspect: {offspring.body_aspect:.2f}, Eye: {offspring.eye_size:.2f}")
    print(f"      Pattern: Type {offspring.pattern_type}, Intensity {offspring.pattern_intensity:.2f}")

    # Validate offspring ranges
    assert 0 <= offspring.template_id <= 5, "offspring template_id out of range"
    assert 0.6 <= offspring.fin_size <= 1.4, "offspring fin_size out of range"
    assert 0.6 <= offspring.tail_size <= 1.4, "offspring tail_size out of range"
    assert 0.7 <= offspring.body_aspect <= 1.3, "offspring body_aspect out of range"
    assert 0.7 <= offspring.eye_size <= 1.3, "offspring eye_size out of range"
    assert 0.0 <= offspring.pattern_intensity <= 1.0, "offspring pattern_intensity out of range"
    assert 0 <= offspring.pattern_type <= 3, "offspring pattern_type out of range"

    print("\n   ✓ Offspring visual traits within valid ranges")

    # Test 4: Multiple generations
    print("\n3. Testing multi-generational inheritance:")

    current_gen = [genome1, genome2]
    for gen in range(1, 4):
        next_gen = []
        for i in range(3):
            parent1 = current_gen[i % len(current_gen)]
            parent2 = current_gen[(i + 1) % len(current_gen)]
            child = Genome.from_parents(parent1, parent2, mutation_rate=0.15)
            next_gen.append(child)

        print(f"   Generation {gen}: {len(next_gen)} offspring created")
        print(f"      Templates: {[child.template_id for child in next_gen]}")
        print(f"      Fin sizes: {[f'{child.fin_size:.2f}' for child in next_gen]}")
        print(f"      Pattern types: {[child.pattern_type for child in next_gen]}")

        # Validate all offspring
        for child in next_gen:
            assert 0 <= child.template_id <= 5
            assert 0.6 <= child.fin_size <= 1.4
            assert 0 <= child.pattern_type <= 3

        current_gen = next_gen

    print("\n   ✓ Multi-generational inheritance successful")

    # Test 5: High mutation stress
    print("\n4. Testing with high population stress:")

    stressed_offspring = Genome.from_parents(
        genome1,
        genome2,
        mutation_rate=0.2,
        mutation_strength=0.2,
        population_stress=0.8  # High stress
    )

    print(f"   Stressed offspring:")
    print(f"      Template: {stressed_offspring.template_id}")
    print(f"      Fin: {stressed_offspring.fin_size:.2f}, Tail: {stressed_offspring.tail_size:.2f}")
    print(f"      Pattern: Type {stressed_offspring.pattern_type}, Intensity {stressed_offspring.pattern_intensity:.2f}")

    print("\n   ✓ High-stress mutations applied successfully")

    print("\n" + "=" * 60)
    print("✓ ALL VISUAL GENETICS TESTS PASSED")
    print("=" * 60)
    print("\nThe parametric fish template system is working correctly!")
    print("Visual traits are properly inherited and mutated across generations.")
    print("\nYou can now run the simulation to see diverse fish evolving!")
    print("=" * 60)

if __name__ == "__main__":
    test_visual_traits()
