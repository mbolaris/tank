"""Backward compatibility layer for Genome class.

This module provides a mixin class that exposes direct property accessors
for physical and behavioral traits, maintaining compatibility with code
that expects `genome.trait` instead of `genome.physical.trait.value`.
"""

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from core.algorithms import BehaviorAlgorithm
    from core.poker.strategy.implementations import PokerStrategyAlgorithm
    from core.genetics.physical import PhysicalTraits
    from core.genetics.behavioral import BehavioralTraits


class GenomeCompatibilityMixin:
    """Mixin providing backward compatibility properties for Genome.
    
    This allows access to trait values directly on the genome instance
    (e.g., genome.size_modifier) rather than through the nested structure
    (genome.physical.size_modifier.value).
    """
    
    # Type hints for the mixin to know about the main class attributes
    physical: "PhysicalTraits"
    behavioral: "BehavioralTraits"

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
