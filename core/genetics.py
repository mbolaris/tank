"""Genetics system for artificial life simulation.

This module provides a genetic system for fish, allowing for heritable traits,
mutations, and evolutionary dynamics.
"""

import random
from dataclasses import dataclass, field
from typing import Tuple, Optional, TYPE_CHECKING, Dict, List
from enum import Enum

if TYPE_CHECKING:
    from core.neural_brain import NeuralBrain
    from core.behavior_algorithms import BehaviorAlgorithm


class GeneticCrossoverMode(Enum):
    """Different modes for genetic crossover during reproduction."""
    AVERAGING = "averaging"  # Simple average of parent traits
    RECOMBINATION = "recombination"  # Gene recombination (more realistic)
    DOMINANT_RECESSIVE = "dominant_recessive"  # Some genes are dominant


@dataclass
class Genome:
    """Represents the genetic makeup of a fish.

    Attributes:
        speed_modifier: Multiplier for base speed (0.5-1.5)
        size_modifier: Multiplier for base size (0.7-1.3)
        vision_range: Multiplier for detection range (0.7-1.3)
        metabolism_rate: Multiplier for energy consumption (0.7-1.3)
        max_energy: Multiplier for maximum energy capacity (0.7-1.5)
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
        brain: Neural network brain (optional, can be None for simple AI)
        behavior_algorithm: Parametrizable behavior algorithm (NEW!)
        fitness_score: Accumulated fitness over lifetime (0.0+)
        learned_behaviors: Behavioral improvements from experience
        epigenetic_modifiers: Environmental effects on gene expression
        mate_preferences: Preferences for mate selection
    """

    # Performance traits
    speed_modifier: float = 1.0
    size_modifier: float = 1.0
    vision_range: float = 1.0

    # Metabolic traits
    metabolism_rate: float = 1.0
    max_energy: float = 1.0
    fertility: float = 1.0

    # Behavioral traits
    aggression: float = 0.5
    social_tendency: float = 0.5

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

    # Neural brain (optional)
    brain: Optional['NeuralBrain'] = None

    # Behavior algorithm (NEW: algorithmic evolution system)
    behavior_algorithm: Optional['BehaviorAlgorithm'] = None

    # Fitness tracking (NEW: for selection pressure)
    fitness_score: float = field(default=0.0)

    # Learned behaviors (NEW: improve within lifetime)
    learned_behaviors: Dict[str, float] = field(default_factory=dict)

    # Epigenetic modifiers (NEW: environmental effects)
    epigenetic_modifiers: Dict[str, float] = field(default_factory=dict)

    # Mate preferences (NEW: sexual selection)
    mate_preferences: Dict[str, float] = field(default_factory=lambda: {
        'prefer_high_fitness': 0.5,
        'prefer_similar_size': 0.5,
        'prefer_different_color': 0.5,
        'prefer_high_energy': 0.5,
    })

    @classmethod
    def random(cls, use_brain: bool = True, use_algorithm: bool = True) -> 'Genome':
        """Create a random genome with traits within normal ranges.

        Args:
            use_brain: Whether to include a neural network brain
            use_algorithm: Whether to include a behavior algorithm

        Returns:
            New random genome
        """
        # Import here to avoid circular dependency
        brain = None
        if use_brain:
            from core.neural_brain import NeuralBrain
            brain = NeuralBrain.random()

        # Create random behavior algorithm
        algorithm = None
        if use_algorithm:
            from core.behavior_algorithms import get_random_algorithm
            algorithm = get_random_algorithm()

        return cls(
            speed_modifier=random.uniform(0.7, 1.3),
            size_modifier=random.uniform(0.7, 1.3),
            vision_range=random.uniform(0.7, 1.3),
            metabolism_rate=random.uniform(0.7, 1.3),
            max_energy=random.uniform(0.7, 1.5),
            fertility=random.uniform(0.6, 1.4),
            aggression=random.uniform(0.0, 1.0),
            social_tendency=random.uniform(0.0, 1.0),
            color_hue=random.random(),
            # Visual traits for parametric fish templates
            template_id=random.randint(0, 5),
            fin_size=random.uniform(0.6, 1.4),
            tail_size=random.uniform(0.6, 1.4),
            body_aspect=random.uniform(0.7, 1.3),
            eye_size=random.uniform(0.7, 1.3),
            pattern_intensity=random.random(),
            pattern_type=random.randint(0, 3),
            brain=brain,
            behavior_algorithm=algorithm,
        )

    def update_fitness(self, food_eaten: int = 0, survived_frames: int = 0,
                      reproductions: int = 0, energy_ratio: float = 0.0):
        """Update fitness score based on life events.

        Args:
            food_eaten: Number of food items consumed
            survived_frames: Frames survived this update
            reproductions: Number of successful reproductions
            energy_ratio: Current energy / max energy ratio
        """
        # Fitness components
        self.fitness_score += food_eaten * 2.0  # Eating is valuable
        self.fitness_score += survived_frames * 0.01  # Survival matters
        self.fitness_score += reproductions * 50.0  # Reproduction is highly valuable
        self.fitness_score += energy_ratio * 0.1  # Maintaining energy is good

    def calculate_mate_compatibility(self, other: 'Genome') -> float:
        """Calculate compatibility score with potential mate (0.0-1.0).

        Args:
            other: Potential mate's genome

        Returns:
            Compatibility score (higher is better)
        """
        compatibility = 0.0

        # Fitness preference
        if other.fitness_score > self.fitness_score:
            compatibility += self.mate_preferences.get('prefer_high_fitness', 0.5) * 0.3

        # Size similarity preference
        size_diff = abs(self.size_modifier - other.size_modifier)
        size_score = 1.0 - min(size_diff / 0.6, 1.0)  # 0.6 is max diff
        compatibility += self.mate_preferences.get('prefer_similar_size', 0.5) * size_score * 0.2

        # Color diversity preference
        color_diff = abs(self.color_hue - other.color_hue)
        color_score = min(color_diff / 0.5, 1.0)  # Prefer different colors
        compatibility += self.mate_preferences.get('prefer_different_color', 0.5) * color_score * 0.2

        # General genetic diversity (trait variance)
        trait_variance = (
            abs(self.speed_modifier - other.speed_modifier) +
            abs(self.metabolism_rate - other.metabolism_rate) +
            abs(self.vision_range - other.vision_range)
        ) / 3.0
        compatibility += min(trait_variance / 0.3, 1.0) * 0.3

        return min(compatibility, 1.0)

    @classmethod
    def from_parents(cls, parent1: 'Genome', parent2: 'Genome',
                     mutation_rate: float = 0.1, mutation_strength: float = 0.1,
                     population_stress: float = 0.0,
                     crossover_mode: GeneticCrossoverMode = GeneticCrossoverMode.RECOMBINATION) -> 'Genome':
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
        # IMPROVEMENT: Adaptive mutation rates - increase when population is stressed
        # This allows faster evolution when the population is struggling
        adaptive_mutation_rate = mutation_rate * (1.0 + population_stress * 2.0)  # Up to 3x higher
        adaptive_mutation_strength = mutation_strength * (1.0 + population_stress * 1.5)  # Up to 2.5x stronger

        # Clamp to reasonable ranges
        adaptive_mutation_rate = min(0.4, adaptive_mutation_rate)  # Max 40% mutation rate
        adaptive_mutation_strength = min(0.25, adaptive_mutation_strength)  # Max 25% strength

        def inherit_trait(val1: float, val2: float, min_val: float, max_val: float,
                         dominant_gene: Optional[int] = None) -> float:
            """Inherit a trait from parents with possible mutation.

            Args:
                val1: Parent 1 trait value
                val2: Parent 2 trait value
                min_val: Minimum allowed value
                max_val: Maximum allowed value
                dominant_gene: If set (0 or 1), that parent's gene is dominant

            Returns:
                Inherited trait value
            """
            # Choose inheritance method based on crossover mode
            if crossover_mode == GeneticCrossoverMode.AVERAGING:
                # Original method: average of parents
                inherited = (val1 + val2) / 2.0

            elif crossover_mode == GeneticCrossoverMode.RECOMBINATION:
                # Gene recombination: randomly choose from each parent
                inherited = val1 if random.random() < 0.5 else val2
                # Add some blending
                inherited = inherited * 0.7 + ((val1 + val2) / 2.0) * 0.3

            elif crossover_mode == GeneticCrossoverMode.DOMINANT_RECESSIVE:
                # Dominant/recessive genes
                if dominant_gene is not None:
                    # Dominant gene takes precedence
                    dominant_val = val1 if dominant_gene == 0 else val2
                    recessive_val = val2 if dominant_gene == 0 else val1
                    # 75% dominant, 25% recessive expression
                    inherited = dominant_val * 0.75 + recessive_val * 0.25
                else:
                    # No dominance, use random selection
                    inherited = val1 if random.random() < 0.5 else val2
            else:
                # Default to averaging
                inherited = (val1 + val2) / 2.0

            # Apply mutation (using adaptive rates)
            if random.random() < adaptive_mutation_rate:
                mutation = random.gauss(0, adaptive_mutation_strength)
                inherited += mutation

            # Clamp to valid range
            return max(min_val, min(max_val, inherited))

        # Handle brain inheritance
        brain = None
        if parent1.brain is not None and parent2.brain is not None:
            from core.neural_brain import NeuralBrain
            brain = NeuralBrain.crossover(parent1.brain, parent2.brain,
                                         mutation_rate=adaptive_mutation_rate,
                                         mutation_strength=adaptive_mutation_strength)
        elif parent1.brain is not None or parent2.brain is not None:
            # If only one parent has a brain, randomly inherit it
            from core.neural_brain import NeuralBrain
            parent_brain = parent1.brain if parent1.brain is not None else parent2.brain
            if parent_brain and random.random() < 0.5:
                brain = NeuralBrain.random()  # Create random brain for diversity

        # Handle behavior algorithm inheritance (NEW!)
        algorithm = None
        if parent1.behavior_algorithm is not None:
            # Inherit from parent1 and mutate (using adaptive rates)
            from core.behavior_algorithms import inherit_algorithm_with_mutation
            algorithm = inherit_algorithm_with_mutation(
                parent1.behavior_algorithm,
                mutation_rate=adaptive_mutation_rate * 1.5,  # Slightly higher mutation for algorithms
                mutation_strength=adaptive_mutation_strength * 1.5
            )
        elif parent2.behavior_algorithm is not None:
            # Inherit from parent2 and mutate (using adaptive rates)
            from core.behavior_algorithms import inherit_algorithm_with_mutation
            algorithm = inherit_algorithm_with_mutation(
                parent2.behavior_algorithm,
                mutation_rate=adaptive_mutation_rate * 1.5,
                mutation_strength=adaptive_mutation_strength * 1.5
            )
        else:
            # No algorithm from either parent, create random
            from core.behavior_algorithms import get_random_algorithm
            algorithm = get_random_algorithm()

        # Determine dominant genes randomly (for DOMINANT_RECESSIVE mode)
        speed_dominant = 0 if random.random() < 0.5 else 1
        size_dominant = 0 if random.random() < 0.5 else 1
        metabolism_dominant = 0 if random.random() < 0.5 else 1

        # NEW: Trait linkage - speed and metabolism are linked
        # Higher speed should correlate with higher metabolism
        speed = inherit_trait(parent1.speed_modifier, parent2.speed_modifier, 0.5, 1.5, speed_dominant)

        # Metabolism is influenced by speed (linked traits)
        base_metabolism = inherit_trait(parent1.metabolism_rate, parent2.metabolism_rate, 0.7, 1.3, metabolism_dominant)
        # Link: faster fish tend to have higher metabolism
        metabolism_link_factor = (speed - 1.0) * 0.2  # -0.1 to +0.1 adjustment
        metabolism = max(0.7, min(1.3, base_metabolism + metabolism_link_factor))

        # NEW: Inherit mate preferences with slight variation
        mate_prefs = {}
        for pref_key in parent1.mate_preferences:
            p1_val = parent1.mate_preferences.get(pref_key, 0.5)
            p2_val = parent2.mate_preferences.get(pref_key, 0.5)
            mate_prefs[pref_key] = inherit_trait(p1_val, p2_val, 0.0, 1.0)

        # NEW: Epigenetic modifiers (environmental effects passed to offspring)
        epigenetic = {}
        if parent1.epigenetic_modifiers or parent2.epigenetic_modifiers:
            # Inherit some epigenetic modifications (with 50% retention rate)
            for modifier_key in set(list(parent1.epigenetic_modifiers.keys()) + list(parent2.epigenetic_modifiers.keys())):
                p1_val = parent1.epigenetic_modifiers.get(modifier_key, 0.0)
                p2_val = parent2.epigenetic_modifiers.get(modifier_key, 0.0)
                avg_val = (p1_val + p2_val) / 2.0
                # Epigenetic effects decay by 50% each generation
                if abs(avg_val) > 0.01:  # Only keep significant modifiers
                    epigenetic[modifier_key] = avg_val * 0.5

        # Inherit template_id with possible mutation (discrete choice)
        inherited_template = parent1.template_id if random.random() < 0.5 else parent2.template_id
        if random.random() < adaptive_mutation_rate:
            # Mutation: randomly shift template ±1
            inherited_template = max(0, min(5, inherited_template + random.choice([-1, 0, 1])))

        # Inherit pattern_type with possible mutation (discrete choice)
        inherited_pattern = parent1.pattern_type if random.random() < 0.5 else parent2.pattern_type
        if random.random() < adaptive_mutation_rate:
            # Mutation: randomly shift pattern ±1
            inherited_pattern = max(0, min(3, inherited_pattern + random.choice([-1, 0, 1])))

        return cls(
            speed_modifier=speed,
            size_modifier=inherit_trait(parent1.size_modifier, parent2.size_modifier, 0.7, 1.3, size_dominant),
            vision_range=inherit_trait(parent1.vision_range, parent2.vision_range, 0.7, 1.3),
            metabolism_rate=metabolism,  # Linked to speed
            max_energy=inherit_trait(parent1.max_energy, parent2.max_energy, 0.7, 1.5),
            fertility=inherit_trait(parent1.fertility, parent2.fertility, 0.6, 1.4),
            aggression=inherit_trait(parent1.aggression, parent2.aggression, 0.0, 1.0),
            social_tendency=inherit_trait(parent1.social_tendency, parent2.social_tendency, 0.0, 1.0),
            color_hue=inherit_trait(parent1.color_hue, parent2.color_hue, 0.0, 1.0),
            # NEW: Visual trait inheritance for parametric fish templates
            template_id=inherited_template,
            fin_size=inherit_trait(parent1.fin_size, parent2.fin_size, 0.6, 1.4),
            tail_size=inherit_trait(parent1.tail_size, parent2.tail_size, 0.6, 1.4),
            body_aspect=inherit_trait(parent1.body_aspect, parent2.body_aspect, 0.7, 1.3),
            eye_size=inherit_trait(parent1.eye_size, parent2.eye_size, 0.7, 1.3),
            pattern_intensity=inherit_trait(parent1.pattern_intensity, parent2.pattern_intensity, 0.0, 1.0),
            pattern_type=inherited_pattern,
            brain=brain,
            behavior_algorithm=algorithm,
            fitness_score=0.0,  # New offspring starts with 0 fitness
            learned_behaviors={},  # Start with no learned behaviors
            epigenetic_modifiers=epigenetic,  # Inherit epigenetic effects
            mate_preferences=mate_prefs,  # Inherit mate preferences
        )

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
