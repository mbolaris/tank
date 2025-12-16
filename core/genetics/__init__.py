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

# Re-export main classes for backward compatibility
from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS, BehavioralTraits
from core.genetics.genome import (
    GeneticCrossoverMode,
    Genome,
)
from core.genetics.physical import PHYSICAL_TRAIT_SPECS, PhysicalTraits
from core.genetics.plant import PlantGenome
from core.genetics.trait import GeneticTrait, TraitSpec

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
]

