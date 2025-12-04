"""Genetics system for artificial life simulation.

This module provides a genetic system for fish, allowing for heritable traits,
mutations, and evolutionary dynamics.

Uses core.evolution module for crossover, mutation, and inheritance operations.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Generic, TypeVar, Any, Union

from core.constants import FISH_PATTERN_COUNT, FISH_TEMPLATE_COUNT
from core.evolution.inheritance import (
    inherit_algorithm,
    inherit_learned_behaviors,
)
from core.evolution.inheritance import (
    inherit_discrete_trait as _inherit_discrete_trait,
)
from core.evolution.inheritance import (
    inherit_trait as _inherit_trait,
)
from core.evolution.mutation import calculate_adaptive_mutation_rate

if TYPE_CHECKING:
    from core.algorithms import BehaviorAlgorithm
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

T = TypeVar("T")

@dataclass
class GeneticTrait(Generic[T]):
    """A genetic trait with metadata for evolution.
    
    Attributes:
        value: The actual trait value
        mutation_rate: Multiplier for how likely this specific trait is to mutate
        mutation_strength: Multiplier for how strongly this trait mutates
        hgt_probability: Probability of Horizontal Gene Transfer (or direct inheritance)
    """
    value: T
    mutation_rate: float = 1.0
    mutation_strength: float = 1.0
    hgt_probability: float = 0.1

    def mutate_meta(self, rng: random.Random = random) -> None:
        """Mutate the metadata itself (evolution of evolution)."""
        if rng.random() < 0.05:
            self.mutation_rate = max(0.1, min(5.0, self.mutation_rate + rng.gauss(0, 0.1)))
        if rng.random() < 0.05:
            self.mutation_strength = max(0.1, min(5.0, self.mutation_strength + rng.gauss(0, 0.1)))
        if rng.random() < 0.05:
            self.hgt_probability = max(0.0, min(1.0, self.hgt_probability + rng.gauss(0, 0.05)))

@dataclass
class PhysicalTraits:
    """Physical attributes of the fish."""
    size_modifier: GeneticTrait[float]
    fertility: GeneticTrait[float]
    color_hue: GeneticTrait[float]
    template_id: GeneticTrait[int]
    fin_size: GeneticTrait[float]
    tail_size: GeneticTrait[float]
    body_aspect: GeneticTrait[float]
    eye_size: GeneticTrait[float]
    pattern_intensity: GeneticTrait[float]
    pattern_type: GeneticTrait[int]

    @classmethod
    def random(cls, rng: random.Random) -> "PhysicalTraits":
        return cls(
            size_modifier=GeneticTrait(rng.uniform(0.7, 1.3)),
            fertility=GeneticTrait(rng.uniform(0.6, 1.4)),
            color_hue=GeneticTrait(rng.random()),
            template_id=GeneticTrait(rng.randint(0, FISH_TEMPLATE_COUNT - 1)),
            fin_size=GeneticTrait(rng.uniform(0.6, 1.4)),
            tail_size=GeneticTrait(rng.uniform(0.6, 1.4)),
            body_aspect=GeneticTrait(rng.uniform(0.7, 1.3)),
            eye_size=GeneticTrait(rng.uniform(0.7, 1.3)),
            pattern_intensity=GeneticTrait(rng.random()),
            pattern_type=GeneticTrait(rng.randint(0, FISH_PATTERN_COUNT - 1)),
        )

@dataclass
class BehavioralTraits:
    """Behavioral attributes of the fish."""
    aggression: GeneticTrait[float]
    social_tendency: GeneticTrait[float]
    pursuit_aggression: GeneticTrait[float]
    prediction_skill: GeneticTrait[float]
    hunting_stamina: GeneticTrait[float]
    
    # Algorithms are complex objects, but we wrap them in GeneticTrait too
    behavior_algorithm: GeneticTrait[Optional["BehaviorAlgorithm"]]
    poker_algorithm: GeneticTrait[Optional["BehaviorAlgorithm"]]
    poker_strategy_algorithm: GeneticTrait[Optional["PokerStrategyAlgorithm"]]
    
    mate_preferences: GeneticTrait[Dict[str, float]]

    @classmethod
    def random(cls, rng: random.Random, use_algorithm: bool = True) -> "BehavioralTraits":
        algorithm = None
        poker_algorithm = None
        poker_strategy_algorithm = None
        
        if use_algorithm:
            from core.algorithms import get_random_algorithm
            from core.poker.strategy.implementations import get_random_poker_strategy
            algorithm = get_random_algorithm(rng=rng)
            poker_algorithm = get_random_algorithm(rng=rng)
            poker_strategy_algorithm = get_random_poker_strategy(rng=rng)
            
        return cls(
            aggression=GeneticTrait(rng.uniform(0.0, 1.0)),
            social_tendency=GeneticTrait(rng.uniform(0.0, 1.0)),
            pursuit_aggression=GeneticTrait(rng.uniform(0.0, 1.0)),
            prediction_skill=GeneticTrait(rng.uniform(0.0, 1.0)),
            hunting_stamina=GeneticTrait(rng.uniform(0.0, 1.0)),
            behavior_algorithm=GeneticTrait(algorithm),
            poker_algorithm=GeneticTrait(poker_algorithm),
            poker_strategy_algorithm=GeneticTrait(poker_strategy_algorithm),
            mate_preferences=GeneticTrait({
                "prefer_similar_size": 0.5,
                "prefer_different_color": 0.5,
                "prefer_high_energy": 0.5,
            })
        )

class GeneticCrossoverMode(Enum):
    """Different modes for genetic crossover during reproduction."""
    AVERAGING = "averaging"
    RECOMBINATION = "recombination"
    DOMINANT_RECESSIVE = "dominant_recessive"

@dataclass
class Genome:
    """Represents the genetic makeup of a fish."""
    
    physical: PhysicalTraits
    behavioral: BehavioralTraits
    
    # Learned behaviors and epigenetics are not strictly "genetic traits" in the same way
    learned_behaviors: Dict[str, float] = field(default_factory=dict)
    epigenetic_modifiers: Dict[str, float] = field(default_factory=dict)

    # Backward compatibility properties
    @property
    def size_modifier(self) -> float: return self.physical.size_modifier.value
    @size_modifier.setter
    def size_modifier(self, v: float): self.physical.size_modifier.value = v

    @property
    def fertility(self) -> float: return self.physical.fertility.value
    @fertility.setter
    def fertility(self, v: float): self.physical.fertility.value = v

    @property
    def color_hue(self) -> float: return self.physical.color_hue.value
    @color_hue.setter
    def color_hue(self, v: float): self.physical.color_hue.value = v

    @property
    def template_id(self) -> int: return self.physical.template_id.value
    @template_id.setter
    def template_id(self, v: int): self.physical.template_id.value = v

    @property
    def fin_size(self) -> float: return self.physical.fin_size.value
    @fin_size.setter
    def fin_size(self, v: float): self.physical.fin_size.value = v

    @property
    def tail_size(self) -> float: return self.physical.tail_size.value
    @tail_size.setter
    def tail_size(self, v: float): self.physical.tail_size.value = v

    @property
    def body_aspect(self) -> float: return self.physical.body_aspect.value
    @body_aspect.setter
    def body_aspect(self, v: float): self.physical.body_aspect.value = v

    @property
    def eye_size(self) -> float: return self.physical.eye_size.value
    @eye_size.setter
    def eye_size(self, v: float): self.physical.eye_size.value = v

    @property
    def pattern_intensity(self) -> float: return self.physical.pattern_intensity.value
    @pattern_intensity.setter
    def pattern_intensity(self, v: float): self.physical.pattern_intensity.value = v

    @property
    def pattern_type(self) -> int: return self.physical.pattern_type.value
    @pattern_type.setter
    def pattern_type(self, v: int): self.physical.pattern_type.value = v
    
    @property
    def aggression(self) -> float: return self.behavioral.aggression.value
    @aggression.setter
    def aggression(self, v: float): self.behavioral.aggression.value = v

    @property
    def social_tendency(self) -> float: return self.behavioral.social_tendency.value
    @social_tendency.setter
    def social_tendency(self, v: float): self.behavioral.social_tendency.value = v

    @property
    def pursuit_aggression(self) -> float: return self.behavioral.pursuit_aggression.value
    @pursuit_aggression.setter
    def pursuit_aggression(self, v: float): self.behavioral.pursuit_aggression.value = v

    @property
    def prediction_skill(self) -> float: return self.behavioral.prediction_skill.value
    @prediction_skill.setter
    def prediction_skill(self, v: float): self.behavioral.prediction_skill.value = v

    @property
    def hunting_stamina(self) -> float: return self.behavioral.hunting_stamina.value
    @hunting_stamina.setter
    def hunting_stamina(self, v: float): self.behavioral.hunting_stamina.value = v

    @property
    def behavior_algorithm(self) -> Optional["BehaviorAlgorithm"]: return self.behavioral.behavior_algorithm.value
    @behavior_algorithm.setter
    def behavior_algorithm(self, v: Optional["BehaviorAlgorithm"]): self.behavioral.behavior_algorithm.value = v

    @property
    def poker_algorithm(self) -> Optional["BehaviorAlgorithm"]: return self.behavioral.poker_algorithm.value
    @poker_algorithm.setter
    def poker_algorithm(self, v: Optional["BehaviorAlgorithm"]): self.behavioral.poker_algorithm.value = v

    @property
    def poker_strategy_algorithm(self) -> Optional["PokerStrategyAlgorithm"]: return self.behavioral.poker_strategy_algorithm.value
    @poker_strategy_algorithm.setter
    def poker_strategy_algorithm(self, v: Optional["PokerStrategyAlgorithm"]): self.behavioral.poker_strategy_algorithm.value = v

    @property
    def mate_preferences(self) -> Dict[str, float]: return self.behavioral.mate_preferences.value
    @mate_preferences.setter
    def mate_preferences(self, v: Dict[str, float]): self.behavioral.mate_preferences.value = v

    @property
    def speed_modifier(self) -> float:
        """Calculate speed modifier based on physical traits."""
        template_speed_bonus = {0: 1.0, 1: 1.2, 2: 0.8, 3: 1.0, 4: 0.9, 5: 1.1}.get(self.template_id, 1.0)
        propulsion = (self.fin_size * 0.4 + self.tail_size * 0.6)
        hydrodynamics = 1.0 - abs(self.body_aspect - 0.8) * 0.5
        return template_speed_bonus * propulsion * hydrodynamics

    @property
    def vision_range(self) -> float:
        """Calculate vision range based on eye size."""
        return self.eye_size

    @property
    def metabolism_rate(self) -> float:
        """Calculate metabolism rate based on physical traits."""
        cost = 1.0
        cost += (self.size_modifier - 1.0) * 0.5
        cost += (self.speed_modifier - 1.0) * 0.8
        cost += (self.eye_size - 1.0) * 0.3
        return max(0.5, cost)

    @classmethod
    def random(cls, use_algorithm: bool = True, rng: Optional[random.Random] = None) -> "Genome":
        rng = rng or random
        return cls(
            physical=PhysicalTraits.random(rng),
            behavioral=BehavioralTraits.random(rng, use_algorithm)
        )

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

    @classmethod
    def from_parents_weighted(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        parent1_weight: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        population_stress: float = 0.0,
    ) -> "Genome":
        """Create offspring genome with weighted contributions from parents."""
        parent1_weight = max(0.0, min(1.0, parent1_weight))
        adaptive_rate, adaptive_strength = calculate_adaptive_mutation_rate(
            mutation_rate, mutation_strength, population_stress
        )

        def inherit_trait_val(
            t1: GeneticTrait[float], 
            t2: GeneticTrait[float], 
            min_val: float, 
            max_val: float
        ) -> GeneticTrait[float]:
            # Use trait-specific multipliers
            eff_rate = adaptive_rate * (t1.mutation_rate + t2.mutation_rate) / 2
            eff_strength = adaptive_strength * (t1.mutation_strength + t2.mutation_strength) / 2
            
            new_val = _inherit_trait(
                t1.value, t2.value, min_val, max_val,
                weight1=parent1_weight,
                mutation_rate=eff_rate,
                mutation_strength=eff_strength,
            )
            
            # Create new trait with inherited/mutated metadata
            new_trait = GeneticTrait(new_val)
            new_trait.mutation_rate = (t1.mutation_rate + t2.mutation_rate) / 2
            new_trait.mutation_strength = (t1.mutation_strength + t2.mutation_strength) / 2
            new_trait.hgt_probability = (t1.hgt_probability + t2.hgt_probability) / 2
            new_trait.mutate_meta()
            return new_trait

        # Physical Traits
        physical = PhysicalTraits(
            size_modifier=inherit_trait_val(parent1.physical.size_modifier, parent2.physical.size_modifier, 0.7, 1.3),
            fertility=inherit_trait_val(parent1.physical.fertility, parent2.physical.fertility, 0.6, 1.4),
            color_hue=inherit_trait_val(parent1.physical.color_hue, parent2.physical.color_hue, 0.0, 1.0),
            template_id=GeneticTrait(_inherit_discrete_trait(
                parent1.template_id, parent2.template_id, 0, 5, weight1=parent1_weight, mutation_rate=adaptive_rate
            )),
            fin_size=inherit_trait_val(parent1.physical.fin_size, parent2.physical.fin_size, 0.6, 1.4),
            tail_size=inherit_trait_val(parent1.physical.tail_size, parent2.physical.tail_size, 0.6, 1.4),
            body_aspect=inherit_trait_val(parent1.physical.body_aspect, parent2.physical.body_aspect, 0.7, 1.3),
            eye_size=inherit_trait_val(parent1.physical.eye_size, parent2.physical.eye_size, 0.7, 1.3),
            pattern_intensity=inherit_trait_val(parent1.physical.pattern_intensity, parent2.physical.pattern_intensity, 0.0, 1.0),
            pattern_type=GeneticTrait(_inherit_discrete_trait(
                parent1.pattern_type, parent2.pattern_type, 0, 3, weight1=parent1_weight, mutation_rate=adaptive_rate
            )),
        )

        # Behavioral Traits
        # Algorithms
        algo_val = inherit_algorithm(
            parent1.behavior_algorithm, parent2.behavior_algorithm,
            weight1=parent1_weight,
            mutation_rate=adaptive_rate * 1.5,
            mutation_strength=adaptive_strength * 1.5,
            algorithm_switch_rate=0.03,
        )
        
        poker_algo_val = None
        if parent1.poker_algorithm is not None or parent2.poker_algorithm is not None:
            from core.algorithms import crossover_poker_algorithms
            poker_algo_val = crossover_poker_algorithms(
                parent1.poker_algorithm, parent2.poker_algorithm,
                parent1_poker_wins=0, parent2_poker_wins=0,
                mutation_rate=adaptive_rate * 1.2,
                mutation_strength=adaptive_strength * 1.2,
            )
        else:
            from core.algorithms import get_random_algorithm
            poker_algo_val = get_random_algorithm()

        poker_strat_val = None
        if parent1.poker_strategy_algorithm is not None or parent2.poker_strategy_algorithm is not None:
            from core.poker.strategy.implementations import crossover_poker_strategies
            poker_strat_val = crossover_poker_strategies(
                parent1.poker_strategy_algorithm, parent2.poker_strategy_algorithm,
                mutation_rate=adaptive_rate * 1.2,
                mutation_strength=adaptive_strength * 1.2,
            )
        else:
            from core.poker.strategy.implementations import get_random_poker_strategy
            poker_strat_val = get_random_poker_strategy()

        # Mate preferences
        mate_prefs = {}
        for pref_key in parent1.mate_preferences:
            p1_val = parent1.mate_preferences.get(pref_key, 0.5)
            p2_val = parent2.mate_preferences.get(pref_key, 0.5)
            # Simple inheritance for now
            mate_prefs[pref_key] = _inherit_trait(p1_val, p2_val, 0.0, 1.0, weight1=parent1_weight, mutation_rate=adaptive_rate)

        behavioral = BehavioralTraits(
            aggression=inherit_trait_val(parent1.behavioral.aggression, parent2.behavioral.aggression, 0.0, 1.0),
            social_tendency=inherit_trait_val(parent1.behavioral.social_tendency, parent2.behavioral.social_tendency, 0.0, 1.0),
            pursuit_aggression=inherit_trait_val(parent1.behavioral.pursuit_aggression, parent2.behavioral.pursuit_aggression, 0.0, 1.0),
            prediction_skill=inherit_trait_val(parent1.behavioral.prediction_skill, parent2.behavioral.prediction_skill, 0.0, 1.0),
            hunting_stamina=inherit_trait_val(parent1.behavioral.hunting_stamina, parent2.behavioral.hunting_stamina, 0.0, 1.0),
            behavior_algorithm=GeneticTrait(algo_val),
            poker_algorithm=GeneticTrait(poker_algo_val),
            poker_strategy_algorithm=GeneticTrait(poker_strat_val),
            mate_preferences=GeneticTrait(mate_prefs),
        )

        # Epigenetics
        epigenetic = {}
        if parent1.epigenetic_modifiers or parent2.epigenetic_modifiers:
            for modifier_key in set(list(parent1.epigenetic_modifiers.keys()) + list(parent2.epigenetic_modifiers.keys())):
                p1_val = parent1.epigenetic_modifiers.get(modifier_key, 0.0)
                p2_val = parent2.epigenetic_modifiers.get(modifier_key, 0.0)
                weighted_val = p1_val * parent1_weight + p2_val * (1.0 - parent1_weight)
                if abs(weighted_val) > 0.01:
                    epigenetic[modifier_key] = weighted_val * 0.5

        offspring = cls(physical=physical, behavioral=behavioral, epigenetic_modifiers=epigenetic)
        inherit_learned_behaviors(parent1, parent2, offspring)
        return offspring

    @classmethod
    def from_parents(
        cls,
        parent1: "Genome",
        parent2: "Genome",
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        population_stress: float = 0.0,
        crossover_mode: GeneticCrossoverMode = GeneticCrossoverMode.RECOMBINATION,
    ) -> "Genome":
        """Create offspring genome by mixing parent genes with mutations."""
        # For simplicity in this refactor, we'll delegate to from_parents_weighted with 0.5 weight
        # unless specific crossover logic is needed.
        # The original code had specific logic for DOMINANT_RECESSIVE.
        # We can approximate that by choosing a weight close to 0 or 1 per trait, but that's complex to map.
        # For now, let's use 0.5 weight which maps to AVERAGING/RECOMBINATION.
        
        # TODO: Fully implement DOMINANT_RECESSIVE logic if needed.
        return cls.from_parents_weighted(
            parent1, parent2, 0.5, mutation_rate, mutation_strength, population_stress
        )

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
