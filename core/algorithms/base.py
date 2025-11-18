"""Base classes and utilities for behavior algorithms.

This module contains:
- BehaviorAlgorithm base class
- ALGORITHM_PARAMETER_BOUNDS configuration
- Vector2 implementation (if pygame not available)
- Helper functions for algorithm execution
"""

import random
import math
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities import Fish


ALGORITHM_PARAMETER_BOUNDS = {
    'adaptive_pacer': {
        'base_speed': (0.5, 0.8),
        'energy_influence': (0.3, 0.7),
    },
    'alignment_matcher': {
        'alignment_radius': (60.0, 120.0),
        'alignment_strength': (0.5, 1.0),
    },
    'ambush_feeder': {
        'patience': (0.5, 1.0),
        'strike_distance': (30.0, 80.0),
        'strike_speed': (1.0, 1.5),
    },
    'boids_behavior': {
        'alignment_weight': (0.3, 0.7),
        'cohesion_weight': (0.3, 0.7),
        'separation_weight': (0.3, 0.7),
    },
    'border_hugger': {
        'hug_speed': (0.7, 1.1),
    },
    'bottom_feeder': {
        'preferred_depth': (0.7, 0.9),
        'search_speed': (0.4, 0.8),
    },
    'boundary_explorer': {
        'edge_preference': (0.6, 1.0),
        'exploration_speed': (0.5, 0.8),
    },
    'burst_swimmer': {
        'burst_duration': (30.0, 90.0),
        'burst_speed': (1.2, 1.6),
        'rest_duration': (60.0, 120.0),
    },
    'center_hugger': {
        'orbit_radius': (50.0, 120.0),
        'return_strength': (0.5, 0.9),
    },
    'circular_hunter': {
        'circle_radius': (40.0, 100.0),
        'circle_speed': (0.05, 0.15),
        'strike_threshold': (0.3, 0.6),
    },
    'cooperative_forager': {
        'follow_strength': (0.5, 0.9),
        'independence': (0.2, 0.5),
    },
    'corner_seeker': {
        'approach_speed': (0.4, 0.7),
    },
    'distance_keeper': {
        'approach_speed': (0.3, 0.6),
        'flee_speed': (0.8, 1.2),
        'safe_distance': (120.0, 200.0),
    },
    'dynamic_schooler': {
        'calm_cohesion': (0.3, 0.6),
        'danger_cohesion': (0.8, 1.2),
        'danger_threshold': (150.0, 250.0),
    },
    'energy_aware_food_seeker': {
        'calm_speed': (0.3, 0.6),
        'urgency_threshold': (0.3, 0.7),
        'urgent_speed': (0.8, 1.2),
    },
    'energy_balancer': {
        'max_energy_ratio': (0.7, 0.9),
        'min_energy_ratio': (0.3, 0.5),
    },
    'energy_conserver': {
        'activity_threshold': (0.4, 0.7),
        'rest_speed': (0.1, 0.3),
    },
    'erratic_evader': {
        'evasion_speed': (0.8, 1.3),
        'randomness': (0.5, 1.0),
        'threat_range': (100.0, 180.0),
    },
    'food_memory_seeker': {
        'exploration_rate': (0.2, 0.5),
        'memory_strength': (0.5, 1.0),
    },
    'food_quality_optimizer': {
        'distance_weight': (0.3, 0.7),
        'quality_weight': (0.5, 1.0),
    },
    'freeze_response': {
        'freeze_distance': (80.0, 150.0),
        'resume_distance': (200.0, 300.0),
    },
    'front_runner': {
        'independence': (0.5, 0.9),
        'leadership_strength': (0.7, 1.2),
    },
    'greedy_food_seeker': {
        'detection_range': (0.5, 1.0),
        'speed_multiplier': (0.7, 1.3),
    },
    'group_defender': {
        'group_strength': (0.6, 1.0),
        'min_group_distance': (30.0, 80.0),
    },
    'leader_follower': {
        'follow_strength': (0.6, 1.0),
        'max_follow_distance': (80.0, 150.0),
    },
    'loose_schooler': {
        'cohesion_strength': (0.3, 0.6),
        'max_distance': (100.0, 200.0),
    },
    'metabolic_optimizer': {
        'efficiency_threshold': (0.5, 0.8),
        'high_efficiency_speed': (0.7, 1.1),
        'low_efficiency_speed': (0.2, 0.4),
    },
    'mirror_mover': {
        'mirror_distance': (50.0, 100.0),
        'mirror_strength': (0.6, 1.0),
    },
    'nomadic_wanderer': {
        'direction_change_rate': (0.01, 0.05),
        'wander_strength': (0.5, 0.9),
    },
    'opportunistic_feeder': {
        'max_pursuit_distance': (50.0, 200.0),
        'speed': (0.6, 1.0),
    },
    'opportunistic_rester': {
        'active_speed': (0.5, 0.9),
        'safe_radius': (100.0, 200.0),
    },
    'panic_flee': {
        'flee_speed': (1.2, 1.8),
        'panic_distance': (100.0, 200.0),
    },
    'patrol_feeder': {
        'food_priority': (0.6, 1.0),
        'patrol_radius': (50.0, 150.0),
        'patrol_speed': (0.5, 1.0),
    },
    'perimeter_guard': {
        'orbit_radius': (70.0, 130.0),
        'orbit_speed': (0.5, 0.9),
    },
    'perpendicular_escape': {
        'escape_speed': (1.0, 1.4),
    },
    'random_explorer': {
        'change_frequency': (0.02, 0.08),
        'exploration_speed': (0.5, 0.9),
    },
    'route_patroller': {
        'patrol_speed': (0.5, 0.8),
        'waypoint_threshold': (30.0, 60.0),
    },
    'separation_seeker': {
        'min_distance': (30.0, 70.0),
        'separation_strength': (0.5, 1.0),
    },
    'spiral_escape': {
        'spiral_radius': (20.0, 60.0),
        'spiral_rate': (0.1, 0.3),
    },
    'starvation_preventer': {
        'critical_threshold': (0.2, 0.4),
        'urgency_multiplier': (1.3, 1.8),
    },
    'stealthy_avoider': {
        'awareness_range': (150.0, 250.0),
        'stealth_speed': (0.3, 0.6),
    },
    'surface_skimmer': {
        'horizontal_speed': (0.5, 1.0),
        'preferred_depth': (0.1, 0.3),
    },
    'sustainable_cruiser': {
        'consistency': (0.7, 1.0),
        'cruise_speed': (0.4, 0.7),
    },
    'territorial_defender': {
        'aggression': (0.5, 1.0),
        'territory_radius': (80.0, 150.0),
    },
    'tight_schooler': {
        'cohesion_strength': (0.7, 1.2),
        'preferred_distance': (20.0, 50.0),
    },
    'vertical_escaper': {
        'escape_speed': (1.0, 1.5),
    },
    'wall_follower': {
        'follow_speed': (0.5, 0.8),
        'wall_distance': (20.0, 60.0),
    },
    'zigzag_forager': {
        'forward_speed': (0.6, 1.0),
        'zigzag_amplitude': (0.5, 1.2),
        'zigzag_frequency': (0.02, 0.08),
    },
    # Poker interaction algorithms
    'poker_challenger': {
        'challenge_radius': (100.0, 250.0),
        'challenge_speed': (0.8, 1.3),
        'min_energy_to_challenge': (15.0, 30.0),
    },
    'poker_dodger': {
        'avoidance_radius': (80.0, 150.0),
        'avoidance_speed': (0.7, 1.1),
        'food_priority': (0.6, 1.0),
    },
    'poker_gambler': {
        'high_energy_threshold': (0.6, 0.9),
        'challenge_speed': (1.0, 1.5),
        'risk_tolerance': (0.3, 0.8),
    },
    'selective_poker': {
        'min_energy_ratio': (0.4, 0.7),
        'max_energy_ratio': (0.7, 0.95),
        'challenge_speed': (0.6, 1.0),
        'selectivity': (0.5, 0.9),
    },
    'poker_opportunist': {
        'poker_weight': (0.3, 0.7),
        'food_weight': (0.3, 0.7),
        'opportunity_radius': (80.0, 150.0),
    },
}


