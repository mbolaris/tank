"""Genetic trait definitions and inheritance helpers.

This module provides:
- GeneticTrait: A wrapper that adds meta-genetic properties to trait values
- TraitSpec: Declarative specification for trait bounds and behavior
- Helper functions for inheriting traits between parents
"""

import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, List, Optional, TypeVar

from core.evolution.inheritance import (
    inherit_trait as _inherit_trait,
    inherit_discrete_trait as _inherit_discrete_trait,
)

if TYPE_CHECKING:
    pass

T = TypeVar("T")


@dataclass
class GeneticTrait(Generic[T]):
    """A genetic trait with metadata for evolution.

    Attributes:
        value: The actual trait value
        mutation_rate: Multiplier for how likely this specific trait is to mutate
        mutation_strength: Multiplier for how strongly this trait mutates
        hgt_probability: Probability of Horizontal Gene Transfer (taking trait from mate)
    """

    value: T
    mutation_rate: float = 1.0
    mutation_strength: float = 1.0
    hgt_probability: float = 0.1

    def mutate_meta(self, rng: pyrandom.Random = pyrandom) -> None:
        """Mutate the metadata itself (evolution of evolution)."""
        # Dampen meta-mutation to avoid runaway evolvability changes.
        # Lower chance and smaller gaussian steps; tighten clamps.
        if rng.random() < 0.01:
            self.mutation_rate = max(0.5, min(2.0, self.mutation_rate + rng.gauss(0, 0.02)))
        if rng.random() < 0.01:
            self.mutation_strength = max(
                0.5, min(2.0, self.mutation_strength + rng.gauss(0, 0.02))
            )
        if rng.random() < 0.02:
            self.hgt_probability = max(
                0.0, min(1.0, self.hgt_probability + rng.gauss(0, 0.02))
            )


@dataclass
class TraitSpec:
    """Declarative specification for a genetic trait.

    This allows trait definitions to be data-driven rather than hardcoded,
    enabling easier extension and modification of the genetic system.

    Attributes:
        name: Attribute name on the traits container
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        discrete: Whether this is a discrete (int) or continuous (float) trait
        default_factory: Optional factory for generating default values
    """

    name: str
    min_val: float
    max_val: float
    discrete: bool = False
    default_factory: Optional[Callable[[pyrandom.Random], float]] = None

    def random_value(self, rng: pyrandom.Random) -> GeneticTrait:
        """Generate a random trait value within bounds."""
        if self.default_factory:
            val = self.default_factory(rng)
        elif self.discrete:
            val = rng.randint(int(self.min_val), int(self.max_val))
        else:
            val = rng.uniform(self.min_val, self.max_val)
        return GeneticTrait(val)

    def inherit(
        self,
        trait1: GeneticTrait,
        trait2: GeneticTrait,
        *,
        weight1: float,
        base_mutation_rate: float,
        base_mutation_strength: float,
        rng: pyrandom.Random,
    ) -> GeneticTrait:
        """Inherit this trait from two parents with mutation."""
        # Blend metadata from both parents
        eff_rate = base_mutation_rate * (trait1.mutation_rate + trait2.mutation_rate) / 2
        eff_strength = (
            base_mutation_strength * (trait1.mutation_strength + trait2.mutation_strength) / 2
        )

        if self.discrete:
            new_val = _inherit_discrete_trait(
                int(trait1.value),
                int(trait2.value),
                int(self.min_val),
                int(self.max_val),
                weight1=weight1,
                mutation_rate=eff_rate,
                rng=rng,
            )
        else:
            new_val = _inherit_trait(
                float(trait1.value),
                float(trait2.value),
                self.min_val,
                self.max_val,
                weight1=weight1,
                mutation_rate=eff_rate,
                mutation_strength=eff_strength,
                rng=rng,
            )

        # Create new trait with blended metadata
        new_trait = GeneticTrait(
            new_val,
            mutation_rate=(trait1.mutation_rate + trait2.mutation_rate) / 2,
            mutation_strength=(trait1.mutation_strength + trait2.mutation_strength) / 2,
            hgt_probability=(trait1.hgt_probability + trait2.hgt_probability) / 2,
        )
        new_trait.mutate_meta(rng)
        return new_trait


def inherit_traits_from_specs(
    specs: List[TraitSpec],
    parent1_traits: object,
    parent2_traits: object,
    *,
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> dict:
    """Inherit all traits from parents using trait specifications.

    Args:
        specs: List of TraitSpec definitions
        parent1_traits: First parent's trait container
        parent2_traits: Second parent's trait container
        weight1: Weight for first parent (0.0-1.0)
        mutation_rate: Base mutation rate
        mutation_strength: Base mutation strength
        rng: Random number generator

    Returns:
        Dictionary of {trait_name: GeneticTrait} for offspring
    """
    inherited = {}
    for spec in specs:
        trait1 = getattr(parent1_traits, spec.name)
        trait2 = getattr(parent2_traits, spec.name)
        inherited[spec.name] = spec.inherit(
            trait1,
            trait2,
            weight1=weight1,
            base_mutation_rate=mutation_rate,
            base_mutation_strength=mutation_strength,
            rng=rng,
        )
    return inherited
