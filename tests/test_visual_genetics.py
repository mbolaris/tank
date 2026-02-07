#!/usr/bin/env python3
"""Test script to verify visual genetics inheritance"""

import random

from core.config.fish import (BODY_ASPECT_MAX, BODY_ASPECT_MIN, EYE_SIZE_MAX,
                              EYE_SIZE_MIN, FISH_PATTERN_COUNT,
                              FISH_TEMPLATE_COUNT)
from core.genetics import Genome


def test_visual_traits():
    """Test that visual traits are properly initialized and inherited"""
    rng = random.Random(42)  # Deterministic seed

    print("=" * 60)
    print("Testing Visual Genetics System")
    print("=" * 60)

    # Test 1: Random genome generation
    print("\n1. Testing random genome generation:")
    genome1 = Genome.random(use_algorithm=False, rng=rng)
    phys1 = genome1.physical

    print(f"   Template ID: {phys1.template_id.value} (should be 0-{FISH_TEMPLATE_COUNT - 1})")
    print(f"   Fin Size: {phys1.fin_size.value:.2f} (should be 0.5-2.0)")
    print(f"   Tail Size: {phys1.tail_size.value:.2f} (should be 0.5-2.0)")
    print(
        f"   Body Aspect: {phys1.body_aspect.value:.2f} (should be {BODY_ASPECT_MIN}-{BODY_ASPECT_MAX})"
    )
    print(f"   Eye Size: {phys1.eye_size.value:.2f} (should be {EYE_SIZE_MIN}-{EYE_SIZE_MAX})")
    print(f"   Pattern Intensity: {phys1.pattern_intensity.value:.2f} (should be 0.0-1.0)")
    print(f"   Pattern Type: {phys1.pattern_type.value} (should be 0-{FISH_PATTERN_COUNT - 1})")
    print(f"   Color Hue: {phys1.color_hue.value:.2f} (should be 0.0-1.0)")

    # Validate ranges
    assert 0 <= phys1.template_id.value <= FISH_TEMPLATE_COUNT - 1, "template_id out of range"
    assert 0.5 <= phys1.fin_size.value <= 2.0, "fin_size out of range"
    assert 0.5 <= phys1.tail_size.value <= 2.0, "tail_size out of range"
    assert BODY_ASPECT_MIN <= phys1.body_aspect.value <= BODY_ASPECT_MAX, "body_aspect out of range"
    assert EYE_SIZE_MIN <= phys1.eye_size.value <= EYE_SIZE_MAX, "eye_size out of range"
    assert 0.0 <= phys1.pattern_intensity.value <= 1.0, "pattern_intensity out of range"
    assert 0 <= phys1.pattern_type.value <= FISH_PATTERN_COUNT - 1, "pattern_type out of range"

    print("   ✓ All visual traits within valid ranges")

    # Test 2: Create another random genome for breeding
    print("\n2. Testing inheritance from two parents:")
    genome2 = Genome.random(use_algorithm=False, rng=rng)
    phys2 = genome2.physical

    print("\n   Parent 1:")
    print(
        f"      Template: {phys1.template_id.value}, Fin: {phys1.fin_size.value:.2f}, Tail: {phys1.tail_size.value:.2f}"
    )
    print(f"      Body Aspect: {phys1.body_aspect.value:.2f}, Eye: {phys1.eye_size.value:.2f}")
    print(
        f"      Pattern: Type {phys1.pattern_type.value}, Intensity {phys1.pattern_intensity.value:.2f}"
    )

    print("\n   Parent 2:")
    print(
        f"      Template: {phys2.template_id.value}, Fin: {phys2.fin_size.value:.2f}, Tail: {phys2.tail_size.value:.2f}"
    )
    print(f"      Body Aspect: {phys2.body_aspect.value:.2f}, Eye: {phys2.eye_size.value:.2f}")
    print(
        f"      Pattern: Type {phys2.pattern_type.value}, Intensity {phys2.pattern_intensity.value:.2f}"
    )

    # Test 3: Create offspring
    offspring = Genome.from_parents(
        genome1, genome2, mutation_rate=0.1, mutation_strength=0.1, rng=rng
    )

    print("\n   Offspring:")
    offspring_phys = offspring.physical
    print(
        f"      Template: {offspring_phys.template_id.value}, "
        f"Fin: {offspring_phys.fin_size.value:.2f}, Tail: {offspring_phys.tail_size.value:.2f}"
    )
    print(
        f"      Body Aspect: {offspring_phys.body_aspect.value:.2f}, "
        f"Eye: {offspring_phys.eye_size.value:.2f}"
    )
    print(
        f"      Pattern: Type {offspring_phys.pattern_type.value}, "
        f"Intensity {offspring_phys.pattern_intensity.value:.2f}"
    )

    # Validate offspring ranges
    assert (
        0 <= offspring_phys.template_id.value <= FISH_TEMPLATE_COUNT - 1
    ), "offspring template_id out of range"
    assert 0.5 <= offspring_phys.fin_size.value <= 2.0, "offspring fin_size out of range"
    assert 0.5 <= offspring_phys.tail_size.value <= 2.0, "offspring tail_size out of range"
    assert (
        BODY_ASPECT_MIN <= offspring_phys.body_aspect.value <= BODY_ASPECT_MAX
    ), "offspring body_aspect out of range"
    assert (
        EYE_SIZE_MIN <= offspring_phys.eye_size.value <= EYE_SIZE_MAX
    ), "offspring eye_size out of range"
    assert (
        0.0 <= offspring_phys.pattern_intensity.value <= 1.0
    ), "offspring pattern_intensity out of range"
    assert (
        0 <= offspring_phys.pattern_type.value <= FISH_PATTERN_COUNT - 1
    ), "offspring pattern_type out of range"

    print("\n   ✓ Offspring visual traits within valid ranges")

    # Test 4: Multiple generations
    print("\n3. Testing multi-generational inheritance:")

    current_gen = [genome1, genome2]
    for gen in range(1, 4):
        next_gen = []
        for i in range(3):
            parent1 = current_gen[i % len(current_gen)]
            parent2 = current_gen[(i + 1) % len(current_gen)]
            child = Genome.from_parents(parent1, parent2, mutation_rate=0.15, rng=rng)
            next_gen.append(child)

        print(f"   Generation {gen}: {len(next_gen)} offspring created")
        print(f"      Templates: {[child.physical.template_id.value for child in next_gen]}")
        print(f"      Fin sizes: {[f'{child.physical.fin_size.value:.2f}' for child in next_gen]}")
        print(f"      Pattern types: {[child.physical.pattern_type.value for child in next_gen]}")

        # Validate all offspring
        for child in next_gen:
            assert 0 <= child.physical.template_id.value <= FISH_TEMPLATE_COUNT - 1
            assert 0.5 <= child.physical.fin_size.value <= 2.0
            assert 0 <= child.physical.pattern_type.value <= FISH_PATTERN_COUNT - 1

        current_gen = next_gen

    print("\n   ✓ Multi-generational inheritance successful")

    # Test 5: Higher mutation rates
    print("\n4. Testing with higher mutation rates:")

    stressed_offspring = Genome.from_parents(
        genome1,
        genome2,
        mutation_rate=0.2,
        mutation_strength=0.2,
        rng=rng,
    )

    stressed_phys = stressed_offspring.physical
    print("   Stressed offspring:")
    print(f"      Template: {stressed_phys.template_id.value}")
    print(
        f"      Fin: {stressed_phys.fin_size.value:.2f}, Tail: {stressed_phys.tail_size.value:.2f}"
    )
    print(
        f"      Pattern: Type {stressed_phys.pattern_type.value}, "
        f"Intensity {stressed_phys.pattern_intensity.value:.2f}"
    )

    print("\n   ✓ Higher-rate mutations applied successfully")

    print("\n" + "=" * 60)
    print("✓ ALL VISUAL GENETICS TESTS PASSED")
    print("=" * 60)
    print("\nThe parametric fish template system is working correctly!")
    print("Visual traits are properly inherited and mutated across generations.")
    print("\nYou can now run the simulation to see diverse fish evolving!")
    print("=" * 60)


if __name__ == "__main__":
    test_visual_traits()
