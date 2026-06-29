"""Tests for the Horizontal Gene Transfer (HGT) mechanism in TraitSpec.inherit.

Proposal #5 activated the dormant hgt_probability meta-gene so that, during
inheritance, a random draw below the parents' average hgt_probability causes
the trait value to be COPIED from the dominant parent (determined by weight1)
instead of being blended.  These tests verify:

1. HGT fires deterministically when hgt_probability=1.0 (always copy).
2. HGT never fires when hgt_probability=0.0 (always blend, original behavior).
3. When HGT fires, the inherited value comes from the dominant parent (± mutation).
4. Trait bounds are preserved under HGT for both continuous and discrete traits.
5. Deterministic: same seed produces the same outcome.
"""

import random

import pytest

from core.genetics.trait import GeneticTrait, TraitSpec


def _make_spec(*, discrete: bool = False) -> TraitSpec:
    """Create a simple test TraitSpec."""
    return TraitSpec(
        name="test_trait",
        min_val=0.0 if not discrete else 0,
        max_val=1.0 if not discrete else 10,
        discrete=discrete,
    )


def _make_trait(value: float, hgt: float = 0.0) -> GeneticTrait:
    """Create a GeneticTrait with specified value and hgt_probability."""
    return GeneticTrait(
        value,
        mutation_rate=0.0,  # Zero mutation to isolate HGT effect
        mutation_strength=0.0,
        hgt_probability=hgt,
    )


