"""Genome class for fish artificial life simulation.

This module provides the core Genome class that represents the complete
genetic makeup of a fish, combining physical and behavioral traits.
"""

import logging
import random as pyrandom
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from core.evolution.inheritance import inherit_learned_behaviors
from core.evolution.mutation import calculate_adaptive_mutation_rate
from core.genetics.behavioral import BehavioralTraits
from core.genetics.compatibility import GenomeCompatibilityMixin
from core.genetics.physical import PhysicalTraits
from core.genetics.trait import (
    apply_trait_meta_from_dict,
    apply_trait_values_from_dict,
    trait_meta_to_dict,
    trait_values_to_dict,
)

logger = logging.getLogger(__name__)
GENOME_SCHEMA_VERSION = 1


class GeneticCrossoverMode(Enum):
    """Different modes for genetic crossover during reproduction."""

    AVERAGING = "averaging"
    RECOMBINATION = "recombination"
    DOMINANT_RECESSIVE = "dominant_recessive"


@dataclass
class Genome(GenomeCompatibilityMixin):
    """Represents the complete genetic makeup of a fish.

    Attributes:
        physical: Physical appearance traits
        behavioral: Behavioral and decision-making traits
        learned_behaviors: Non-genetic learned adjustments (cultural evolution)
        epigenetic_modifiers: Environmental expression modifiers
    """

    physical: PhysicalTraits
    behavioral: BehavioralTraits

    # Learned behaviors and epigenetics (not strictly genetic)
    learned_behaviors: Dict[str, float] = field(default_factory=dict)
    epigenetic_modifiers: Dict[str, float] = field(default_factory=dict)

    # Backward compatibility properties are provided by GenomeCompatibilityMixin

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
        template_speed_bonus = {0: 1.0, 1: 1.2, 2: 0.8, 3: 1.0, 4: 0.9, 5: 1.1}.get(
            self.template_id, 1.0
        )
        propulsion = self.fin_size * 0.4 + self.tail_size * 0.6
        hydrodynamics = 1.0 - abs(self.body_aspect - 0.8) * 0.5
        result = template_speed_bonus * propulsion * hydrodynamics
        object.__setattr__(self, '_speed_modifier_cache', result)
        return result

    @property
    def vision_range(self) -> float:
        """Calculate vision range based on eye size."""
        return self.eye_size

    @property
    def metabolism_rate(self) -> float:
        """Calculate metabolism rate based on physical traits (cached)."""
        if self._metabolism_rate_cache is not None:
            return self._metabolism_rate_cache
        cost = 1.0
        cost += (self.size_modifier - 1.0) * 0.5
        cost += (self.speed_modifier - 1.0) * 0.8
        cost += (self.eye_size - 1.0) * 0.3
        result = max(0.5, cost)
        object.__setattr__(self, '_metabolism_rate_cache', result)
        return result

    def invalidate_caches(self) -> None:
        """Invalidate cached computed properties when traits change."""
        object.__setattr__(self, '_speed_modifier_cache', None)
        object.__setattr__(self, '_metabolism_rate_cache', None)

    def to_dict(
        self,
        *,
        behavior_algorithm: Optional[Dict[str, Any]] = None,
        poker_algorithm: Optional[Dict[str, Any]] = None,
        poker_strategy_algorithm: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Serialize this genome into JSON-compatible primitives.

        This is intended as a stable boundary format for persistence and transfer.
        """

        behavior_algorithm_dict = behavior_algorithm
        if behavior_algorithm_dict is None and self.behavior_algorithm is not None:
            behavior_algorithm_dict = self.behavior_algorithm.to_dict()

        poker_algorithm_dict = poker_algorithm
        if poker_algorithm_dict is None and self.poker_algorithm is not None:
            poker_algorithm_dict = self.poker_algorithm.to_dict()

        poker_strategy_dict = poker_strategy_algorithm
        if poker_strategy_dict is None and self.poker_strategy_algorithm is not None:
            poker_strategy_dict = self.poker_strategy_algorithm.to_dict()

        from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
        from core.genetics.physical import PHYSICAL_TRAIT_SPECS

        values: Dict[str, Any] = {}
        values.update(trait_values_to_dict(PHYSICAL_TRAIT_SPECS, self.physical))
        values.update(trait_values_to_dict(BEHAVIORAL_TRAIT_SPECS, self.behavioral))

        trait_meta: Dict[str, Dict[str, float]] = {}
        trait_meta.update(trait_meta_to_dict(PHYSICAL_TRAIT_SPECS, self.physical))
        trait_meta.update(trait_meta_to_dict(BEHAVIORAL_TRAIT_SPECS, self.behavioral))

        def _maybe_add_meta(name: str, trait: Any) -> None:
            meta: Dict[str, float] = {}
            if trait.mutation_rate != 1.0:
                meta["mutation_rate"] = float(trait.mutation_rate)
            if trait.mutation_strength != 1.0:
                meta["mutation_strength"] = float(trait.mutation_strength)
            if trait.hgt_probability != 0.1:
                meta["hgt_probability"] = float(trait.hgt_probability)
            if meta:
                trait_meta[name] = meta

        _maybe_add_meta("behavior_algorithm", self.behavioral.behavior_algorithm)
        _maybe_add_meta("poker_algorithm", self.behavioral.poker_algorithm)
        _maybe_add_meta("poker_strategy_algorithm", self.behavioral.poker_strategy_algorithm)
        _maybe_add_meta("mate_preferences", self.behavioral.mate_preferences)

        return {
            "schema_version": GENOME_SCHEMA_VERSION,
            **values,
            # Behavioral complex traits
            "behavior_algorithm": behavior_algorithm_dict,
            "poker_algorithm": poker_algorithm_dict,
            "poker_strategy_algorithm": poker_strategy_dict,
            "mate_preferences": dict(self.behavioral.mate_preferences.value),
            # Non-genetic (but persistable) state
            "learned_behaviors": dict(self.learned_behaviors),
            "epigenetic_modifiers": dict(self.epigenetic_modifiers),
            "trait_meta": trait_meta,
        }

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

        rng = rng or pyrandom
        genome = cls.random(use_algorithm=use_algorithm, rng=rng)

        from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
        from core.genetics.physical import PHYSICAL_TRAIT_SPECS

        apply_trait_values_from_dict(PHYSICAL_TRAIT_SPECS, genome.physical, data)
        apply_trait_values_from_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral, data)

        # Mate preferences (dictionary trait)
        mate_preferences = data.get("mate_preferences")
        if isinstance(mate_preferences, dict):
            genome.mate_preferences = {
                str(key): float(value) for key, value in mate_preferences.items()
            }

        # Evolvability metadata (mutation_rate/mutation_strength/hgt_probability)
        trait_meta = data.get("trait_meta")
        if isinstance(trait_meta, dict):
            try:
                apply_trait_meta_from_dict(PHYSICAL_TRAIT_SPECS, genome.physical, trait_meta)
                apply_trait_meta_from_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral, trait_meta)
            except Exception:
                logger.debug("Failed applying trait_meta; continuing with defaults", exc_info=True)

            # Apply metadata for non-spec traits on BehavioralTraits.
            meta = trait_meta.get("behavior_algorithm")
            if isinstance(meta, dict):
                if "mutation_rate" in meta:
                    genome.behavioral.behavior_algorithm.mutation_rate = max(0.0, float(meta["mutation_rate"]))
                if "mutation_strength" in meta:
                    genome.behavioral.behavior_algorithm.mutation_strength = max(
                        0.0, float(meta["mutation_strength"])
                    )
                if "hgt_probability" in meta:
                    genome.behavioral.behavior_algorithm.hgt_probability = max(
                        0.0, min(1.0, float(meta["hgt_probability"]))
                    )
            meta = trait_meta.get("poker_algorithm")
            if isinstance(meta, dict):
                if "mutation_rate" in meta:
                    genome.behavioral.poker_algorithm.mutation_rate = max(0.0, float(meta["mutation_rate"]))
                if "mutation_strength" in meta:
                    genome.behavioral.poker_algorithm.mutation_strength = max(
                        0.0, float(meta["mutation_strength"])
                    )
                if "hgt_probability" in meta:
                    genome.behavioral.poker_algorithm.hgt_probability = max(
                        0.0, min(1.0, float(meta["hgt_probability"]))
                    )
            meta = trait_meta.get("poker_strategy_algorithm")
            if isinstance(meta, dict):
                if "mutation_rate" in meta:
                    genome.behavioral.poker_strategy_algorithm.mutation_rate = max(
                        0.0, float(meta["mutation_rate"])
                    )
                if "mutation_strength" in meta:
                    genome.behavioral.poker_strategy_algorithm.mutation_strength = max(
                        0.0, float(meta["mutation_strength"])
                    )
                if "hgt_probability" in meta:
                    genome.behavioral.poker_strategy_algorithm.hgt_probability = max(
                        0.0, min(1.0, float(meta["hgt_probability"]))
                    )
            meta = trait_meta.get("mate_preferences")
            if isinstance(meta, dict):
                if "mutation_rate" in meta:
                    genome.behavioral.mate_preferences.mutation_rate = max(
                        0.0, float(meta["mutation_rate"])
                    )
                if "mutation_strength" in meta:
                    genome.behavioral.mate_preferences.mutation_strength = max(
                        0.0, float(meta["mutation_strength"])
                    )
                if "hgt_probability" in meta:
                    genome.behavioral.mate_preferences.hgt_probability = max(
                        0.0, min(1.0, float(meta["hgt_probability"]))
                    )

        # Non-genetic (but persistable) state
        learned = data.get("learned_behaviors")
        if isinstance(learned, dict):
            genome.learned_behaviors = {str(key): float(value) for key, value in learned.items()}
        epigenetic = data.get("epigenetic_modifiers")
        if isinstance(epigenetic, dict):
            genome.epigenetic_modifiers = {
                str(key): float(value) for key, value in epigenetic.items()
            }

        # Algorithms
        try:
            from core.algorithms import behavior_from_dict

            behavior_data = data.get("behavior_algorithm")
            if behavior_data:
                genome.behavior_algorithm = behavior_from_dict(behavior_data)
                if genome.behavior_algorithm is None:
                    logger.warning("Failed to deserialize behavior_algorithm; keeping default")

            poker_data = data.get("poker_algorithm")
            if poker_data:
                genome.poker_algorithm = behavior_from_dict(poker_data)
                if genome.poker_algorithm is None:
                    logger.warning("Failed to deserialize poker_algorithm; keeping default")
        except Exception:
            logger.debug("Failed deserializing behavior algorithms; keeping defaults", exc_info=True)

        try:
            strat_data = data.get("poker_strategy_algorithm")
            if strat_data:
                from core.poker.strategy.implementations import PokerStrategyAlgorithm

                genome.poker_strategy_algorithm = PokerStrategyAlgorithm.from_dict(strat_data)
        except Exception:
            logger.debug("Failed deserializing poker_strategy_algorithm; keeping default", exc_info=True)

        genome.invalidate_caches()
        return genome

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def random(
        cls, use_algorithm: bool = True, rng: Optional[pyrandom.Random] = None
    ) -> "Genome":
        """Create a random genome."""
        rng = rng or pyrandom
        return cls(
            physical=PhysicalTraits.random(rng),
            behavioral=BehavioralTraits.random(rng, use_algorithm),
        )

    @classmethod
    def from_parents_weighted(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        parent1_weight: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        population_stress: float = 0.0,
        rng: Optional[pyrandom.Random] = None,
    ) -> "Genome":
        """Create offspring genome with weighted contributions from parents.

        This is the core inheritance method. The declarative trait system
        handles all the per-trait inheritance, eliminating hundreds of lines
        of duplicated code.
        """
        rng = rng or pyrandom
        parent1_weight = max(0.0, min(1.0, parent1_weight))
        adaptive_rate, adaptive_strength = calculate_adaptive_mutation_rate(
            mutation_rate, mutation_strength, population_stress
        )

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
        )

        # Inherit epigenetics
        epigenetic = _inherit_epigenetics(
            parent1.epigenetic_modifiers,
            parent2.epigenetic_modifiers,
            parent1_weight,
            rng,
        )

        offspring = cls(
            physical=physical, behavioral=behavioral, epigenetic_modifiers=epigenetic
        )
        inherit_learned_behaviors(parent1, parent2, offspring)
        return offspring

    @classmethod
    def clone_with_mutation(
        cls,
        parent: "Genome",
        population_stress: float = 0.0,
        rng: Optional[pyrandom.Random] = None,
    ) -> "Genome":
        """Clone a genome with mutation (asexual reproduction)."""
        return cls.from_parents_weighted(
            parent1=parent,
            parent2=parent,
            parent1_weight=1.0,
            population_stress=population_stress,
            rng=rng,
        )

    @classmethod
    def from_parents(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        population_stress: float = 0.0,
        crossover_mode: GeneticCrossoverMode = GeneticCrossoverMode.RECOMBINATION,
        rng: Optional[pyrandom.Random] = None,
    ) -> "Genome":
        """Create offspring genome by mixing parent genes with mutations."""
        # All crossover modes currently delegate to weighted blend with 50/50 split
        return cls.from_parents_weighted(
            parent1,
            parent2,
            0.5,
            mutation_rate,
            mutation_strength,
            population_stress,
            rng,
        )

    @classmethod
    def from_winner_choice(
        cls,
        winner: "Genome",
        mate: "Genome",
        population_stress: float = 0.0,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        rng: Optional[pyrandom.Random] = None,
    ) -> "Genome":
        """Create offspring where winner selectively borrows mate traits.

        The winner genome uses its hgt_probability to decide which traits
        to take from the mate vs keep from self.
        """
        # Winner-based inheritance uses 80/20 weighting favoring winner
        return cls.from_parents_weighted(
            parent1=winner,
            parent2=mate,
            parent1_weight=0.8,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            population_stress=population_stress,
            rng=rng,
        )

    # =========================================================================
    # Instance Methods
    # =========================================================================

    def calculate_mate_compatibility(self, other: "Genome") -> float:
        """Calculate compatibility score with potential mate (0.0-1.0)."""
        compatibility = 0.0

        # Size similarity preference
        size_diff = abs(self.size_modifier - other.size_modifier)
        size_score = 1.0 - min(size_diff / 0.6, 1.0)
        compatibility += self.mate_preferences.get("prefer_similar_size", 0.5) * size_score * 0.3

        # Color diversity preference
        color_diff = abs(self.color_hue - other.color_hue)
        color_score = min(color_diff / 0.5, 1.0)
        compatibility += (
            self.mate_preferences.get("prefer_different_color", 0.5) * color_score * 0.3
        )

        # General genetic diversity
        trait_variance = (
            abs(self.speed_modifier - other.speed_modifier)
            + abs(self.metabolism_rate - other.metabolism_rate)
            + abs(self.vision_range - other.vision_range)
        ) / 3.0
        compatibility += min(trait_variance / 0.3, 1.0) * 0.4

        return min(compatibility, 1.0)

    def get_color_tint(self) -> Tuple[int, int, int]:
        """Get RGB color tint based on genome."""
        hue = self.color_hue * 360
        if hue < 60:
            r, g, b = 255, int(hue / 60 * 255), 0
        elif hue < 120:
            r, g, b = int((120 - hue) / 60 * 255), 255, 0
        elif hue < 180:
            r, g, b = 0, 255, int((hue - 120) / 60 * 255)
        elif hue < 240:
            r, g, b = 0, int((240 - hue) / 60 * 255), 255
        elif hue < 300:
            r, g, b = int((hue - 240) / 60 * 255), 0, 255
        else:
            r, g, b = 255, 0, int((360 - hue) / 60 * 255)

        saturation = 0.3
        r = int(r * saturation + 255 * (1 - saturation))
        g = int(g * saturation + 255 * (1 - saturation))
        b = int(b * saturation + 255 * (1 - saturation))
        return (r, g, b)


def _inherit_epigenetics(
    mods1: Dict[str, float],
    mods2: Dict[str, float],
    weight1: float,
    rng: pyrandom.Random,
) -> Dict[str, float]:
    """Inherit epigenetic modifiers from parents."""
    epigenetic = {}
    if mods1 or mods2:
        for modifier_key in set(list(mods1.keys()) + list(mods2.keys())):
            p1_val = mods1.get(modifier_key, 0.0)
            p2_val = mods2.get(modifier_key, 0.0)
            weighted_val = p1_val * weight1 + p2_val * (1.0 - weight1)
            if abs(weighted_val) > 0.01:
                epigenetic[modifier_key] = weighted_val * 0.5
    return epigenetic
