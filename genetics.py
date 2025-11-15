"""Genetics system for artificial life simulation.

This module provides a genetic system for fish, allowing for heritable traits,
mutations, and evolutionary dynamics.
"""

import random
from dataclasses import dataclass
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from neural_brain import NeuralBrain
    from behavior_algorithms import BehaviorAlgorithm


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
        brain: Neural network brain (optional, can be None for simple AI)
        behavior_algorithm: Parametrizable behavior algorithm (NEW!)
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

    # Neural brain (optional)
    brain: Optional['NeuralBrain'] = None

    # Behavior algorithm (NEW: algorithmic evolution system)
    behavior_algorithm: Optional['BehaviorAlgorithm'] = None

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
            from neural_brain import NeuralBrain
            brain = NeuralBrain.random()

        # Create random behavior algorithm
        algorithm = None
        if use_algorithm:
            from behavior_algorithms import get_random_algorithm
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
            brain=brain,
            behavior_algorithm=algorithm,
        )

    @classmethod
    def from_parents(cls, parent1: 'Genome', parent2: 'Genome',
                     mutation_rate: float = 0.1, mutation_strength: float = 0.1) -> 'Genome':
        """Create offspring genome by mixing parent genes with mutations.

        Args:
            parent1: First parent's genome
            parent2: Second parent's genome
            mutation_rate: Probability of each gene mutating (0.0-1.0)
            mutation_strength: Magnitude of mutations (0.0-1.0)

        Returns:
            New genome combining parent traits with possible mutations
        """
        def inherit_trait(val1: float, val2: float, min_val: float, max_val: float) -> float:
            """Inherit a trait from parents with possible mutation."""
            # Average of parents (could also do random choice or weighted)
            inherited = (val1 + val2) / 2.0

            # Apply mutation
            if random.random() < mutation_rate:
                mutation = random.gauss(0, mutation_strength)
                inherited += mutation

            # Clamp to valid range
            return max(min_val, min(max_val, inherited))

        # Handle brain inheritance
        brain = None
        if parent1.brain is not None and parent2.brain is not None:
            from neural_brain import NeuralBrain
            brain = NeuralBrain.crossover(parent1.brain, parent2.brain,
                                         mutation_rate=mutation_rate,
                                         mutation_strength=mutation_strength)
        elif parent1.brain is not None or parent2.brain is not None:
            # If only one parent has a brain, randomly inherit it
            from neural_brain import NeuralBrain
            parent_brain = parent1.brain if parent1.brain is not None else parent2.brain
            if parent_brain and random.random() < 0.5:
                brain = NeuralBrain.random()  # Create random brain for diversity

        # Handle behavior algorithm inheritance (NEW!)
        algorithm = None
        if parent1.behavior_algorithm is not None:
            # Inherit from parent1 and mutate
            from behavior_algorithms import inherit_algorithm_with_mutation
            algorithm = inherit_algorithm_with_mutation(
                parent1.behavior_algorithm,
                mutation_rate=mutation_rate * 1.5,  # Slightly higher mutation for algorithms
                mutation_strength=mutation_strength * 1.5
            )
        elif parent2.behavior_algorithm is not None:
            # Inherit from parent2 and mutate
            from behavior_algorithms import inherit_algorithm_with_mutation
            algorithm = inherit_algorithm_with_mutation(
                parent2.behavior_algorithm,
                mutation_rate=mutation_rate * 1.5,
                mutation_strength=mutation_strength * 1.5
            )
        else:
            # No algorithm from either parent, create random
            from behavior_algorithms import get_random_algorithm
            algorithm = get_random_algorithm()

        return cls(
            speed_modifier=inherit_trait(parent1.speed_modifier, parent2.speed_modifier, 0.5, 1.5),
            size_modifier=inherit_trait(parent1.size_modifier, parent2.size_modifier, 0.7, 1.3),
            vision_range=inherit_trait(parent1.vision_range, parent2.vision_range, 0.7, 1.3),
            metabolism_rate=inherit_trait(parent1.metabolism_rate, parent2.metabolism_rate, 0.7, 1.3),
            max_energy=inherit_trait(parent1.max_energy, parent2.max_energy, 0.7, 1.5),
            fertility=inherit_trait(parent1.fertility, parent2.fertility, 0.6, 1.4),
            aggression=inherit_trait(parent1.aggression, parent2.aggression, 0.0, 1.0),
            social_tendency=inherit_trait(parent1.social_tendency, parent2.social_tendency, 0.0, 1.0),
            color_hue=inherit_trait(parent1.color_hue, parent2.color_hue, 0.0, 1.0),
            brain=brain,
            behavior_algorithm=algorithm,
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
