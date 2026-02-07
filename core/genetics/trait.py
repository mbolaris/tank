"""Genetic trait definitions and inheritance helpers.

This module provides:
- GeneticTrait: A wrapper that adds meta-genetic properties to trait values
- TraitSpec: Declarative specification for trait bounds and behavior
- Helper functions for inheriting traits between parents
"""

import random as pyrandom
from dataclasses import dataclass
from typing import (TYPE_CHECKING, Any, Callable, Dict, Generic, List,
                    Optional, TypeVar, Union)

from core.evolution.inheritance import \
    inherit_discrete_trait as _inherit_discrete_trait
from core.evolution.inheritance import inherit_trait as _inherit_trait

if TYPE_CHECKING:
    pass

T = TypeVar("T")

# =============================================================================
# Meta-Mutation Constants
# =============================================================================
# These control the "evolution of evolution" - how quickly the meta-genetic
# parameters (mutation_rate, mutation_strength, hgt_probability) can change.
# TUNED FOR FASTER EVOLUTION: Increased rates to accelerate adaptation.

META_MUTATION_CHANCE: float = 0.10  # 10% chance per trait (up from 5%)
META_HGT_MUTATION_CHANCE: float = 0.15  # 15% HGT mutation chance (up from 8%)
META_MUTATION_SIGMA: float = 0.08  # Gaussian sigma for meta-changes (up from 0.05)

