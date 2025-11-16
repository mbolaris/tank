"""Neural network brain system for fish.

This module provides neural network-based decision making for fish,
allowing them to learn and evolve better survival strategies.
"""

import math
import random
from typing import List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from core.entities import Fish, Food, Crab, Agent


def sigmoid(x: float) -> float:
    """Sigmoid activation function."""
    return 1.0 / (1.0 + math.exp(-max(-20, min(20, x))))  # Clamped to prevent overflow


def tanh(x: float) -> float:
    """Tanh activation function."""
    return math.tanh(max(-20, min(20, x)))  # Clamped


@dataclass
class NeuralBrain:
    """A simple feedforward neural network brain for fish.

    Architecture:
        Input layer: 12 neurons
            - distance to nearest food (normalized)
            - angle to nearest food (sin/cos)
            - distance to nearest ally (same species)
            - angle to nearest ally (sin/cos)
            - distance to nearest predator
            - angle to nearest predator (sin/cos)
            - current energy (normalized 0-1)
            - current speed (normalized)
            - age stage (0-1, baby to elder)
            - is_starving (0 or 1)

        Hidden layer: 8 neurons

        Output layer: 2 neurons
            - desired velocity X (-1 to 1)
            - desired velocity Y (-1 to 1)

    Attributes:
        weights_input_hidden: Weights from input to hidden layer (12x8 = 96 weights)
        weights_hidden_output: Weights from hidden to output layer (8x2 = 16 weights)
        bias_hidden: Bias values for hidden layer (8 values)
        bias_output: Bias values for output layer (2 values)
    """

    weights_input_hidden: List[List[float]]  # 12x8
    weights_hidden_output: List[List[float]]  # 8x2
    bias_hidden: List[float]  # 8
    bias_output: List[float]  # 2

    INPUT_SIZE = 12
    HIDDEN_SIZE = 8
    OUTPUT_SIZE = 2

    @classmethod
    def random(cls) -> 'NeuralBrain':
        """Create a random neural network brain."""
        # Initialize with small random weights
        weights_input_hidden = [[random.uniform(-1, 1) for _ in range(cls.HIDDEN_SIZE)]
                                for _ in range(cls.INPUT_SIZE)]
        weights_hidden_output = [[random.uniform(-1, 1) for _ in range(cls.OUTPUT_SIZE)]
                                 for _ in range(cls.HIDDEN_SIZE)]
        bias_hidden = [random.uniform(-0.5, 0.5) for _ in range(cls.HIDDEN_SIZE)]
        bias_output = [random.uniform(-0.5, 0.5) for _ in range(cls.OUTPUT_SIZE)]

        return cls(
            weights_input_hidden=weights_input_hidden,
            weights_hidden_output=weights_hidden_output,
            bias_hidden=bias_hidden,
            bias_output=bias_output
        )

    @classmethod
    def crossover(cls, parent1: 'NeuralBrain', parent2: 'NeuralBrain',
                  mutation_rate: float = 0.1, mutation_strength: float = 0.3) -> 'NeuralBrain':
        """Create offspring brain by mixing parent brains with mutation.

        Args:
            parent1: First parent's brain
            parent2: Second parent's brain
            mutation_rate: Probability of each weight mutating
            mutation_strength: Magnitude of mutations

        Returns:
            New brain with mixed weights
        """
        def mix_weights(w1: List[List[float]], w2: List[List[float]]) -> List[List[float]]:
            """Mix two weight matrices."""
            result = []
            for i in range(len(w1)):
                row = []
                for j in range(len(w1[i])):
                    # Average parents' weights
                    weight = (w1[i][j] + w2[i][j]) / 2.0

                    # Apply mutation
                    if random.random() < mutation_rate:
                        weight += random.gauss(0, mutation_strength)
                        weight = max(-5, min(5, weight))  # Clamp

                    row.append(weight)
                result.append(row)
            return result

        def mix_bias(b1: List[float], b2: List[float]) -> List[float]:
            """Mix two bias vectors."""
            result = []
            for i in range(len(b1)):
                bias = (b1[i] + b2[i]) / 2.0

                # Apply mutation
                if random.random() < mutation_rate:
                    bias += random.gauss(0, mutation_strength)
                    bias = max(-5, min(5, bias))  # Clamp

                result.append(bias)
            return result

        return cls(
            weights_input_hidden=mix_weights(parent1.weights_input_hidden, parent2.weights_input_hidden),
            weights_hidden_output=mix_weights(parent1.weights_hidden_output, parent2.weights_hidden_output),
            bias_hidden=mix_bias(parent1.bias_hidden, parent2.bias_hidden),
            bias_output=mix_bias(parent1.bias_output, parent2.bias_output)
        )

    def think(self, inputs: List[float]) -> Tuple[float, float]:
        """Process inputs through the neural network.

        Args:
            inputs: List of 12 input values

        Returns:
            Tuple of (velocity_x, velocity_y) in range [-1, 1]
        """
        if len(inputs) != self.INPUT_SIZE:
            raise ValueError(f"Expected {self.INPUT_SIZE} inputs, got {len(inputs)}")

        # Hidden layer computation
        hidden = []
        for h in range(self.HIDDEN_SIZE):
            activation = self.bias_hidden[h]
            for i in range(self.INPUT_SIZE):
                activation += inputs[i] * self.weights_input_hidden[i][h]
            hidden.append(tanh(activation))

        # Output layer computation
        outputs = []
        for o in range(self.OUTPUT_SIZE):
            activation = self.bias_output[o]
            for h in range(self.HIDDEN_SIZE):
                activation += hidden[h] * self.weights_hidden_output[h][o]
            outputs.append(tanh(activation))

        return outputs[0], outputs[1]


