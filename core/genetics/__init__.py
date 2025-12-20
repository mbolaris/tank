"""Unified genetics package for artificial life simulation.

This package provides a consolidated genetic system for all evolvable entities
(fish, plants) with:

- Declarative trait specifications (TraitSpec)
- Unified inheritance and mutation logic
- Clean separation of physical and behavioral traits
- Support for meta-genetic evolution (traits that control mutation rates)

Design Philosophy (ALife vs GA):
- NO explicit fitness function evaluation
- NO tournament selection
- Selection emerges from survival and reproduction success
"""

# Re-export main classes for package convenience
from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS, BehavioralTraits
from core.genetics.genome import (
    GeneticCrossoverMode,
    Genome,
)
from core.genetics.physical import PHYSICAL_TRAIT_SPECS, PhysicalTraits
from core.genetics.plant import PlantGenome
from core.genetics.reproduction import ReproductionParams
from core.genetics.trait import (
    GeneticTrait,
    TraitSpec,
    inherit_traits_from_specs,
    inherit_traits_from_specs_recombination,
    trait_values_to_dict,
    trait_meta_to_dict,
    apply_trait_values_from_dict,
    apply_trait_meta_from_dict,
)
from core.genetics.validation import validate_traits_from_specs

__all__ = [
    # Core classes
    "Genome",
    "PlantGenome",
    "GeneticTrait",
    "TraitSpec",
    "GeneticCrossoverMode",
    # Trait containers
    "PhysicalTraits",
    "BehavioralTraits",
    # Trait specifications
    "PHYSICAL_TRAIT_SPECS",
    "BEHAVIORAL_TRAIT_SPECS",
    # Inheritance helpers
    "inherit_traits_from_specs",
    "inherit_traits_from_specs_recombination",
    # Serialization helpers
    "trait_values_to_dict",
    "trait_meta_to_dict",
    "apply_trait_values_from_dict",
    "apply_trait_meta_from_dict",
    # Reproduction API
    "ReproductionParams",
    # Validation
    "validate_traits_from_specs",
]
