"""Property-based tests for genetic trait system invariants.

These tests systematically verify that critical invariants hold under all
conditions, catching edge cases that specific scenario tests might miss.

Key invariants tested:
- Traits always stay within spec bounds after random generation
- Traits always stay within spec bounds after inheritance
- Serialization round-trips preserve trait values exactly
- Meta-mutation keeps parameters within valid ranges
"""

import random

import pytest

from core.genetics import (BehavioralTraits, GeneticTrait, Genome,
                           PhysicalTraits)
from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
from core.genetics.physical import PHYSICAL_TRAIT_SPECS
from core.genetics.trait import (META_MUTATION_RATE_MAX,
                                 META_MUTATION_RATE_MIN,
                                 META_MUTATION_STRENGTH_MAX,
                                 META_MUTATION_STRENGTH_MIN)


class TestTraitBoundsInvariants:
    """Tests that verify traits always stay within their declared bounds."""

    @pytest.mark.parametrize("seed", range(100))
    def test_physical_traits_random_in_bounds(self, seed: int) -> None:
        """All random physical traits must be within TraitSpec bounds."""
        rng = random.Random(seed)
        traits = PhysicalTraits.random(rng)

        for spec in PHYSICAL_TRAIT_SPECS:
            trait = getattr(traits, spec.name)
            assert spec.min_val <= trait.value <= spec.max_val, (
                f"Seed {seed}: {spec.name}={trait.value} "
                f"not in [{spec.min_val}, {spec.max_val}]"
            )

    @pytest.mark.parametrize("seed", range(100))
    def test_behavioral_traits_random_in_bounds(self, seed: int) -> None:
        """All random behavioral traits must be within TraitSpec bounds."""
        rng = random.Random(seed)
        traits = BehavioralTraits.random(rng, use_algorithm=False)

        for spec in BEHAVIORAL_TRAIT_SPECS:
            trait = getattr(traits, spec.name)
            assert spec.min_val <= trait.value <= spec.max_val, (
                f"Seed {seed}: {spec.name}={trait.value} "
                f"not in [{spec.min_val}, {spec.max_val}]"
            )

    @pytest.mark.parametrize("seed", range(50))
    def test_physical_inheritance_preserves_bounds(self, seed: int) -> None:
        """Offspring physical traits must always be within bounds after inheritance."""
        rng = random.Random(seed)
        parent1 = PhysicalTraits.random(rng)
        parent2 = PhysicalTraits.random(rng)

        # Use high mutation to stress-test bounds clamping
        child = PhysicalTraits.from_parents(
            parent1, parent2, rng=rng, mutation_rate=0.5, mutation_strength=0.5
        )

        for spec in PHYSICAL_TRAIT_SPECS:
            trait = getattr(child, spec.name)
            assert spec.min_val <= trait.value <= spec.max_val, (
                f"Seed {seed}: child {spec.name}={trait.value} "
                f"not in [{spec.min_val}, {spec.max_val}]"
            )

    @pytest.mark.parametrize("seed", range(50))
    def test_behavioral_inheritance_preserves_bounds(self, seed: int) -> None:
        """Offspring behavioral traits must always be within bounds after inheritance."""
        rng = random.Random(seed)
        parent1 = BehavioralTraits.random(rng, use_algorithm=False)
        parent2 = BehavioralTraits.random(rng, use_algorithm=False)

        child = BehavioralTraits.from_parents(
            parent1, parent2, rng=rng, mutation_rate=0.5, mutation_strength=0.5
        )

        for spec in BEHAVIORAL_TRAIT_SPECS:
            trait = getattr(child, spec.name)
            assert spec.min_val <= trait.value <= spec.max_val, (
                f"Seed {seed}: child {spec.name}={trait.value} "
                f"not in [{spec.min_val}, {spec.max_val}]"
            )


@pytest.mark.slow
class TestMetaMutationInvariants:
    """Tests that verify meta-mutation keeps parameters within valid ranges."""

    @pytest.mark.parametrize("seed", range(100))
    def test_meta_mutation_bounds(self, seed: int) -> None:
        """Meta-mutation must keep parameters within valid ranges."""
        rng = random.Random(seed)
        trait = GeneticTrait(1.0, mutation_rate=1.0, mutation_strength=1.0, hgt_probability=0.5)

        # Apply many mutations to stress-test bounds
        for _ in range(1000):
            trait.mutate_meta(rng)

        assert (
            META_MUTATION_RATE_MIN <= trait.mutation_rate <= META_MUTATION_RATE_MAX
        ), f"mutation_rate {trait.mutation_rate} out of bounds"
        assert (
            META_MUTATION_STRENGTH_MIN <= trait.mutation_strength <= META_MUTATION_STRENGTH_MAX
        ), f"mutation_strength {trait.mutation_strength} out of bounds"
        assert (
            0.0 <= trait.hgt_probability <= 1.0
        ), f"hgt_probability {trait.hgt_probability} out of bounds"


class TestSerializationInvariants:
    """Tests that verify serialization preserves trait values."""

    @pytest.mark.parametrize("seed", range(50))
    def test_genome_serialization_roundtrip(self, seed: int) -> None:
        """Genome -> dict -> Genome preserves all physical trait values."""
        rng = random.Random(seed)
        original = Genome.random(rng=rng, use_algorithm=False)

        data = original.to_dict()
        restored = Genome.from_dict(data, rng=rng, use_algorithm=False)

        for spec in PHYSICAL_TRAIT_SPECS:
            orig_val = getattr(original.physical, spec.name).value
            rest_val = getattr(restored.physical, spec.name).value
            assert orig_val == pytest.approx(
                rest_val, abs=1e-9
            ), f"Seed {seed}: {spec.name} changed from {orig_val} to {rest_val}"

    @pytest.mark.parametrize("seed", range(50))
    def test_genome_behavioral_serialization_roundtrip(self, seed: int) -> None:
        """Genome -> dict -> Genome preserves all behavioral trait values."""
        rng = random.Random(seed)
        original = Genome.random(rng=rng, use_algorithm=False)

        data = original.to_dict()
        restored = Genome.from_dict(data, rng=rng, use_algorithm=False)

        for spec in BEHAVIORAL_TRAIT_SPECS:
            orig_val = getattr(original.behavioral, spec.name).value
            rest_val = getattr(restored.behavioral, spec.name).value
            assert orig_val == pytest.approx(
                rest_val, abs=1e-9
            ), f"Seed {seed}: {spec.name} changed from {orig_val} to {rest_val}"


class TestDiscreteTraitTypes:
    """Tests that discrete traits remain integers after inheritance."""

    @pytest.mark.parametrize("seed", range(50))
    def test_discrete_physical_traits_are_integers(self, seed: int) -> None:
        """Discrete physical traits must be integers after any operation."""
        rng = random.Random(seed)
        parent1 = PhysicalTraits.random(rng)
        parent2 = PhysicalTraits.random(rng)
        child = PhysicalTraits.from_parents(parent1, parent2, rng=rng)

        for spec in PHYSICAL_TRAIT_SPECS:
            if spec.discrete:
                trait = getattr(child, spec.name)
                assert isinstance(
                    trait.value, int
                ), f"Discrete trait {spec.name} has non-int value: {trait.value}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
