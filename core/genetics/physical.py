"""Physical traits for fish genomes.

This module defines the physical appearance traits that affect fish visuals
and physical capabilities (size, speed derived from body shape, etc.).
"""

import random as pyrandom
from dataclasses import dataclass
from typing import List

from core.constants import (
    FISH_PATTERN_COUNT,
    FISH_SIZE_MODIFIER_MAX,
    FISH_SIZE_MODIFIER_MIN,
    FISH_TEMPLATE_COUNT,
)
from core.genetics.trait import GeneticTrait, TraitSpec, inherit_traits_from_specs

# Declarative specifications for all physical traits
PHYSICAL_TRAIT_SPECS: List[TraitSpec] = [
    TraitSpec("size_modifier", FISH_SIZE_MODIFIER_MIN, FISH_SIZE_MODIFIER_MAX),
    TraitSpec("color_hue", 0.0, 1.0),
    TraitSpec("template_id", 0, FISH_TEMPLATE_COUNT - 1, discrete=True),
    TraitSpec("fin_size", 0.5, 2.0),
    TraitSpec("tail_size", 0.5, 2.0),
    TraitSpec("body_aspect", 0.7, 1.3),
    TraitSpec("eye_size", 0.7, 1.3),
    TraitSpec("pattern_intensity", 0.0, 1.0),
    TraitSpec("pattern_type", 0, FISH_PATTERN_COUNT - 1, discrete=True),
    TraitSpec("lifespan_modifier", 0.6, 1.4),
]


@dataclass
class PhysicalTraits:
    """Physical attributes of a fish.

    These traits affect appearance and physical capabilities like speed.
    """

    size_modifier: GeneticTrait[float]
    color_hue: GeneticTrait[float]
    template_id: GeneticTrait[int]
    fin_size: GeneticTrait[float]
    tail_size: GeneticTrait[float]
    body_aspect: GeneticTrait[float]
    eye_size: GeneticTrait[float]
    pattern_intensity: GeneticTrait[float]
    pattern_type: GeneticTrait[int]
    lifespan_modifier: GeneticTrait[float]

    @classmethod
    def random(cls, rng: pyrandom.Random) -> "PhysicalTraits":
        """Generate random physical traits."""
        traits = {spec.name: spec.random_value(rng) for spec in PHYSICAL_TRAIT_SPECS}
        return cls(**traits)

    @classmethod
    def from_parents(
        cls,
        parent1: "PhysicalTraits",
        parent2: "PhysicalTraits",
        *,
        weight1: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        rng: pyrandom.Random,
    ) -> "PhysicalTraits":
        """Inherit physical traits from two parents."""
        inherited = inherit_traits_from_specs(
            PHYSICAL_TRAIT_SPECS,
            parent1,
            parent2,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
        return cls(**inherited)
