"""Genetics system for artificial life simulation.

This module provides a genetic system for fish, allowing for heritable traits,
mutations, and evolutionary dynamics.

Uses core.evolution module for crossover, mutation, and inheritance operations.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Tuple

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


@dataclass
class MetaGeneticTraits:
    """Meta-genetic traits that control inheritance and mutation of base traits.
    
    These meta-traits are themselves heritable and mutable, creating a second
    level of evolution that controls HOW traits evolve.
    
    For each base genetic trait, we store:
    - HGT probability: Chance of inheriting trait directly from mate (vs averaging)
    - Mutation rate multiplier: Per-trait mutation rate modifier
    """
    
    # Performance traits
    size_modifier_hgt_prob: float = 0.1
    size_modifier_mutation_mult: float = 1.0
    fertility_hgt_prob: float = 0.1
    fertility_mutation_mult: float = 1.0
    
    # Behavioral traits
    aggression_hgt_prob: float = 0.1
    aggression_mutation_mult: float = 1.0
    social_tendency_hgt_prob: float = 0.1
    social_tendency_mutation_mult: float = 1.0
    
    # Hunting traits
    pursuit_aggression_hgt_prob: float = 0.1
    pursuit_aggression_mutation_mult: float = 1.0
    prediction_skill_hgt_prob: float = 0.1
    prediction_skill_mutation_mult: float = 1.0
    hunting_stamina_hgt_prob: float = 0.1
    hunting_stamina_mutation_mult: float = 1.0
    
    # Visual traits
    color_hue_hgt_prob: float = 0.1
    color_hue_mutation_mult: float = 1.0
    fin_size_hgt_prob: float = 0.1
    fin_size_mutation_mult: float = 1.0
    tail_size_hgt_prob: float = 0.1
    tail_size_mutation_mult: float = 1.0
    body_aspect_hgt_prob: float = 0.1
    body_aspect_mutation_mult: float = 1.0
    eye_size_hgt_prob: float = 0.1
    eye_size_mutation_mult: float = 1.0
    pattern_intensity_hgt_prob: float = 0.1
    pattern_intensity_mutation_mult: float = 1.0
    
    # Discrete traits (template_id, pattern_type) don't use HGT - they use Mendelian inheritance
    # But they can still have custom mutation rates
    template_id_mutation_mult: float = 1.0
    pattern_type_mutation_mult: float = 1.0


class GeneticCrossoverMode(Enum):
    """Different modes for genetic crossover during reproduction."""

    AVERAGING = "averaging"  # Simple average of parent traits
    RECOMBINATION = "recombination"  # Gene recombination (more realistic)
    DOMINANT_RECESSIVE = "dominant_recessive"  # Some genes are dominant


@dataclass
class Genome:
    """Represents the genetic makeup of a fish.

    Attributes:
        size_modifier: Multiplier for base size (0.7-1.3), also determines max energy capacity
        fertility: Multiplier for reproduction rate (0.6-1.4)
        aggression: Territorial/competitive behavior (0.0-1.0)
        social_tendency: Preference for schooling (0.0-1.0)
        color_hue: Color variation for visual diversity (0.0-1.0)
        template_id: Fish body template selection (0-5, inherited)
        fin_size: Size of dorsal and pectoral fins (0.6-1.4)
        tail_size: Size and spread of tail fin (0.6-1.4)
        body_aspect: Body width-to-height ratio/roundness (0.7-1.3)
        eye_size: Eye size relative to body (0.7-1.3)
        pattern_intensity: Visibility of patterns/stripes (0.0-1.0)
        pattern_type: Pattern style: 0=stripes, 1=spots, 2=solid, 3=gradient
        behavior_algorithm: Primary behavior algorithm for general movement decisions
        poker_algorithm: Poker-specific behavior algorithm (mix-and-match evolution)
        meta_traits: Meta-genetic traits controlling per-trait HGT and mutation
        learned_behaviors: Behavioral improvements from experience
        epigenetic_modifiers: Environmental effects on gene expression
        mate_preferences: Preferences for mate selection
    """

    # Performance traits (Now derived from visuals, except fertility)
    size_modifier: float = 1.0
    fertility: float = 1.0

    # Behavioral traits
    aggression: float = 0.5
    social_tendency: float = 0.5

    # Hunting traits (NEW: for evolving better live food catching ability)
    pursuit_aggression: float = 0.5  # How aggressively fish chase moving food (0.0-1.0)
    prediction_skill: float = 0.5  # Ability to predict where moving food will be (0.0-1.0)
    hunting_stamina: float = 0.5  # How long fish can sustain high-speed pursuit (0.0-1.0)

    # Visual traits
    color_hue: float = 0.5

    # NEW: Advanced visual traits for parametric fish templates
    template_id: int = 0  # Which fish body template to use (0-5)
    fin_size: float = 1.0  # Size of fins (0.6-1.4)
    tail_size: float = 1.0  # Size of tail fin (0.6-1.4)
    body_aspect: float = 1.0  # Body width-to-height ratio (0.7-1.3)
    eye_size: float = 1.0  # Eye size relative to body (0.7-1.3)
    pattern_intensity: float = 0.5  # Pattern visibility (0.0-1.0)
    pattern_type: int = 0  # Pattern style: 0=stripes, 1=spots, 2=solid, 3=gradient

    # Behavior algorithm (algorithmic evolution system)
    behavior_algorithm: Optional["BehaviorAlgorithm"] = None

    # Poker-specific behavior algorithm (NEW: for mix-and-match evolution)
    # This allows fish to have different algorithms for general movement vs poker decisions
    poker_algorithm: Optional["BehaviorAlgorithm"] = None

    # Poker strategy algorithm (NEW: controls actual betting decisions)
    # This is separate from poker_algorithm which controls movement when seeking/avoiding poker
    poker_strategy_algorithm: Optional["PokerStrategyAlgorithm"] = None

    # Meta-genetic traits (NEW: control per-trait HGT and mutation rates)
    meta_traits: MetaGeneticTraits = field(default_factory=MetaGeneticTraits)

    # Learned behaviors (NEW: improve within lifetime)
    learned_behaviors: Dict[str, float] = field(default_factory=dict)

    # Epigenetic modifiers (NEW: environmental effects)
    epigenetic_modifiers: Dict[str, float] = field(default_factory=dict)

    # Mate preferences (NEW: sexual selection)
    mate_preferences: Dict[str, float] = field(
        default_factory=lambda: {
            "prefer_similar_size": 0.5,
            "prefer_different_color": 0.5,
            "prefer_high_energy": 0.5,
        }
    )


    @property
    def speed_modifier(self) -> float:
        """Calculate speed modifier based on physical traits.
        
        Derived from:
        - template_id: Body shape aerodynamics
        - fin_size: Propulsion power
        - tail_size: Propulsion power
        - body_aspect: Hydrodynamic efficiency
        """
        # Template stats (base speed factor)
        # 0: Standard (1.0)
        # 1: Streamlined/Torpedo (1.2) - Fast
        # 2: Round/Discus (0.8) - Slow but maneuverable
        # 3: Eel-like (1.0)
        # 4: Boxy (0.9)
        # 5: Flat (1.1)
        template_speed_bonus = {0: 1.0, 1: 1.2, 2: 0.8, 3: 1.0, 4: 0.9, 5: 1.1}.get(self.template_id, 1.0)
        
        # Fins and Tail provide thrust
        # Larger fins = more thrust
        propulsion = (self.fin_size * 0.4 + self.tail_size * 0.6)
        
        # Body aspect: 1.0 is balanced. 
        # Streamlined (0.7-0.9) is faster than Round (1.1-1.3)
        # Optimal aspect for speed is around 0.8
        hydrodynamics = 1.0 - abs(self.body_aspect - 0.8) * 0.5
        
        return template_speed_bonus * propulsion * hydrodynamics

    @property
    def vision_range(self) -> float:
        """Calculate vision range based on eye size.
        
        Larger eyes = better vision.
        """
        return self.eye_size

    @property
    def metabolism_rate(self) -> float:
        """Calculate metabolism rate based on physical traits.
        
        Costs:
        - Size: Larger bodies require more energy (Cube law approximation)
        - Speed: Muscle mass for speed requires maintenance
        - Brain/Senses: Large eyes and sensory processing cost energy
        """
        # Base cost
        cost = 1.0
        
        # Size cost (Fish.max_energy scales with size, so this is relative consumption)
        # Larger fish burn more absolute energy, but we also want them to be less efficient per unit of mass?
        # Or maybe just proportional. Let's make it slightly super-linear to punish excessive size without food.
        cost += (self.size_modifier - 1.0) * 0.5
        
        # Speed cost (Muscle mass maintenance)
        # Faster fish burn significantly more energy
        cost += (self.speed_modifier - 1.0) * 0.8
        
        # Sensory cost (Brain power for vision)
        cost += (self.eye_size - 1.0) * 0.3
        
        return max(0.5, cost)

    @classmethod
    def random(cls, use_algorithm: bool = True, rng: Optional[random.Random] = None) -> "Genome":
        """Create a random genome with traits within normal ranges.

        Args:
            use_algorithm: Whether to include behavior algorithms
            rng: Random number generator (defaults to global random module)

        Returns:
            New random genome
        """
        rng = rng or random
        # Create random behavior algorithms
        algorithm = None
        poker_algorithm = None
        poker_strategy_algorithm = None
        if use_algorithm:
            from core.algorithms import get_random_algorithm
            from core.poker.strategy.implementations import get_random_poker_strategy

            algorithm = get_random_algorithm(rng=rng)
            # Also create a random poker algorithm for mix-and-match evolution
            poker_algorithm = get_random_algorithm(rng=rng)
            # Create random poker strategy for betting decisions
            poker_strategy_algorithm = get_random_poker_strategy(rng=rng)

        return cls(
            # Removed independent speed_modifier, vision_range, metabolism_rate
            size_modifier=rng.uniform(0.7, 1.3),
            fertility=rng.uniform(0.6, 1.4),
            aggression=rng.uniform(0.0, 1.0),
            social_tendency=rng.uniform(0.0, 1.0),
            # Hunting traits (NEW)
            pursuit_aggression=rng.uniform(0.0, 1.0),
            prediction_skill=rng.uniform(0.0, 1.0),
            hunting_stamina=rng.uniform(0.0, 1.0),
            color_hue=rng.random(),
            # Visual traits for parametric fish templates
            template_id=rng.randint(0, FISH_TEMPLATE_COUNT - 1),
            fin_size=rng.uniform(0.6, 1.4),
            tail_size=rng.uniform(0.6, 1.4),
            body_aspect=rng.uniform(0.7, 1.3),
            eye_size=rng.uniform(0.7, 1.3),
            pattern_intensity=rng.random(),
            pattern_type=rng.randint(0, FISH_PATTERN_COUNT - 1),
            behavior_algorithm=algorithm,
            poker_algorithm=poker_algorithm,
            poker_strategy_algorithm=poker_strategy_algorithm,
        )

    def calculate_mate_compatibility(self, other: "Genome") -> float:
        """Calculate compatibility score with potential mate (0.0-1.0).
        
        Used for standard reproduction (not poker-driven).

        Args:
            other: Potential mate's genome

        Returns:
            Compatibility score (higher is better)
        """
        compatibility = 0.0

        # Size similarity preference
        size_diff = abs(self.size_modifier - other.size_modifier)
        size_score = 1.0 - min(size_diff / 0.6, 1.0)  # 0.6 is max diff
        compatibility += self.mate_preferences.get("prefer_similar_size", 0.5) * size_score * 0.3

        # Color diversity preference
        color_diff = abs(self.color_hue - other.color_hue)
        color_score = min(color_diff / 0.5, 1.0)  # Prefer different colors
        compatibility += (
            self.mate_preferences.get("prefer_different_color", 0.5) * color_score * 0.3
        )

        # General genetic diversity (trait variance)
        # Use derived traits for comparison
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
        """Create offspring genome with weighted contributions from parents.

        This method allows for unequal genetic contributions, useful for scenarios
        where one parent has proven superior fitness (e.g., poker winner).

        Args:
            parent1: First parent's genome
            parent2: Second parent's genome
            parent1_weight: How much parent1 contributes (0.0-1.0), parent2 gets (1.0-parent1_weight)
            mutation_rate: Probability of each gene mutating (0.0-1.0)
            mutation_strength: Magnitude of mutations (0.0-1.0)
            population_stress: Population stress level (0.0-1.0) for adaptive mutations

        Returns:
            New genome with weighted parent contributions plus mutations
        """
        # Clamp weight to valid range
        parent1_weight = max(0.0, min(1.0, parent1_weight))

        # Use evolution module for adaptive mutation rates
        adaptive_rate, adaptive_strength = calculate_adaptive_mutation_rate(
            mutation_rate, mutation_strength, population_stress
        )

        # Helper using evolution module's inherit_trait
        def weighted_inherit(val1: float, val2: float, min_val: float, max_val: float) -> float:
            return _inherit_trait(
                val1, val2, min_val, max_val,
                weight1=parent1_weight,
                mutation_rate=adaptive_rate,
                mutation_strength=adaptive_strength,
            )

        # Handle behavior algorithm with weighted crossover
        algorithm = inherit_algorithm(
            parent1.behavior_algorithm,
            parent2.behavior_algorithm,
            weight1=parent1_weight,
            mutation_rate=adaptive_rate * 1.5,
            mutation_strength=adaptive_strength * 1.5,
            algorithm_switch_rate=0.03,
        )

        # Handle poker algorithm with SPECIALIZED poker crossover for evolution
        poker_algorithm = None
        if parent1.poker_algorithm is not None or parent2.poker_algorithm is not None:
            from core.algorithms import crossover_poker_algorithms

            poker_algorithm = crossover_poker_algorithms(
                parent1.poker_algorithm,
                parent2.poker_algorithm,
                parent1_poker_wins=0,  # Fish context not available here
                parent2_poker_wins=0,
                mutation_rate=adaptive_rate * 1.2,
                mutation_strength=adaptive_strength * 1.2,
            )
        else:
            from core.algorithms import get_random_algorithm
            poker_algorithm = get_random_algorithm()

        # Handle poker strategy algorithm (betting decisions evolve independently)
        poker_strategy_algorithm = None
        if (
            parent1.poker_strategy_algorithm is not None
            or parent2.poker_strategy_algorithm is not None
        ):
            from core.poker.strategy.implementations import crossover_poker_strategies

            poker_strategy_algorithm = crossover_poker_strategies(
                parent1.poker_strategy_algorithm,
                parent2.poker_strategy_algorithm,
                mutation_rate=adaptive_rate * 1.2,
                mutation_strength=adaptive_strength * 1.2,
            )
        else:
            from core.poker.strategy.implementations import get_random_poker_strategy
            poker_strategy_algorithm = get_random_poker_strategy()

        # Discrete traits using evolution module
        inherited_template = _inherit_discrete_trait(
            parent1.template_id, parent2.template_id,
            0, 5, weight1=parent1_weight, mutation_rate=adaptive_rate,
        )
        inherited_pattern = _inherit_discrete_trait(
            parent1.pattern_type, parent2.pattern_type,
            0, 3, weight1=parent1_weight, mutation_rate=adaptive_rate,
        )

        # Removed independent inheritance of speed, metabolism, vision
        # They are now derived from the visual traits below

        # Inherit hunting traits (NEW)
        pursuit_aggression = weighted_inherit(
            parent1.pursuit_aggression, parent2.pursuit_aggression, 0.0, 1.0
        )
        prediction_skill = weighted_inherit(
            parent1.prediction_skill, parent2.prediction_skill, 0.0, 1.0
        )
        hunting_stamina = weighted_inherit(
            parent1.hunting_stamina, parent2.hunting_stamina, 0.0, 1.0
        )

        # Weighted mate preferences
        mate_prefs = {}
        for pref_key in parent1.mate_preferences:
            p1_val = parent1.mate_preferences.get(pref_key, 0.5)
            p2_val = parent2.mate_preferences.get(pref_key, 0.5)
            mate_prefs[pref_key] = weighted_inherit(p1_val, p2_val, 0.0, 1.0)

        # Weighted epigenetic modifiers (decay by 50%)
        epigenetic = {}
        if parent1.epigenetic_modifiers or parent2.epigenetic_modifiers:
            for modifier_key in set(
                list(parent1.epigenetic_modifiers.keys())
                + list(parent2.epigenetic_modifiers.keys())
            ):
                p1_val = parent1.epigenetic_modifiers.get(modifier_key, 0.0)
                p2_val = parent2.epigenetic_modifiers.get(modifier_key, 0.0)
                weighted_val = p1_val * parent1_weight + p2_val * (1.0 - parent1_weight)
                if abs(weighted_val) > 0.01:
                    epigenetic[modifier_key] = weighted_val * 0.5

        # Create offspring genome
        offspring = cls(
            # Derived traits removed from init  
            size_modifier=weighted_inherit(parent1.size_modifier, parent2.size_modifier, 0.7, 1.3),
            fertility=weighted_inherit(parent1.fertility, parent2.fertility, 0.6, 1.4),
            aggression=weighted_inherit(parent1.aggression, parent2.aggression, 0.0, 1.0),
            social_tendency=weighted_inherit(
                parent1.social_tendency, parent2.social_tendency, 0.0, 1.0
            ),
            # Hunting traits (NEW)
            pursuit_aggression=pursuit_aggression,
            prediction_skill=prediction_skill,
            hunting_stamina=hunting_stamina,
            color_hue=weighted_inherit(parent1.color_hue, parent2.color_hue, 0.0, 1.0),
            template_id=inherited_template,
            fin_size=weighted_inherit(parent1.fin_size, parent2.fin_size, 0.6, 1.4),
            tail_size=weighted_inherit(parent1.tail_size, parent2.tail_size, 0.6, 1.4),
            body_aspect=weighted_inherit(parent1.body_aspect, parent2.body_aspect, 0.7, 1.3),
            eye_size=weighted_inherit(parent1.eye_size, parent2.eye_size, 0.7, 1.3),
            pattern_intensity=weighted_inherit(
                parent1.pattern_intensity, parent2.pattern_intensity, 0.0, 1.0
            ),
            pattern_type=inherited_pattern,
            behavior_algorithm=algorithm,
            poker_algorithm=poker_algorithm,
            poker_strategy_algorithm=poker_strategy_algorithm,
            learned_behaviors={},
            epigenetic_modifiers=epigenetic,
            mate_preferences=mate_prefs,
        )

        # Cultural inheritance of learned behaviors using evolution module
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
        """Create offspring genome by mixing parent genes with mutations.

        Args:
            parent1: First parent's genome
            parent2: Second parent's genome
            mutation_rate: Probability of each gene mutating (0.0-1.0)
            mutation_strength: Magnitude of mutations (0.0-1.0)
            population_stress: Population stress level (0.0-1.0) for adaptive mutations
            crossover_mode: Method for combining parent genes

        Returns:
            New genome combining parent traits with possible mutations
        """
        # Use evolution module for adaptive mutation rates
        adaptive_rate, adaptive_strength = calculate_adaptive_mutation_rate(
            mutation_rate, mutation_strength, population_stress
        )

        # Pre-check crossover mode for inherit_trait behavior
        is_averaging = crossover_mode == GeneticCrossoverMode.AVERAGING
        is_dominant = crossover_mode == GeneticCrossoverMode.DOMINANT_RECESSIVE

        # Determine dominant genes randomly (for DOMINANT_RECESSIVE mode)
        # Removed speed/metabolism dominance checks as they are now derived
        size_dominant = 0 if random.random() < 0.5 else 1

        def inherit_trait_with_mode(
            val1: float,
            val2: float,
            min_val: float,
            max_val: float,
            dominant_gene: Optional[int] = None,
        ) -> float:
            """Inherit trait using crossover mode."""
            # Determine weight based on crossover mode
            if is_averaging:
                weight1 = 0.5
            elif is_dominant and dominant_gene is not None:
                weight1 = 0.75 if dominant_gene == 0 else 0.25
            else:
                # Recombination: random selection with blending handled by inherit_trait
                weight1 = 0.5

            return _inherit_trait(
                val1, val2, min_val, max_val,
                weight1=weight1,
                mutation_rate=adaptive_rate,
                mutation_strength=adaptive_strength,
            )

        # Handle behavior algorithm inheritance using evolution module
        algorithm = inherit_algorithm(
            parent1.behavior_algorithm,
            parent2.behavior_algorithm,
            weight1=0.5,
            mutation_rate=adaptive_rate * 1.5,
            mutation_strength=adaptive_strength * 1.5,
            algorithm_switch_rate=0.05,
        )

        # Handle poker algorithm inheritance separately for mix-and-match evolution
        poker_algorithm = inherit_algorithm(
            parent1.poker_algorithm,
            parent2.poker_algorithm,
            weight1=0.5,
            mutation_rate=adaptive_rate * 1.5,
            mutation_strength=adaptive_strength * 1.5,
            algorithm_switch_rate=0.05,
        )

        # Handle poker strategy algorithm inheritance (for betting decisions)
        poker_strategy_algorithm = None
        if (
            parent1.poker_strategy_algorithm is not None
            or parent2.poker_strategy_algorithm is not None
        ):
            from core.poker.strategy.implementations import crossover_poker_strategies

            poker_strategy_algorithm = crossover_poker_strategies(
                parent1.poker_strategy_algorithm,
                parent2.poker_strategy_algorithm,
                mutation_rate=adaptive_rate * 1.2,
                mutation_strength=adaptive_strength * 1.2,
            )
        else:
            from core.poker.strategy.implementations import get_random_poker_strategy
            poker_strategy_algorithm = get_random_poker_strategy()

        # Removed independent inheritance of speed and metabolism
        # They are now derived from the visual traits below

        # Inherit hunting traits (NEW)
        pursuit_aggression = inherit_trait_with_mode(
            parent1.pursuit_aggression, parent2.pursuit_aggression, 0.0, 1.0
        )
        prediction_skill = inherit_trait_with_mode(
            parent1.prediction_skill, parent2.prediction_skill, 0.0, 1.0
        )
        hunting_stamina = inherit_trait_with_mode(
            parent1.hunting_stamina, parent2.hunting_stamina, 0.0, 1.0
        )

        # Inherit mate preferences
        mate_prefs = {}
        for pref_key in parent1.mate_preferences:
            p1_val = parent1.mate_preferences.get(pref_key, 0.5)
            p2_val = parent2.mate_preferences.get(pref_key, 0.5)
            mate_prefs[pref_key] = inherit_trait_with_mode(p1_val, p2_val, 0.0, 1.0)

        # Epigenetic modifiers (decay by 50% each generation)
        epigenetic = {}
        if parent1.epigenetic_modifiers or parent2.epigenetic_modifiers:
            for modifier_key in set(
                list(parent1.epigenetic_modifiers.keys())
                + list(parent2.epigenetic_modifiers.keys())
            ):
                p1_val = parent1.epigenetic_modifiers.get(modifier_key, 0.0)
                p2_val = parent2.epigenetic_modifiers.get(modifier_key, 0.0)
                avg_val = (p1_val + p2_val) / 2.0
                if abs(avg_val) > 0.01:
                    epigenetic[modifier_key] = avg_val * 0.5

        # Discrete traits using evolution module
        inherited_template = _inherit_discrete_trait(
            parent1.template_id, parent2.template_id,
            0, 5, weight1=0.5, mutation_rate=adaptive_rate,
        )
        inherited_pattern = _inherit_discrete_trait(
            parent1.pattern_type, parent2.pattern_type,
            0, 3, weight1=0.5, mutation_rate=adaptive_rate,
        )

        offspring = cls(
            # Derived traits removed from init
            size_modifier=inherit_trait_with_mode(
                parent1.size_modifier, parent2.size_modifier, 0.7, 1.3, size_dominant
            ),
            fertility=inherit_trait_with_mode(
                parent1.fertility, parent2.fertility, 0.6, 1.4
            ),
            aggression=inherit_trait_with_mode(
                parent1.aggression, parent2.aggression, 0.0, 1.0
            ),
            social_tendency=inherit_trait_with_mode(
                parent1.social_tendency, parent2.social_tendency, 0.0, 1.0
            ),
            # Hunting traits (NEW)
            pursuit_aggression=pursuit_aggression,
            prediction_skill=prediction_skill,
            hunting_stamina=hunting_stamina,
            color_hue=inherit_trait_with_mode(
                parent1.color_hue, parent2.color_hue, 0.0, 1.0
            ),
            template_id=inherited_template,
            fin_size=inherit_trait_with_mode(
                parent1.fin_size, parent2.fin_size, 0.6, 1.4
            ),
            tail_size=inherit_trait_with_mode(
                parent1.tail_size, parent2.tail_size, 0.6, 1.4
            ),
            body_aspect=inherit_trait_with_mode(
                parent1.body_aspect, parent2.body_aspect, 0.7, 1.3
            ),
            eye_size=inherit_trait_with_mode(
                parent1.eye_size, parent2.eye_size, 0.7, 1.3
            ),
            pattern_intensity=inherit_trait_with_mode(
                parent1.pattern_intensity, parent2.pattern_intensity, 0.0, 1.0
            ),
            pattern_type=inherited_pattern,
            behavior_algorithm=algorithm,
            poker_algorithm=poker_algorithm,
            poker_strategy_algorithm=poker_strategy_algorithm,
            learned_behaviors={},
            epigenetic_modifiers=epigenetic,
            mate_preferences=mate_prefs,
        )

        # Cultural inheritance of learned behaviors using evolution module
        inherit_learned_behaviors(parent1, parent2, offspring)

        return offspring

    def get_color_tint(self) -> Tuple[int, int, int]:
        """Get RGB color tint based on genome.

        Returns:
            RGB tuple for colorizing the fish sprite
        """
        # Convert hue (0-1) to RGB using simple HSV-like conversion
        # This gives visual diversity to the population
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

        # Desaturate to make it more subtle (blend with white)
        saturation = 0.3
        r = int(r * saturation + 255 * (1 - saturation))
        g = int(g * saturation + 255 * (1 - saturation))
        b = int(b * saturation + 255 * (1 - saturation))

        return (r, g, b)
