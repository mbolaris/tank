"""Genome class for fish artificial life simulation.

This module provides the core Genome class that represents the complete
genetic makeup of a fish, combining physical and behavioral traits.
"""

import logging
import random as pyrandom
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

import core.genetics.expression as expression
from core.exceptions import GeneticsError
from core.genetics.behavioral import (
    BEHAVIORAL_TRAIT_SPECS,
    BehavioralTraits,
    validate_policy_fields,
)
from core.genetics.code_policy_traits import SOCCER_POLICY
from core.genetics.genome_codec import genome_debug_snapshot, genome_from_dict, genome_to_dict
from core.genetics.physical import PHYSICAL_TRAIT_SPECS, PhysicalTraits
from core.genetics.reproduction import ReproductionMutationContext, ReproductionParams
from core.genetics.trait import GeneticTrait
from core.genetics.validation import validate_traits_from_specs
from core.util.rng import require_rng_param

if TYPE_CHECKING:
    from core.code_pool.genome_code_pool import GenomeCodePool

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
    _speed_modifier_cache: float | None = field(default=None, repr=False, compare=False)
    _metabolism_rate_cache: float | None = field(default=None, repr=False, compare=False)

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
    ) -> dict[str, Any]:
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
        data: dict[str, Any],
        *,
        rng: pyrandom.Random | None = None,
        use_algorithm: bool = True,
    ) -> "Genome":
        """Deserialize a genome from JSON-compatible primitives.

        Unknown fields are ignored; missing fields keep randomized defaults.
        """
        rng = require_rng_param(rng, "__init__")
        genome = genome_from_dict(
            data,
            schema_version_expected=GENOME_SCHEMA_VERSION,
            genome_factory=lambda: cls.random(use_algorithm=use_algorithm, rng=rng),
            rng=rng,
        )
        return cast("Genome", genome)

    def debug_snapshot(self) -> dict[str, Any]:
        """Return a compact, stable dict for logging/debugging."""
        return genome_debug_snapshot(self)

    def validate(self) -> dict[str, Any]:
        """Validate trait ranges/types; returns a dict with any issues found."""
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
        """Raise GeneticsError if validation finds problems (debug aid)."""
        result = self.validate()
        if result["ok"]:
            return
        issues = "\n".join(result["issues"])
        raise GeneticsError(f"Invalid genome:\n{issues}")

    def normalize(
        self,
        *,
        rng: pyrandom.Random,
        code_pool: "GenomeCodePool | None" = None,
        soccer_enabled: bool = False,
    ) -> None:
        """Back-fill required fields a genome may be missing (idempotent).

        A fully-populated genome (the common case) is a no-op. This exists for
        genomes that reach a live fish without having gone through
        :meth:`random` with every flag set - older saves/migrations, or a
        caller that hand-builds a ``Genome`` - so the invariant "a genome is
        complete" lives on the genome itself rather than being re-implemented
        by every consumer that constructs or loads one.

        Consumes RNG only for the fields it actually has to fill, in this
        fixed order (poker strategy, then soccer policy): callers that care
        about exact RNG draw sequences (this project's determinism contract)
        must not reorder or split these checks.
        """
        if self.behavioral.poker_strategy is None or self.behavioral.poker_strategy.value is None:
            from core.poker.strategy.implementations import get_random_poker_strategy

            strategy = get_random_poker_strategy(rng=rng)
            if self.behavioral.poker_strategy is None:
                self.behavioral.poker_strategy = GeneticTrait(strategy)
            else:
                self.behavioral.poker_strategy.value = strategy

        if soccer_enabled:
            soccer_trait = self.behavioral.soccer_policy_id
            if soccer_trait is None or soccer_trait.value is None:
                if code_pool is not None:
                    default_id = code_pool.get_default(SOCCER_POLICY)
                    if default_id:
                        self.behavioral.soccer_policy_id = GeneticTrait(default_id)
                        self.behavioral.soccer_policy_params = GeneticTrait({})
                    else:
                        available = code_pool.get_components_by_kind(SOCCER_POLICY)
                        if available:
                            chosen = rng.choice(available)
                            self.behavioral.soccer_policy_id = GeneticTrait(chosen)
                            self.behavioral.soccer_policy_params = GeneticTrait({})

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def random(cls, use_algorithm: bool = True, rng: pyrandom.Random | None = None) -> "Genome":
        """Create a random genome."""
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
        rng: pyrandom.Random | None = None,
        available_policies: list[str] | None = None,
        diversity_score: float | None = None,
        mutation_context: ReproductionMutationContext | None = None,
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
            diversity_score=diversity_score,
            mutation_context=mutation_context,
        )

    @classmethod
    def from_parents_weighted(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        parent1_weight: float = 0.5,
        mutation_rate: float = 0.15,  # Increased from 0.1
        mutation_strength: float = 0.15,  # Increased from 0.1
        rng: pyrandom.Random | None = None,
        available_policies: list[str] | None = None,
        diversity_score: float | None = None,
        mutation_context: ReproductionMutationContext | None = None,
    ) -> "Genome":
        """Create offspring genome with weighted contributions from parents.

        This is the core inheritance method. The declarative trait system
        handles all the per-trait inheritance, eliminating hundreds of lines
        of duplicated code.
        """
        rng = require_rng_param(rng, "__init__")
        parent1_weight = max(0.0, min(1.0, parent1_weight))
        context = mutation_context or ReproductionMutationContext.from_score(diversity_score)
        adaptive_rate, adaptive_strength = ReproductionParams(
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
        ).adaptive_mutation(context)

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
            diversity_score=diversity_score,
            mutation_context=context,
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
        rng: pyrandom.Random | None = None,
        available_policies: list[str] | None = None,
        diversity_score: float | None = None,
        mutation_context: ReproductionMutationContext | None = None,
    ) -> "Genome":
        """Clone a genome with mutation (asexual reproduction)."""
        return cls.from_parents_weighted_params(
            parent1=parent,
            parent2=parent,
            parent1_weight=1.0,
            params=ReproductionParams(),
            rng=rng,
            available_policies=available_policies,
            diversity_score=diversity_score,
            mutation_context=mutation_context,
        )

    @classmethod
    def from_parents(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        mutation_rate: float = 0.15,  # Increased from 0.1
        mutation_strength: float = 0.15,  # Increased from 0.1
        crossover_mode: GeneticCrossoverMode = GeneticCrossoverMode.RECOMBINATION,
        rng: pyrandom.Random | None = None,
        available_policies: list[str] | None = None,
        diversity_score: float | None = None,
        mutation_context: ReproductionMutationContext | None = None,
        parent1_dominant: bool | None = None,
    ) -> "Genome":
        """Create offspring genome by mixing parent genes with mutations."""
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
                diversity_score=diversity_score,
                mutation_context=mutation_context,
            )

        if crossover_mode is GeneticCrossoverMode.DOMINANT_RECESSIVE:
            logger.debug(
                "crossover_mode=%s currently behaves like recombination", crossover_mode.value
            )

        context = mutation_context or ReproductionMutationContext.from_score(diversity_score)
        adaptive_rate, adaptive_strength = params.adaptive_mutation(context)

        physical = PhysicalTraits.from_parents_recombination(
            parent1.physical,
            parent2.physical,
            parent1_probability=0.5,
            mutation_rate=adaptive_rate,
            mutation_strength=adaptive_strength,
            rng=rng,
            parent1_dominant=parent1_dominant,
        )

        behavioral = BehavioralTraits.from_parents_recombination(
            parent1.behavioral,
            parent2.behavioral,
            parent1_probability=0.5,
            mutation_rate=adaptive_rate,
            mutation_strength=adaptive_strength,
            rng=rng,
            available_policies=available_policies,
            diversity_score=diversity_score,
            mutation_context=context,
            parent1_dominant=parent1_dominant,
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
        rng: pyrandom.Random | None = None,
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
        preferred physical trait values, behavioral trait preferences,
        plus a bonus for higher pattern intensity.
        """
        return expression.calculate_mate_attraction(
            self.physical, self.behavioral, other.physical, other.behavioral
        )

    def get_color_tint(self) -> tuple[int, int, int]:
        """Get RGB color tint based on genome."""
        return expression.calculate_color_tint(self.physical)
