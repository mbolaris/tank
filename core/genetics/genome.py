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
from core.genetics.behavioral import BehavioralTraits, MATE_PREFERENCE_SPECS, normalize_mate_preferences
from core.genetics.genome_codec import genome_debug_snapshot, genome_from_dict, genome_to_dict
from core.genetics.physical import PhysicalTraits
from core.genetics.reproduction import ReproductionParams
from core.genetics.validation import validate_traits_from_specs

logger = logging.getLogger(__name__)
GENOME_SCHEMA_VERSION = 1
_TEMPLATE_SPEED_BONUS = {0: 1.0, 1: 1.2, 2: 0.8, 3: 1.0, 4: 0.9, 5: 1.1}
_SPEED_MODIFIER_MIN = 0.5
_SPEED_MODIFIER_MAX = 1.5
_METABOLISM_RATE_MIN = 0.5
_PATTERN_INTENSITY_BASELINE = 0.5
_PATTERN_INTENSITY_COST_WEIGHT = 0.3


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _normalized_similarity(
    value: float,
    target: float,
    min_value: float,
    max_value: float,
    *,
    circular: bool = False,
) -> float:
    span = max_value - min_value
    if span <= 0:
        return 1.0
    diff = abs(value - target)
    if circular:
        diff = diff % span
        diff = min(diff, span - diff)
    return 1.0 - min(diff / span, 1.0)


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
    """

    physical: PhysicalTraits
    behavioral: BehavioralTraits

    # Learned behaviors (not strictly genetic)
    learned_behaviors: Dict[str, float] = field(default_factory=dict)

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
        template_id = self.physical.template_id.value
        template_speed_bonus = _TEMPLATE_SPEED_BONUS.get(template_id, 1.0)
        propulsion = self.physical.fin_size.value * 0.4 + self.physical.tail_size.value * 0.6
        hydrodynamics = 1.0 - abs(self.physical.body_aspect.value - 0.8) * 0.5
        result = template_speed_bonus * propulsion * hydrodynamics
        result = _clamp(result, _SPEED_MODIFIER_MIN, _SPEED_MODIFIER_MAX)
        object.__setattr__(self, '_speed_modifier_cache', result)
        return result

    @property
    def vision_range(self) -> float:
        """Calculate vision range based on eye size."""
        return self.physical.eye_size.value

    @property
    def metabolism_rate(self) -> float:
        """Calculate metabolism rate based on physical traits (cached)."""
        if self._metabolism_rate_cache is not None:
            return self._metabolism_rate_cache
        cost = 1.0
        cost += (self.physical.size_modifier.value - 1.0) * 0.5
        cost += (self.speed_modifier - 1.0) * 0.8
        cost += (self.physical.eye_size.value - 1.0) * 0.3
        cost += (
            self.physical.pattern_intensity.value - _PATTERN_INTENSITY_BASELINE
        ) * _PATTERN_INTENSITY_COST_WEIGHT
        result = max(_METABOLISM_RATE_MIN, cost)
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
        return genome_to_dict(
            self,
            schema_version=GENOME_SCHEMA_VERSION,
            behavior_algorithm=behavior_algorithm,
            poker_algorithm=poker_algorithm,
            poker_strategy_algorithm=poker_strategy_algorithm,
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
        rng = rng or pyrandom
        return genome_from_dict(
            data,
            schema_version_expected=GENOME_SCHEMA_VERSION,
            genome_factory=lambda: cls.random(use_algorithm=use_algorithm, rng=rng),
            rng=rng,
        )

    def debug_snapshot(self) -> Dict[str, Any]:
        """Return a compact, stable dict for logging/debugging."""
        return genome_debug_snapshot(self)

    def validate(self) -> Dict[str, Any]:
        """Validate trait ranges/types; returns a dict with any issues found."""
        from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
        from core.genetics.physical import PHYSICAL_TRAIT_SPECS

        issues = []
        issues.extend(validate_traits_from_specs(PHYSICAL_TRAIT_SPECS, self.physical, path="genome.physical"))
        issues.extend(
            validate_traits_from_specs(BEHAVIORAL_TRAIT_SPECS, self.behavioral, path="genome.behavioral")
        )
        # Non-spec traits (broad checks only)
        if not isinstance(self.learned_behaviors, dict):
            issues.append(f"genome.learned_behaviors: expected dict, got {type(self.learned_behaviors).__name__}")

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
    def random(
        cls, use_algorithm: bool = True, rng: Optional[pyrandom.Random] = None
    ) -> "Genome":
        """Create a random genome."""
        rng = rng or pyrandom
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
    ) -> "Genome":
        """Create offspring genome using a parameter object for mutation inputs."""
        return cls.from_parents_weighted(
            parent1=parent1,
            parent2=parent2,
            parent1_weight=parent1_weight,
            mutation_rate=params.mutation_rate,
            mutation_strength=params.mutation_strength,
            rng=rng,
        )

    @classmethod
    def from_parents_weighted(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        parent1_weight: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        rng: Optional[pyrandom.Random] = None,
    ) -> "Genome":
        """Create offspring genome with weighted contributions from parents.

        This is the core inheritance method. The declarative trait system
        handles all the per-trait inheritance, eliminating hundreds of lines
        of duplicated code.
        """
        rng = rng or pyrandom
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
    ) -> "Genome":
        """Clone a genome with mutation (asexual reproduction)."""
        return cls.from_parents_weighted_params(
            parent1=parent,
            parent2=parent,
            parent1_weight=1.0,
            params=ReproductionParams(),
            rng=rng,
        )

    @classmethod
    def from_parents(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        crossover_mode: GeneticCrossoverMode = GeneticCrossoverMode.RECOMBINATION,
        rng: Optional[pyrandom.Random] = None,
    ) -> "Genome":
        """Create offspring genome by mixing parent genes with mutations."""
        rng = rng or pyrandom
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
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
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
        offspring = cls(
            physical=physical,
            behavioral=behavioral,
        )
        inherit_learned_behaviors(parent1, parent2, offspring)
        return offspring
    # =========================================================================
    # Instance Methods
    # =========================================================================

    def calculate_mate_compatibility(self, other: "Genome") -> float:
        """Calculate compatibility score with potential mate (0.0-1.0).

        Compatibility is based on how closely the mate matches this fish's
        preferred physical trait values, plus a bonus for higher pattern intensity.
        """
        raw_prefs = self.behavioral.mate_preferences.value
        preferences = raw_prefs if isinstance(raw_prefs, dict) else {}
        normalized_prefs = normalize_mate_preferences(
            preferences,
            physical=self.physical,
        )

        scores = []
        weights = []
        for trait_name, spec in MATE_PREFERENCE_SPECS.items():
            desired = normalized_prefs[trait_name]
            mate_value = getattr(other.physical, trait_name).value
            score = _normalized_similarity(
                mate_value,
                desired,
                spec.min_val,
                spec.max_val,
                circular=(trait_name == "color_hue"),
            )
            scores.append(score)
            weights.append(1.0)

        pattern_weight = normalized_prefs.get("prefer_high_pattern_intensity", 0.5)
        if pattern_weight > 0.0:
            scores.append(_clamp(other.physical.pattern_intensity.value, 0.0, 1.0))
            weights.append(pattern_weight)

        total_weight = sum(weights)
        if total_weight <= 0.0:
            return 0.0
        compatibility = sum(score * weight for score, weight in zip(scores, weights)) / total_weight
        return min(max(compatibility, 0.0), 1.0)

    def get_color_tint(self) -> Tuple[int, int, int]:
        """Get RGB color tint based on genome."""
        hue = self.physical.color_hue.value * 360
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