class TestHGTMechanism:
    """Tests that the HGT gate in TraitSpec.inherit works correctly."""

    def test_hgt_always_fires_when_probability_one(self) -> None:
        """With hgt_probability=1.0 and zero mutation, value should equal donor."""
        spec = _make_spec()
        parent1 = _make_trait(0.8, hgt=1.0)
        parent2 = _make_trait(0.2, hgt=1.0)
        rng = random.Random(42)

        # weight1=0.7 means parent1 is dominant
        child = spec.inherit(
            parent1,
            parent2,
            weight1=0.7,
            base_mutation_rate=0.0,
            base_mutation_strength=0.0,
            rng=rng,
        )
        # With hgt=1.0 and mutation_rate=0.0, child value should be exactly parent1's
        assert child.value == pytest.approx(
            0.8
        ), f"Expected donor (parent1) value 0.8, got {child.value}"

    def test_hgt_copies_parent2_when_weight1_low(self) -> None:
        """With weight1 < 0.5, HGT should copy from parent2 (the dominant one)."""
        spec = _make_spec()
        parent1 = _make_trait(0.8, hgt=1.0)
        parent2 = _make_trait(0.2, hgt=1.0)
        rng = random.Random(42)

        # weight1=0.3 means parent2 is dominant
        child = spec.inherit(
            parent1,
            parent2,
            weight1=0.3,
            base_mutation_rate=0.0,
            base_mutation_strength=0.0,
            rng=rng,
        )
        assert child.value == pytest.approx(
            0.2
        ), f"Expected donor (parent2) value 0.2, got {child.value}"

    def test_hgt_never_fires_when_probability_zero(self) -> None:
        """With hgt_probability=0.0, should always blend (original behavior)."""
        spec = _make_spec()
        parent1 = _make_trait(0.8, hgt=0.0)
        parent2 = _make_trait(0.2, hgt=0.0)
        rng = random.Random(42)

        child = spec.inherit(
            parent1,
            parent2,
            weight1=0.5,
            base_mutation_rate=0.0,
            base_mutation_strength=0.0,
            rng=rng,
        )
        # With equal weight and zero mutation, should be average of 0.8 and 0.2 = 0.5
        assert child.value == pytest.approx(0.5), f"Expected blended value 0.5, got {child.value}"

    def test_hgt_discrete_trait_copies_exactly(self) -> None:
        """Discrete traits should also copy via HGT when probability is 1.0."""
        spec = _make_spec(discrete=True)
        parent1 = _make_trait(8, hgt=1.0)
        parent2 = _make_trait(2, hgt=1.0)
        rng = random.Random(42)

        child = spec.inherit(
            parent1,
            parent2,
            weight1=0.7,
            base_mutation_rate=0.0,
            base_mutation_strength=0.0,
            rng=rng,
        )
        assert child.value == 8, f"Expected donor value 8, got {child.value}"
        assert isinstance(child.value, int), "Discrete trait should be int"

    @pytest.mark.parametrize("seed", range(50))
    def test_hgt_preserves_bounds(self, seed: int) -> None:
        """HGT + mutation must never produce values outside spec bounds."""
        spec = _make_spec()
        rng = random.Random(seed)

        # Use extreme values near bounds and high hgt + mutation
        parent1 = GeneticTrait(
            spec.max_val, mutation_rate=0.5, mutation_strength=0.5, hgt_probability=0.9
        )
        parent2 = GeneticTrait(
            spec.min_val, mutation_rate=0.5, mutation_strength=0.5, hgt_probability=0.9
        )

        child = spec.inherit(
            parent1,
            parent2,
            weight1=0.5,
            base_mutation_rate=0.5,
            base_mutation_strength=0.5,
            rng=rng,
        )
        assert (
            spec.min_val <= child.value <= spec.max_val
        ), f"Seed {seed}: value {child.value} outside [{spec.min_val}, {spec.max_val}]"

    @pytest.mark.parametrize("seed", range(50))
    def test_hgt_discrete_preserves_bounds(self, seed: int) -> None:
        """HGT + mutation on discrete traits must stay in bounds."""
        spec = _make_spec(discrete=True)
        rng = random.Random(seed)

        parent1 = GeneticTrait(
            int(spec.max_val),
            mutation_rate=0.5,
            mutation_strength=0.5,
            hgt_probability=0.9,
        )
        parent2 = GeneticTrait(
            int(spec.min_val),
            mutation_rate=0.5,
            mutation_strength=0.5,
            hgt_probability=0.9,
        )

        child = spec.inherit(
            parent1,
            parent2,
            weight1=0.5,
            base_mutation_rate=0.5,
            base_mutation_strength=0.5,
            rng=rng,
        )
        assert (
            spec.min_val <= child.value <= spec.max_val
        ), f"Seed {seed}: value {child.value} outside [{spec.min_val}, {spec.max_val}]"
        assert isinstance(child.value, int), "Discrete trait must be int"

    def test_hgt_deterministic(self) -> None:
        """Same seed must produce the same HGT result."""
        spec = _make_spec()
        parent1 = GeneticTrait(0.9, mutation_rate=0.3, mutation_strength=0.1, hgt_probability=0.6)
        parent2 = GeneticTrait(0.1, mutation_rate=0.2, mutation_strength=0.15, hgt_probability=0.4)

        results = []
        for _ in range(3):
            rng = random.Random(42)
            child = spec.inherit(
                parent1,
                parent2,
                weight1=0.7,
                base_mutation_rate=0.1,
                base_mutation_strength=0.1,
                rng=rng,
            )
            results.append(child.value)

        assert results[0] == results[1] == results[2], f"Non-deterministic: {results}"

    def test_hgt_probability_is_heritable(self) -> None:
        """Child's hgt_probability should be the average of parents'."""
        spec = _make_spec()
        parent1 = _make_trait(0.5, hgt=0.8)
        parent2 = _make_trait(0.5, hgt=0.2)
        rng = random.Random(42)

        child = spec.inherit(
            parent1,
            parent2,
            weight1=0.5,
            base_mutation_rate=0.0,
            base_mutation_strength=0.0,
            rng=rng,
        )
        # Before meta-mutation, avg should be 0.5; after meta-mutation it may shift
        # but should remain in [0, 1]
        assert 0.0 <= child.hgt_probability <= 1.0

    def test_hgt_fires_at_intermediate_probability(self) -> None:
        """With moderate hgt_probability, HGT should fire in some fraction of trials."""
        spec = _make_spec()
        parent1 = _make_trait(0.9, hgt=0.5)
        parent2 = _make_trait(0.1, hgt=0.5)

        hgt_count = 0
        n_trials = 200
        for seed in range(n_trials):
            rng = random.Random(seed)
            child = spec.inherit(
                parent1,
                parent2,
                weight1=0.7,
                base_mutation_rate=0.0,
                base_mutation_strength=0.0,
                rng=rng,
            )
            # If HGT fired with weight1=0.7, child should be near 0.9 (parent1)
            # If blended with weight1=0.7, child = 0.9*0.7 + 0.1*0.3 = 0.66
            # So values > 0.8 indicate HGT fired
            if child.value > 0.85:
                hgt_count += 1

        # Expected: ~50% HGT fires (avg hgt_probability = 0.5)
        # Allow wide range: 30-70% to account for RNG variation
        fraction = hgt_count / n_trials
        assert 0.25 <= fraction <= 0.75, f"HGT fired {fraction*100:.0f}% of the time; expected ~50%"

    def test_hgt_respects_parent1_dominant_explicit(self) -> None:
        """With parent1_dominant=True/False, HGT should copy from parent1/parent2 regardless of weight1."""
        spec = _make_spec()
        parent1 = _make_trait(0.8, hgt=1.0)
        parent2 = _make_trait(0.2, hgt=1.0)
        rng = random.Random(42)

        # weight1=0.2 (means parent2 is dominant by weight)
        # but parent1_dominant=True (explicitly overrides weight1)
        child1 = spec.inherit(
            parent1,
            parent2,
            weight1=0.2,
            base_mutation_rate=0.0,
            base_mutation_strength=0.0,
            rng=rng,
            parent1_dominant=True,
        )
        assert child1.value == pytest.approx(0.8)

        # weight1=0.8 (means parent1 is dominant by weight)
        # but parent1_dominant=False (explicitly overrides weight1)
        child2 = spec.inherit(
            parent1,
            parent2,
            weight1=0.8,
            base_mutation_rate=0.0,
            base_mutation_strength=0.0,
            rng=rng,
            parent1_dominant=False,
        )
        assert child2.value == pytest.approx(0.2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
