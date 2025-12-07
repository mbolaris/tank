"""Genetics system for artificial life simulation.

BACKWARD COMPATIBILITY MODULE
=============================
This module re-exports from core.genetics package for backward compatibility.
New code should import directly from core.genetics instead.

Example:
    # Old way (still works)
    from core.genetics import Genome, GeneticTrait

    # New way (preferred)
    from core.genetics import Genome, GeneticTrait
"""

# Re-export all public symbols from the new genetics package
from core.genetics.trait import GeneticTrait, TraitSpec
from core.genetics.genome import Genome, GeneticCrossoverMode
from core.genetics.physical import PhysicalTraits
from core.genetics.behavioral import BehavioralTraits

# Re-export evolution helpers that were previously used from here
from core.evolution.inheritance import inherit_learned_behaviors
from core.evolution.mutation import calculate_adaptive_mutation_rate

__all__ = [
    "Genome",
    "GeneticTrait",
    "TraitSpec",
    "GeneticCrossoverMode",
    "PhysicalTraits",
    "BehavioralTraits",
    "inherit_learned_behaviors",
    "calculate_adaptive_mutation_rate",
]
