"""Genome class for fish artificial life simulation.

This module provides the core Genome class that represents the complete
genetic makeup of a fish, combining physical and behavioral traits.
"""

import random as pyrandom
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from core.evolution.mutation import calculate_adaptive_mutation_rate
from core.evolution.inheritance import inherit_learned_behaviors
from core.genetics.trait import GeneticTrait
from core.genetics.physical import PhysicalTraits
from core.genetics.behavioral import BehavioralTraits

if TYPE_CHECKING:
    from core.algorithms import BehaviorAlgorithm
    from core.poker.strategy.implementations import PokerStrategyAlgorithm


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
        learned_behaviors: Non-genetic learned adjustments (cultural evolution)
        epigenetic_modifiers: Environmental expression modifiers
    """

    physical: PhysicalTraits
    behavioral: BehavioralTraits

    # Learned behaviors and epigenetics (not strictly genetic)
    learned_behaviors: Dict[str, float] = field(default_factory=dict)
    epigenetic_modifiers: Dict[str, float] = field(default_factory=dict)

    # =========================================================================
    # Backward Compatibility Properties
    # =========================================================================
    # These properties provide direct access to trait values (genome.size_modifier)
    # instead of requiring genome.physical.size_modifier.value.
    # =========================================================================

    # --- Physical Traits ---
    @property
    def size_modifier(self) -> float:
        return self.physical.size_modifier.value

    @size_modifier.setter
    def size_modifier(self, v: float) -> None:
        self.physical.size_modifier.value = v

    @property
    def color_hue(self) -> float:
        return self.physical.color_hue.value

    @color_hue.setter
    def color_hue(self, v: float) -> None:
        self.physical.color_hue.value = v

    @property
    def template_id(self) -> int:
        return self.physical.template_id.value

    @template_id.setter
    def template_id(self, v: int) -> None:
        self.physical.template_id.value = v

    @property
    def fin_size(self) -> float:
        return self.physical.fin_size.value

    @fin_size.setter
    def fin_size(self, v: float) -> None:
        self.physical.fin_size.value = v

    @property
    def tail_size(self) -> float:
        return self.physical.tail_size.value

    @tail_size.setter
    def tail_size(self, v: float) -> None:
        self.physical.tail_size.value = v

    @property
    def body_aspect(self) -> float:
        return self.physical.body_aspect.value

    @body_aspect.setter
    def body_aspect(self, v: float) -> None:
        self.physical.body_aspect.value = v

    @property
    def eye_size(self) -> float:
        return self.physical.eye_size.value

    @eye_size.setter
    def eye_size(self, v: float) -> None:
        self.physical.eye_size.value = v

    @property
    def pattern_intensity(self) -> float:
        return self.physical.pattern_intensity.value

    @pattern_intensity.setter
    def pattern_intensity(self, v: float) -> None:
        self.physical.pattern_intensity.value = v

    @property
    def pattern_type(self) -> int:
        return self.physical.pattern_type.value

    @pattern_type.setter
    def pattern_type(self, v: int) -> None:
        self.physical.pattern_type.value = v

    # --- Behavioral Traits ---
    @property
    def aggression(self) -> float:
        return self.behavioral.aggression.value

    @aggression.setter
    def aggression(self, v: float) -> None:
        self.behavioral.aggression.value = v

    @property
    def social_tendency(self) -> float:
        return self.behavioral.social_tendency.value

    @social_tendency.setter
    def social_tendency(self, v: float) -> None:
        self.behavioral.social_tendency.value = v

    @property
    def pursuit_aggression(self) -> float:
        return self.behavioral.pursuit_aggression.value

    @pursuit_aggression.setter
    def pursuit_aggression(self, v: float) -> None:
        self.behavioral.pursuit_aggression.value = v

    @property
    def prediction_skill(self) -> float:
        return self.behavioral.prediction_skill.value

    @prediction_skill.setter
    def prediction_skill(self, v: float) -> None:
        self.behavioral.prediction_skill.value = v

    @property
    def hunting_stamina(self) -> float:
        return self.behavioral.hunting_stamina.value

    @hunting_stamina.setter
    def hunting_stamina(self, v: float) -> None:
        self.behavioral.hunting_stamina.value = v

    @property
    def asexual_reproduction_chance(self) -> float:
        return self.behavioral.asexual_reproduction_chance.value

    @asexual_reproduction_chance.setter
    def asexual_reproduction_chance(self, v: float) -> None:
        self.behavioral.asexual_reproduction_chance.value = v

    @property
    def behavior_algorithm(self) -> Optional["BehaviorAlgorithm"]:
        return self.behavioral.behavior_algorithm.value

    @behavior_algorithm.setter
    def behavior_algorithm(self, v: Optional["BehaviorAlgorithm"]) -> None:
        self.behavioral.behavior_algorithm.value = v

    @property
    def poker_algorithm(self) -> Optional["BehaviorAlgorithm"]:
        return self.behavioral.poker_algorithm.value

    @poker_algorithm.setter
    def poker_algorithm(self, v: Optional["BehaviorAlgorithm"]) -> None:
        self.behavioral.poker_algorithm.value = v

    @property
    def poker_strategy_algorithm(self) -> Optional["PokerStrategyAlgorithm"]:
        return self.behavioral.poker_strategy_algorithm.value

    @poker_strategy_algorithm.setter
    def poker_strategy_algorithm(self, v: Optional["PokerStrategyAlgorithm"]) -> None:
        self.behavioral.poker_strategy_algorithm.value = v

    @property
    def mate_preferences(self) -> Dict[str, float]:
        return self.behavioral.mate_preferences.value

    @mate_preferences.setter
    def mate_preferences(self, v: Dict[str, float]) -> None:
        self.behavioral.mate_preferences.value = v

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
