"""Genome class for fish artificial life simulation.

This module provides the core Genome class that represents the complete
genetic makeup of a fish, combining physical and behavioral traits.
"""

import logging
import random as pyrandom
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, cast

from core.genetics import expression
from core.genetics.behavioral import BehavioralTraits
from core.genetics.genome_codec import genome_debug_snapshot, genome_from_dict, genome_to_dict
from core.genetics.physical import PhysicalTraits
from core.genetics.reproduction import ReproductionParams
from core.genetics.validation import validate_traits_from_specs

logger = logging.getLogger(__name__)
GENOME_SCHEMA_VERSION = 2  # Bumped from 1: added code_policy_{kind,component_id,params}


class GeneticCrossoverMode(Enum):
    """Different modes for genetic crossover during reproduction."""

    AVERAGING = "averaging"
    RECOMBINATION = "recombination"
    DOMINANT_RECESSIVE = "dominant_recessive"


@dataclass
class Genome:
    """Represents the complete genetic makeup of a fish.

    Attributes:
        physical: Physical appearance traits
        behavioral: Behavioral and decision-making traits
    """

    physical: PhysicalTraits
    behavioral: BehavioralTraits

    # =========================================================================
    # Derived Properties (computed from base traits with caching)
    # =========================================================================

    # OPTIMIZATION: Cache for computed properties to avoid repeated calculations
    _speed_modifier_cache: Optional[float] = field(default=None, repr=False, compare=False)
    _metabolism_rate_cache: Optional[float] = field(default=None, repr=False, compare=False)

    @property
    def speed_modifier(self) -> float:
        """Calculate speed modifier based on physical traits (cached)."""
        if self._speed_modifier_cache is not None:
            return self._speed_modifier_cache

        result = expression.calculate_speed_modifier(self.physical)
        object.__setattr__(self, "_speed_modifier_cache", result)
        return result

    @property
    def vision_range(self) -> float:
        """Calculate vision range based on eye size."""
        return expression.calculate_vision_range(self.physical)

    @property
    def metabolism_rate(self) -> float:
        """Calculate metabolism rate based on physical traits (cached)."""
        if self._metabolism_rate_cache is not None:
            return self._metabolism_rate_cache

        result = expression.calculate_metabolism_rate(self.physical, self.speed_modifier)
        object.__setattr__(self, "_metabolism_rate_cache", result)
        return result

    def invalidate_caches(self) -> None:
        """Invalidate cached computed properties when traits change."""
        object.__setattr__(self, "_speed_modifier_cache", None)
        object.__setattr__(self, "_metabolism_rate_cache", None)

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        """Serialize this genome into JSON-compatible primitives.

        This is intended as a stable boundary format for persistence and transfer.
        """
        return genome_to_dict(
            self,
            schema_version=GENOME_SCHEMA_VERSION,
        )

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        *,
        rng: Optional[pyrandom.Random] = None,
        use_algorithm: bool = True,
    ) -> "Genome":
        """Deserialize a genome from JSON-compatible primitives.

        Unknown fields are ignored; missing fields keep randomized defaults.
        """
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        genome = genome_from_dict(
            data,
            schema_version_expected=GENOME_SCHEMA_VERSION,
            genome_factory=lambda: cls.random(use_algorithm=use_algorithm, rng=rng),
            rng=rng,
        )
        return cast("Genome", genome)

    def debug_snapshot(self) -> Dict[str, Any]:
        """Return a compact, stable dict for logging/debugging."""
        return genome_debug_snapshot(self)

    def validate(self) -> Dict[str, Any]:
        """Validate trait ranges/types; returns a dict with any issues found."""
        from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
        from core.genetics.physical import PHYSICAL_TRAIT_SPECS

        issues = []
        issues.extend(
            validate_traits_from_specs(PHYSICAL_TRAIT_SPECS, self.physical, path="genome.physical")
        )
        issues.extend(
            validate_traits_from_specs(
                BEHAVIORAL_TRAIT_SPECS, self.behavioral, path="genome.behavioral"
            )
        )

        # Validate per-kind policy params fields
        from core.genetics.behavioral import validate_policy_fields

        for kind, id_attr, params_attr in [
            ("movement_policy", "movement_policy_id", "movement_policy_params"),
            ("poker_policy", "poker_policy_id", "poker_policy_params"),
            ("soccer_policy", "soccer_policy_id", "soccer_policy_params"),
        ]:
            policy_id = (
                getattr(self.behavioral, id_attr).value
                if getattr(self.behavioral, id_attr, None)
                else None
            )
            policy_params = (
                getattr(self.behavioral, params_attr).value
                if getattr(self.behavioral, params_attr, None)
                else None
            )
            policy_issues = validate_policy_fields(policy_id, policy_params, policy_kind=kind)
            for issue in policy_issues:
                issues.append(f"genome.behavioral.{issue}")

        return {"ok": not issues, "issues": issues}

    def assert_valid(self) -> None:
        """Raise ValueError if validation finds problems (debug aid)."""
        result = self.validate()
        if result["ok"]:
            return
        issues = "\n".join(result["issues"])
        raise ValueError(f"Invalid genome:\n{issues}")

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def random(cls, use_algorithm: bool = True, rng: Optional[pyrandom.Random] = None) -> "Genome":
        """Create a random genome."""
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        physical = PhysicalTraits.random(rng)
        return cls(
            physical=physical,
            behavioral=BehavioralTraits.random(rng, use_algorithm, physical=physical),
        )

    @classmethod
    def from_parents_weighted_params(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        parent1_weight: float = 0.5,
        *,
        params: ReproductionParams,
        rng: Optional[pyrandom.Random] = None,
        available_policies: Optional[List[str]] = None,
    ) -> "Genome":
        """Create offspring genome using a parameter object for mutation inputs."""
        return cls.from_parents_weighted(
            parent1=parent1,
            parent2=parent2,
            parent1_weight=parent1_weight,
            mutation_rate=params.mutation_rate,
            mutation_strength=params.mutation_strength,
            rng=rng,
            available_policies=available_policies,
        )

    @classmethod
    def from_parents_weighted(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        parent1_weight: float = 0.5,
        mutation_rate: float = 0.15,  # Increased from 0.1
        mutation_strength: float = 0.15,  # Increased from 0.1
        rng: Optional[pyrandom.Random] = None,
        available_policies: Optional[List[str]] = None,
    ) -> "Genome":
        """Create offspring genome with weighted contributions from parents.

        This is the core inheritance method. The declarative trait system
        handles all the per-trait inheritance, eliminating hundreds of lines
        of duplicated code.
        """
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        parent1_weight = max(0.0, min(1.0, parent1_weight))
        adaptive_rate, adaptive_strength = ReproductionParams(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        ).adaptive_mutation()

        # Inherit traits using declarative specs
        physical = PhysicalTraits.from_parents(
            parent1.physical,
            parent2.physical,
            weight1=parent1_weight,
            mutation_rate=adaptive_rate,
            mutation_strength=adaptive_strength,
            rng=rng,
        )

        behavioral = BehavioralTraits.from_parents(
            parent1.behavioral,
            parent2.behavioral,
            weight1=parent1_weight,
            mutation_rate=adaptive_rate,
            mutation_strength=adaptive_strength,
            rng=rng,
            available_policies=available_policies,
        )

        return cls._assemble_offspring(
            parent1=parent1,
            parent2=parent2,
            physical=physical,
            behavioral=behavioral,
        )

    @classmethod
    def clone_with_mutation(
        cls,
        parent: "Genome",
        rng: Optional[pyrandom.Random] = None,
        available_policies: Optional[List[str]] = None,
    ) -> "Genome":
        """Clone a genome with mutation (asexual reproduction)."""
        return cls.from_parents_weighted_params(
            parent1=parent,
            parent2=parent,
            parent1_weight=1.0,
            params=ReproductionParams(),
            rng=rng,
            available_policies=available_policies,
        )

    @classmethod
    def from_parents(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        mutation_rate: float = 0.15,  # Increased from 0.1
        mutation_strength: float = 0.15,  # Increased from 0.1
        crossover_mode: GeneticCrossoverMode = GeneticCrossoverMode.RECOMBINATION,
        rng: Optional[pyrandom.Random] = None,
        available_policies: Optional[List[str]] = None,
    ) -> "Genome":
        """Create offspring genome by mixing parent genes with mutations."""
        from core.util.rng import require_rng_param

        rng = require_rng_param(rng, "__init__")
        params = ReproductionParams(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        )

        if crossover_mode is GeneticCrossoverMode.AVERAGING:
            return cls.from_parents_weighted_params(
                parent1=parent1,
                parent2=parent2,
                parent1_weight=0.5,
                params=params,
                rng=rng,
                available_policies=available_policies,
            )

        if crossover_mode is GeneticCrossoverMode.DOMINANT_RECESSIVE:
            logger.debug(
                "crossover_mode=%s currently behaves like recombination", crossover_mode.value
            )

        adaptive_rate, adaptive_strength = params.adaptive_mutation()

        physical = PhysicalTraits.from_parents_recombination(
            parent1.physical,
            parent2.physical,
            parent1_probability=0.5,
            mutation_rate=adaptive_rate,
            mutation_strength=adaptive_strength,
            rng=rng,
        )

        behavioral = BehavioralTraits.from_parents_recombination(
            parent1.behavioral,
            parent2.behavioral,
            parent1_probability=0.5,
            mutation_rate=adaptive_rate,
            mutation_strength=adaptive_strength,
            rng=rng,
        )

        return cls._assemble_offspring(
            parent1=parent1,
            parent2=parent2,
            physical=physical,
            behavioral=behavioral,
        )

    @classmethod
    def from_winner_choice(
        cls,
        winner: "Genome",
        mate: "Genome",
        mutation_rate: float = 0.15,  # Increased from 0.1
        mutation_strength: float = 0.15,  # Increased from 0.1
        rng: Optional[pyrandom.Random] = None,
    ) -> "Genome":
        """Create offspring where winner selectively borrows mate traits.

        The winner genome uses its hgt_probability to decide which traits
        to take from the mate vs keep from self.
        """
        # Winner-based inheritance uses 80/20 weighting favoring winner
        return cls.from_parents_weighted_params(
            parent1=winner,
            parent2=mate,
            parent1_weight=0.8,
            params=ReproductionParams(
                mutation_rate=mutation_rate,
                mutation_strength=mutation_strength,
            ),
            rng=rng,
        )

    @classmethod
    def _assemble_offspring(
        cls,
        *,
        parent1: "Genome",
        parent2: "Genome",
        physical: PhysicalTraits,
        behavioral: BehavioralTraits,
    ) -> "Genome":
        """Build an offspring genome and apply non-genetic inheritance."""
        return cls(
            physical=physical,
            behavioral=behavioral,
        )

    # =========================================================================
    # Instance Methods
    # =========================================================================

    def calculate_mate_attraction(self, other: "Genome") -> float:
        """Calculate how much this genome is attracted to another (0.0-1.0).

        Attraction is based on how closely the mate matches this fish's
        preferred physical trait values, plus a bonus for higher pattern intensity.
        """
        return expression.calculate_mate_attraction(self.physical, self.behavioral, other.physical)

    def get_color_tint(self) -> Tuple[int, int, int]:
        """Get RGB color tint based on genome."""
        return expression.calculate_color_tint(self.physical)