@dataclass
class BehaviorAlgorithm(ABC):
    """Base class for all behavior algorithms.

    Each algorithm has:
    - A unique algorithm_id
    - A set of parameters that can mutate
    - An execute method that determines fish movement
    """

    algorithm_id: str
    parameters: Dict[str, float] = field(default_factory=dict)
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.parameter_bounds:
            bounds = ALGORITHM_PARAMETER_BOUNDS.get(self.algorithm_id)
            if bounds:
                self.parameter_bounds = {key: (float(low), float(high)) for key, (low, high) in bounds.items()}

    @abstractmethod
    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        """Execute the algorithm and return desired velocity.

        Args:
            fish: The fish using this algorithm

        Returns:
            Tuple of (velocity_x, velocity_y) as direction (-1 to 1 range)
        """
        pass

    def mutate_parameters(self, mutation_rate: float = 0.15, mutation_strength: float = 0.2) -> None:
        """Mutate the algorithm's parameters.

        Args:
            mutation_rate: Probability of each parameter mutating
            mutation_strength: Magnitude of mutations
        """
        for key, current_value in list(self.parameters.items()):
            # Skip non-numeric parameters (they shouldn't be mutated)
            if not isinstance(current_value, (int, float)):
                continue

            if random.random() >= mutation_rate:
                continue

            bounds = self.parameter_bounds.get(key)
            if bounds:
                lower, upper = bounds
                span = upper - lower
                if span <= 0:
                    span = max(abs(current_value), 1.0)
                mutated = current_value + random.gauss(0, mutation_strength) * span
                mutated = max(lower, min(upper, mutated))
            else:
                scale = max(abs(current_value), 1.0)
                mutated = current_value + random.gauss(0, mutation_strength) * scale
                mutated = max(0.0, mutated)

            self.parameters[key] = mutated

    @classmethod
    def random_instance(cls) -> 'BehaviorAlgorithm':
        """Create a random instance of this algorithm with random parameters."""
        raise NotImplementedError("Subclasses must implement random_instance")