# Bounds widened to allow more evolutionary diversity
META_MUTATION_RATE_MIN: float = 0.4  # Allow slightly lower rates
META_MUTATION_RATE_MAX: float = 3.0  # Allow much higher rates (up from 2.0)
META_MUTATION_STRENGTH_MIN: float = 0.4  # Allow slightly lower strength
META_MUTATION_STRENGTH_MAX: float = 3.0  # Allow much stronger mutations (up from 2.0)


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def random_genetic_trait(
    value: Any,
    rng: pyrandom.Random,
    *,
    hgt_max: float = 0.2,
) -> "GeneticTrait":
    """Create a GeneticTrait with randomized meta-genetic values.

    Use this factory when creating traits for the founding population
    to ensure initial genetic diversity in evolvability parameters.

    Args:
        value: The trait value
        rng: Random number generator
        hgt_max: Maximum initial HGT probability (default 0.2 = 20%)

    Returns:
        GeneticTrait with randomized mutation_rate, mutation_strength, hgt_probability
    """
    mutation_rate = _coerce_float(
        rng.uniform(META_MUTATION_RATE_MIN, META_MUTATION_RATE_MAX),
        (META_MUTATION_RATE_MIN + META_MUTATION_RATE_MAX) / 2,
    )
    mutation_strength = _coerce_float(
        rng.uniform(META_MUTATION_STRENGTH_MIN, META_MUTATION_STRENGTH_MAX),
        (META_MUTATION_STRENGTH_MIN + META_MUTATION_STRENGTH_MAX) / 2,
    )
    hgt_probability = _coerce_float(rng.uniform(0.0, hgt_max), hgt_max / 2)
    return GeneticTrait(
        value,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        hgt_probability=hgt_probability,
    )


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

    def mutate_meta(self, rng: Optional[pyrandom.Random] = None) -> None:
        """Mutate the metadata itself (evolution of evolution).

        Uses dampened mutation rates to prevent runaway evolvability changes.
        See module-level META_* constants for tuning parameters.
        """
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        if rng.random() < META_MUTATION_CHANCE:
            self.mutation_rate = max(
                META_MUTATION_RATE_MIN,
                min(META_MUTATION_RATE_MAX, self.mutation_rate + rng.gauss(0, META_MUTATION_SIGMA)),
            )
        if rng.random() < META_MUTATION_CHANCE:
            self.mutation_strength = max(
                META_MUTATION_STRENGTH_MIN,
                min(
                    META_MUTATION_STRENGTH_MAX,
                    self.mutation_strength + rng.gauss(0, META_MUTATION_SIGMA),
                ),
            )
        if rng.random() < META_HGT_MUTATION_CHANCE:
            self.hgt_probability = max(
                0.0, min(1.0, self.hgt_probability + rng.gauss(0, META_MUTATION_SIGMA))
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
        """Generate a random trait value within bounds.

        Also randomizes meta-genetic values (mutation_rate, mutation_strength,
        hgt_probability) to ensure the founding population has genetic diversity
        that can drift over evolution.
        """
        raw_value: Any
        if self.default_factory:
            raw_value = self.default_factory(rng)
        elif self.discrete:
            raw_value = rng.randint(int(self.min_val), int(self.max_val))
        else:
            raw_value = rng.uniform(self.min_val, self.max_val)

        value: Union[float, int]
        if self.discrete:
            default_int = int(round((self.min_val + self.max_val) / 2))
            int_value = _coerce_int(raw_value, default_int)
            value = max(int(self.min_val), min(int(self.max_val), int(int_value)))
        else:
            default_float = (self.min_val + self.max_val) / 2.0
            float_value = _coerce_float(raw_value, default_float)
            value = max(self.min_val, min(self.max_val, float(float_value)))

        # Randomize meta-genetic values to seed initial diversity
        mutation_rate = _coerce_float(
            rng.uniform(META_MUTATION_RATE_MIN, META_MUTATION_RATE_MAX),
            (META_MUTATION_RATE_MIN + META_MUTATION_RATE_MAX) / 2,
        )
        mutation_strength = _coerce_float(
            rng.uniform(META_MUTATION_STRENGTH_MIN, META_MUTATION_STRENGTH_MAX),
            (META_MUTATION_STRENGTH_MIN + META_MUTATION_STRENGTH_MAX) / 2,
        )
        hgt_probability = _coerce_float(rng.uniform(0.0, 0.2), 0.1)
        return GeneticTrait(
            value,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            hgt_probability=hgt_probability,
        )

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

        value: Union[float, int]
        if self.discrete:
            value = _inherit_discrete_trait(
                int(trait1.value),
                int(trait2.value),
                int(self.min_val),
                int(self.max_val),
                weight1=weight1,
                mutation_rate=eff_rate,
                rng=rng,
            )
        else:
            value = _inherit_trait(
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
            value,
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


def inherit_traits_from_specs_recombination(
    specs: List[TraitSpec],
    parent1_traits: object,
    parent2_traits: object,
    *,
    parent1_probability: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> dict:
    """Inherit all traits by choosing a parent per trait (recombination).

    For each trait, the offspring receives either parent1's value (probability
    `parent1_probability`) or parent2's value; mutation is then applied.
    """
    inherited = {}
    parent1_probability = max(0.0, min(1.0, parent1_probability))
    for spec in specs:
        trait1 = getattr(parent1_traits, spec.name)
        trait2 = getattr(parent2_traits, spec.name)
        trait_weight1 = 1.0 if rng.random() < parent1_probability else 0.0
        inherited[spec.name] = spec.inherit(
            trait1,
            trait2,
            weight1=trait_weight1,
            base_mutation_rate=mutation_rate,
            base_mutation_strength=mutation_strength,
            rng=rng,
        )
    return inherited


def trait_values_to_dict(specs: List[TraitSpec], traits: object) -> Dict[str, Any]:
    """Serialize a trait container to a primitives dict using TraitSpec definitions."""
    out: Dict[str, Any] = {}
    for spec in specs:
        trait = getattr(traits, spec.name)
        out[spec.name] = trait.value
    return out


def trait_meta_to_dict(specs: List[TraitSpec], traits: object) -> Dict[str, Dict[str, float]]:
    """Serialize non-default GeneticTrait metadata for trait containers defined by specs."""
    out: Dict[str, Dict[str, float]] = {}
    for spec in specs:
        trait = getattr(traits, spec.name)
        meta = trait_meta_for_trait(trait)
        if meta:
            out[spec.name] = meta
    return out


def apply_trait_values_from_dict(
    specs: List[TraitSpec], traits: object, data: Dict[str, Any]
) -> None:
    """Apply primitive values from *data* onto *traits* using TraitSpec definitions."""
    for spec in specs:
        if spec.name not in data:
            continue
        trait = getattr(traits, spec.name)
        raw = data[spec.name]
        # Coerce and clamp incoming values to the declared spec bounds.
        if spec.discrete:
            try:
                int_value = int(raw)
            except (TypeError, ValueError):
                continue
            int_value = max(int(spec.min_val), min(int(spec.max_val), int(int_value)))
            trait.value = int(int_value)
        else:
            try:
                float_value = float(raw)
            except (TypeError, ValueError):
                continue
            float_value = max(spec.min_val, min(spec.max_val, float(float_value)))
            trait.value = float(float_value)


def apply_trait_meta_from_dict(
    specs: List[TraitSpec], traits: object, meta_by_trait: Dict[str, Dict[str, Any]]
) -> None:
    """Apply GeneticTrait metadata from a dict produced by `trait_meta_to_dict`."""
    for spec in specs:
        meta = meta_by_trait.get(spec.name)
        if not meta:
            continue
        trait = getattr(traits, spec.name)
        apply_trait_meta_to_trait(trait, meta)


def trait_meta_for_trait(
    trait: GeneticTrait[Any],
    *,
    default_mutation_rate: float = 1.0,
    default_mutation_strength: float = 1.0,
    default_hgt_probability: float = 0.1,
) -> Dict[str, float]:
    """Serialize non-default GeneticTrait metadata for a single trait."""
    meta: Dict[str, float] = {}
    if trait.mutation_rate != default_mutation_rate:
        meta["mutation_rate"] = float(trait.mutation_rate)
    if trait.mutation_strength != default_mutation_strength:
        meta["mutation_strength"] = float(trait.mutation_strength)
    if trait.hgt_probability != default_hgt_probability:
        meta["hgt_probability"] = float(trait.hgt_probability)
    return meta


def apply_trait_meta_to_trait(trait: GeneticTrait[Any], meta: Dict[str, Any]) -> None:
    """Apply GeneticTrait metadata onto a single trait instance."""
    if "mutation_rate" in meta:
        trait.mutation_rate = max(0.0, float(meta["mutation_rate"]))
    if "mutation_strength" in meta:
        trait.mutation_strength = max(0.0, float(meta["mutation_strength"]))
    if "hgt_probability" in meta:
        trait.hgt_probability = max(0.0, min(1.0, float(meta["hgt_probability"])))