def get_brain_inputs(fish: 'Fish') -> List[float]:
    """Extract neural network inputs from fish's environment.

    Args:
        fish: The fish to get inputs for

    Returns:
        List of 12 normalized input values
    """
    try:
        from agents import Food, Crab, Fish as FishClass
    except ImportError:
        from core.entities import Food, Crab, Fish as FishClass

    from core.math_utils import Vector2

    # Initialize inputs
    inputs = [0.0] * 12

    # Helper to normalize distance (0 = very close, 1 = far)
    def normalize_distance(dist: float, max_dist: float = 400.0) -> float:
        return min(1.0, dist / max_dist)

    # Helper to get angle components (sin and cos for continuous representation)
    def get_angle_components(target_pos: Vector2) -> Tuple[float, float]:
        diff = target_pos - fish.pos
        if diff.length() == 0:
            return 0.0, 0.0
        diff = diff.normalize()
        return diff.x, diff.y  # Already normalized -1 to 1

    # 1-3: Nearest food
    nearest_food: Optional[Food] = None
    nearest_food_dist = float('inf')
    for agent in fish.environment.get_agents_of_type(Food):
        dist = (agent.pos - fish.pos).length()
        if dist < nearest_food_dist:
            nearest_food_dist = dist
            nearest_food = agent

    if nearest_food:
        inputs[0] = normalize_distance(nearest_food_dist)
        angle_x, angle_y = get_angle_components(nearest_food.pos)
        inputs[1] = angle_x
        inputs[2] = angle_y

    # 4-6: Nearest ally (same species)
    nearest_ally: Optional[FishClass] = None
    nearest_ally_dist = float('inf')
    for agent in fish.environment.get_agents_of_type(FishClass):
        if agent != fish and agent.species == fish.species:
            dist = (agent.pos - fish.pos).length()
            if dist < nearest_ally_dist:
                nearest_ally_dist = dist
                nearest_ally = agent

    if nearest_ally:
        inputs[3] = normalize_distance(nearest_ally_dist)
        angle_x, angle_y = get_angle_components(nearest_ally.pos)
        inputs[4] = angle_x
        inputs[5] = angle_y

    # 7-9: Nearest predator (crab)
    nearest_predator: Optional[Crab] = None
    nearest_predator_dist = float('inf')
    for agent in fish.environment.get_agents_of_type(Crab):
        dist = (agent.pos - fish.pos).length()
        if dist < nearest_predator_dist:
            nearest_predator_dist = dist
            nearest_predator = agent

    if nearest_predator:
        inputs[6] = normalize_distance(nearest_predator_dist, max_dist=300.0)
        angle_x, angle_y = get_angle_components(nearest_predator.pos)
        inputs[7] = angle_x
        inputs[8] = angle_y

    # 10: Current energy (normalized 0-1)
    inputs[9] = fish.energy / fish.max_energy if fish.max_energy > 0 else 0.0

    # 11: Current speed (normalized 0-1)
    max_speed = 10.0  # Typical max speed
    inputs[10] = min(1.0, fish.vel.length() / max_speed)

    # 12: Is starving (0 or 1)
    inputs[11] = 1.0 if fish.is_starving() else 0.0

    return inputs