def _find_nearest(self, fish: 'Fish', agent_type) -> Optional[Any]:
    """Find nearest agent of given type."""
    agents = fish.environment.get_agents_of_type(agent_type)
    if not agents:
        return None
    return min(agents, key=lambda a: (a.pos - fish.pos).length())


def _safe_normalize(self, vector: Vector2) -> Vector2:
    """Safely normalize a vector, returning zero vector if length is zero.

    Args:
        vector: The vector to normalize

    Returns:
        Normalized vector or Vector2(0, 0) if vector length is zero or near-zero
    """
    length = vector.length()
    if length < 1e-6:  # Use small epsilon to handle floating point errors
        return Vector2(0, 0)
    return vector.normalize()


def _get_predator_threat(self, fish: 'Fish', max_distance: float = float('inf')) -> Tuple[Optional[Any], float, Vector2]:
    """Get information about the nearest predator threat.

    This helper method consolidates the common pattern of finding the nearest
    predator, calculating distance, and computing escape direction.

    Args:
        fish: The fish to check for threats
        max_distance: Maximum distance to consider a threat (default: infinite)

    Returns:
        Tuple of (predator, distance, escape_direction) where:
        - predator: Nearest predator agent or None if none found/in range
        - distance: Distance to predator or infinity if none
        - escape_direction: Normalized vector pointing away from predator or (0,0)
    """
    from core.entities import Crab

    nearest_predator = self._find_nearest(fish, Crab)
    if not nearest_predator:
        return None, float('inf'), Vector2(0, 0)

    distance = (nearest_predator.pos - fish.pos).length()

    if distance > max_distance:
        return None, float('inf'), Vector2(0, 0)

    escape_direction = self._safe_normalize(fish.pos - nearest_predator.pos)
    return nearest_predator, distance, escape_direction


# Inject helper methods into base class
BehaviorAlgorithm._find_nearest = _find_nearest
BehaviorAlgorithm._safe_normalize = _safe_normalize
BehaviorAlgorithm._get_predator_threat = _get_predator_threat
