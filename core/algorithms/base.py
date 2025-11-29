"""Base classes and utilities for behavior algorithms.

This module contains:
- BehaviorAlgorithm base class
- ALGORITHM_PARAMETER_BOUNDS configuration
- Helper functions for algorithm execution
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities import Fish


ALGORITHM_PARAMETER_BOUNDS = {
    "adaptive_pacer": {
        "base_speed": (0.5, 0.8),
        "energy_influence": (0.3, 0.7),
    },
    "alignment_matcher": {
        "alignment_radius": (60.0, 120.0),
        "alignment_strength": (0.5, 1.0),
    },
    "ambush_feeder": {
        "patience": (0.5, 1.0),
        "strike_distance": (30.0, 80.0),
        "strike_speed": (1.0, 1.5),
    },
    "boids_behavior": {
        "alignment_weight": (0.3, 0.7),
        "cohesion_weight": (0.3, 0.7),
        "separation_weight": (0.3, 0.7),
    },
    "border_hugger": {
        "hug_speed": (0.7, 1.1),
    },
    "bottom_feeder": {
        "preferred_depth": (0.7, 0.9),
        "search_speed": (0.4, 0.8),
    },
    "boundary_explorer": {
        "edge_preference": (0.6, 1.0),
        "exploration_speed": (0.5, 0.8),
    },
    "burst_swimmer": {
        "burst_duration": (30.0, 90.0),
        "burst_speed": (1.2, 1.6),
        "rest_duration": (60.0, 120.0),
    },
    "center_hugger": {
        "orbit_radius": (50.0, 120.0),
        "return_strength": (0.5, 0.9),
    },
    "circular_hunter": {
        "circle_radius": (40.0, 100.0),
        "circle_speed": (0.05, 0.15),
        "strike_threshold": (0.3, 0.6),
    },
    "cooperative_forager": {
        "follow_strength": (0.5, 0.9),
        "independence": (0.2, 0.5),
    },
    "corner_seeker": {
        "approach_speed": (0.4, 0.7),
    },
    "distance_keeper": {
        "approach_speed": (0.3, 0.6),
        "flee_speed": (0.8, 1.2),
        "safe_distance": (120.0, 200.0),
    },
    "dynamic_schooler": {
        "calm_cohesion": (0.3, 0.6),
        "danger_cohesion": (0.8, 1.2),
        "danger_threshold": (150.0, 250.0),
    },
    "energy_aware_food_seeker": {
        "calm_speed": (0.3, 0.6),
        "urgency_threshold": (0.3, 0.7),
        "urgent_speed": (0.8, 1.2),
    },
    "energy_balancer": {
        "max_energy_ratio": (0.7, 0.9),
        "min_energy_ratio": (0.3, 0.5),
    },
    "energy_conserver": {
        "activity_threshold": (0.4, 0.7),
        "rest_speed": (0.1, 0.3),
    },
    "erratic_evader": {
        "evasion_speed": (0.8, 1.3),
        "randomness": (0.5, 1.0),
        "threat_range": (100.0, 180.0),
    },
    "food_memory_seeker": {
        "exploration_rate": (0.2, 0.5),
        "memory_strength": (0.5, 1.0),
    },
    "food_quality_optimizer": {
        "distance_weight": (0.3, 0.7),
        "quality_weight": (0.5, 1.0),
    },
    "freeze_response": {
        "freeze_distance": (80.0, 150.0),
        "resume_distance": (200.0, 300.0),
    },
    "front_runner": {
        "independence": (0.5, 0.9),
        "leadership_strength": (0.7, 1.2),
    },
    "greedy_food_seeker": {
        "detection_range": (0.5, 1.0),
        "speed_multiplier": (0.7, 1.3),
    },
    "group_defender": {
        "group_strength": (0.6, 1.0),
        "min_group_distance": (30.0, 80.0),
    },
    "leader_follower": {
        "follow_strength": (0.6, 1.0),
        "max_follow_distance": (80.0, 150.0),
    },
    "loose_schooler": {
        "cohesion_strength": (0.3, 0.6),
        "max_distance": (100.0, 200.0),
    },
    "metabolic_optimizer": {
        "efficiency_threshold": (0.5, 0.8),
        "high_efficiency_speed": (0.7, 1.1),
        "low_efficiency_speed": (0.2, 0.4),
    },
    "mirror_mover": {
        "mirror_distance": (50.0, 100.0),
        "mirror_strength": (0.6, 1.0),
    },
    "nomadic_wanderer": {
        "direction_change_rate": (0.01, 0.05),
        "wander_strength": (0.5, 0.9),
    },
    "opportunistic_feeder": {
        "max_pursuit_distance": (50.0, 200.0),
        "speed": (0.6, 1.0),
    },
    "opportunistic_rester": {
        "active_speed": (0.5, 0.9),
        "safe_radius": (100.0, 200.0),
    },
    "panic_flee": {
        "flee_speed": (1.2, 1.8),
        "panic_distance": (100.0, 200.0),
    },
    "patrol_feeder": {
        "food_priority": (0.6, 1.0),
        "patrol_radius": (50.0, 150.0),
        "patrol_speed": (0.5, 1.0),
    },
    "perimeter_guard": {
        "orbit_radius": (70.0, 130.0),
        "orbit_speed": (0.5, 0.9),
    },
    "perpendicular_escape": {
        "escape_speed": (1.0, 1.4),
    },
    "random_explorer": {
        "change_frequency": (0.02, 0.08),
        "exploration_speed": (0.5, 0.9),
    },
    "route_patroller": {
        "patrol_speed": (0.5, 0.8),
        "waypoint_threshold": (30.0, 60.0),
    },
    "separation_seeker": {
        "min_distance": (30.0, 70.0),
        "separation_strength": (0.5, 1.0),
    },
    "spiral_escape": {
        "spiral_radius": (20.0, 60.0),
        "spiral_rate": (0.1, 0.3),
    },
    "starvation_preventer": {
        "critical_threshold": (0.2, 0.4),
        "urgency_multiplier": (1.3, 1.8),
    },
    "stealthy_avoider": {
        "awareness_range": (150.0, 250.0),
        "stealth_speed": (0.3, 0.6),
    },
    "surface_skimmer": {
        "horizontal_speed": (0.5, 1.0),
        "preferred_depth": (0.1, 0.3),
    },
    "sustainable_cruiser": {
        "consistency": (0.7, 1.0),
        "cruise_speed": (0.4, 0.7),
    },
    "territorial_defender": {
        "aggression": (0.5, 1.0),
        "territory_radius": (80.0, 150.0),
    },
    "tight_schooler": {
        "cohesion_strength": (0.7, 1.2),
        "preferred_distance": (20.0, 50.0),
    },
    "vertical_escaper": {
        "escape_speed": (1.0, 1.5),
    },
    "wall_follower": {
        "follow_speed": (0.5, 0.8),
        "wall_distance": (20.0, 60.0),
    },
    "zigzag_forager": {
        "forward_speed": (0.6, 1.0),
        "zigzag_amplitude": (0.5, 1.2),
        "zigzag_frequency": (0.02, 0.08),
    },
    # Poker interaction algorithms
    "poker_challenger": {
        "challenge_radius": (100.0, 250.0),
        "challenge_speed": (0.8, 1.3),
        "min_energy_to_challenge": (15.0, 30.0),
    },
    "poker_dodger": {
        "avoidance_radius": (80.0, 150.0),
        "avoidance_speed": (0.7, 1.1),
        "food_priority": (0.6, 1.0),
    },
    "poker_gambler": {
        "high_energy_threshold": (0.6, 0.9),
        "challenge_speed": (1.0, 1.5),
        "risk_tolerance": (0.3, 0.8),
    },
    "selective_poker": {
        "min_energy_ratio": (0.4, 0.7),
        "max_energy_ratio": (0.7, 0.95),
        "challenge_speed": (0.6, 1.0),
        "selectivity": (0.5, 0.9),
    },
    "poker_opportunist": {
        "poker_weight": (0.3, 0.7),
        "food_weight": (0.3, 0.7),
        "opportunity_radius": (80.0, 150.0),
    },
    "poker_strategist": {
        "aggression_variance": (0.1, 0.4),
        "position_awareness": (0.5, 1.0),
        "opponent_tracking": (0.3, 0.8),
        "min_energy_ratio": (0.3, 0.6),
        "challenge_speed": (0.7, 1.2),
    },
    "poker_bluffer": {
        "bluff_frequency": (0.2, 0.6),
        "aggression_swing": (0.4, 1.0),
        "unpredictability": (0.3, 0.7),
        "min_energy_to_bluff": (20.0, 40.0),
    },
    "poker_conservative": {
        "min_energy_ratio": (0.6, 0.85),
        "max_risk_tolerance": (0.1, 0.3),
        "safety_distance": (100.0, 180.0),
        "challenge_speed": (0.5, 0.9),
        "energy_advantage_required": (10.0, 30.0),
    },
}


# Parameter-specific mutation configuration
# Different parameter types benefit from different mutation strategies
PARAMETER_MUTATION_CONFIG = {
    # Speed parameters: smaller mutations (they're already normalized)
    "speed": {"base_rate": 0.15, "strength": 0.15},
    # Distance/radius parameters: medium mutations
    "distance": {"base_rate": 0.15, "strength": 0.25},
    # Ratio/threshold parameters: larger mutations (explore energy/behavior states)
    "ratio": {"base_rate": 0.20, "strength": 0.30},
    # Weight parameters: medium mutations
    "weight": {"base_rate": 0.15, "strength": 0.25},
    # Frequency/probability parameters: larger mutations
    "frequency": {"base_rate": 0.20, "strength": 0.30},
    # Energy parameters: medium mutations
    "energy": {"base_rate": 0.15, "strength": 0.25},
    # Default for unclassified parameters
    "default": {"base_rate": 0.15, "strength": 0.20},
}


def classify_parameter(param_name: str) -> str:
    """Classify parameter type based on name for mutation strategy.

    Args:
        param_name: Name of the parameter

    Returns:
        Parameter classification (speed, distance, ratio, weight, etc.)
    """
    param_lower = param_name.lower()

    # Speed-related
    if any(
        word in param_lower
        for word in ["speed", "velocity", "pace", "cruise", "swim", "chase", "flee"]
    ):
        return "speed"

    # Distance/radius-related
    if any(
        word in param_lower
        for word in [
            "radius",
            "distance",
            "range",
            "threshold",
            "detection",
            "awareness",
            "pursuit",
            "safe",
        ]
    ):
        return "distance"

    # Ratio/percentage-related
    if any(
        word in param_lower
        for word in [
            "ratio",
            "threshold",
            "influence",
            "tolerance",
            "selectivity",
            "awareness",
            "tracking",
            "variance",
        ]
    ):
        return "ratio"

    # Weight-related
    if any(
        word in param_lower
        for word in ["weight", "strength", "cohesion", "separation", "alignment", "priority"]
    ):
        return "weight"

    # Frequency/probability-related
    if any(
        word in param_lower
        for word in [
            "frequency",
            "rate",
            "probability",
            "chance",
            "bluff",
            "unpredictability",
            "swing",
        ]
    ):
        return "frequency"

    # Energy-related
    if "energy" in param_lower:
        return "energy"

    return "default"


class BehaviorStrategy(ABC):
    """Marker base class for registrable behavior strategies."""

    pass


@dataclass
class BehaviorAlgorithm(BehaviorStrategy):
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
                self.parameter_bounds = {
                    key: (float(low), float(high)) for key, (low, high) in bounds.items()
                }

    @abstractmethod
    def execute(self, fish: "Fish") -> Tuple[float, float]:
        """Execute the algorithm and return desired velocity.

        Args:
            fish: The fish using this algorithm

        Returns:
            Tuple of (velocity_x, velocity_y) as direction (-1 to 1 range)
        """
        pass

    def mutate_parameters(
        self,
        mutation_rate: float = 0.15,
        mutation_strength: float = 0.2,
        use_parameter_specific: bool = True,
        adaptive_factor: float = 1.0,
    ) -> None:
        """Mutate the algorithm's parameters with parameter-specific strategies.

        Args:
            mutation_rate: Base probability of each parameter mutating
            mutation_strength: Base magnitude of mutations
            use_parameter_specific: Use parameter-specific mutation rates
            adaptive_factor: Multiplier for mutation rates (1.0 = normal, <1.0 = less mutation, >1.0 = more mutation)
        """
        for key, current_value in list(self.parameters.items()):
            # Skip non-numeric parameters (they shouldn't be mutated)
            if not isinstance(current_value, (int, float)):
                continue

            # Get parameter-specific mutation config
            if use_parameter_specific:
                param_type = classify_parameter(key)
                config = PARAMETER_MUTATION_CONFIG.get(
                    param_type, PARAMETER_MUTATION_CONFIG["default"]
                )
                effective_rate = config["base_rate"] * adaptive_factor
                effective_strength = config["strength"] * adaptive_factor
            else:
                effective_rate = mutation_rate * adaptive_factor
                effective_strength = mutation_strength * adaptive_factor

            # Roll for mutation
            if random.random() >= effective_rate:
                continue

            # Apply mutation within bounds
            bounds = self.parameter_bounds.get(key)
            if bounds:
                lower, upper = bounds
                span = upper - lower
                if span <= 0:
                    span = max(abs(current_value), 1.0)
                mutated = current_value + random.gauss(0, effective_strength) * span
                mutated = max(lower, min(upper, mutated))
            else:
                scale = max(abs(current_value), 1.0)
                mutated = current_value + random.gauss(0, effective_strength) * scale
                mutated = max(0.0, mutated)

            self.parameters[key] = mutated

    @classmethod
    def random_instance(cls) -> "BehaviorAlgorithm":
        """Create a random instance of this algorithm with random parameters."""
        raise NotImplementedError("Subclasses must implement random_instance")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize algorithm for migration/storage.

        Returns dictionary containing class name and parameters needed to
        reconstruct this algorithm instance.
        """
        return {
            "class": self.__class__.__name__,
            "algorithm_id": self.algorithm_id,
            "parameters": dict(self.parameters),  # shallow copy
        }


def _find_nearest(self, fish: "Fish", agent_type, max_distance: Optional[float] = None) -> Optional[Any]:
    """Find nearest agent of given type within optional distance limit.

    Performance optimized to use squared distances for comparisons.

    Args:
        fish: The fish searching for agents
        agent_type: Type of agent to search for
        max_distance: Optional maximum detection distance (None = unlimited)

    Returns:
        Nearest agent within range, or None if no agents found/in range
    """
    agents = fish.environment.get_agents_of_type(agent_type)
    if not agents:
        return None

    # Performance: Use squared distances to avoid expensive sqrt operations
    # Also use static Vector2.distance_squared to avoid Vector2 allocations
    fish_x = fish.pos.x
    fish_y = fish.pos.y

    if max_distance is not None:
        max_distance_sq = max_distance * max_distance

        # Find nearest using squared distances
        min_dist_sq = float('inf')
        nearest = None

        for agent in agents:
            # Use static method - no Vector2 allocation
            dist_sq = Vector2.distance_squared(fish_x, fish_y, agent.pos.x, agent.pos.y)

            if dist_sq < min_dist_sq and dist_sq <= max_distance_sq:
                min_dist_sq = dist_sq
                nearest = agent

        return nearest
    else:
        # No distance limit - find closest using squared distances
        min_dist_sq = float('inf')
        nearest = None

        for agent in agents:
            dist_sq = Vector2.distance_squared(fish_x, fish_y, agent.pos.x, agent.pos.y)
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest = agent

        return nearest


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


def _get_predator_threat(
    self, fish: "Fish", max_distance: float = float("inf")
) -> Tuple[Optional[Any], float, Vector2]:
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
        return None, float("inf"), Vector2(0, 0)

    distance = (nearest_predator.pos - fish.pos).length()

    if distance > max_distance:
        return None, float("inf"), Vector2(0, 0)

    escape_direction = self._safe_normalize(fish.pos - nearest_predator.pos)
    return nearest_predator, distance, escape_direction


def _find_nearest_food(self, fish: "Fish") -> Optional[Any]:
    """Find nearest food within time-based detection range.

    Fish have reduced ability to detect food at night due to lower visibility.
    Detection range is modified by time of day:
    - Night: 25% of base range
    - Dawn/Dusk: 75% of base range
    - Day: 100% of base range

    Args:
        fish: The fish searching for food

    Returns:
        Nearest food within detection range, or None if no food detected
    """
    from core.constants import BASE_FOOD_DETECTION_RANGE
    from core.entities import Food

    # Performance: Use cached detection modifier from environment (updated once per frame)
    detection_modifier = fish.environment.get_detection_modifier()
    max_distance = BASE_FOOD_DETECTION_RANGE * detection_modifier

    # Use the updated _find_nearest with max_distance parameter
    return self._find_nearest(fish, Food, max_distance)


def _should_flee_predator(self, fish: "Fish") -> Tuple[bool, float, float]:
    """Check if fish should flee from predators based on energy state.

    Uses energy-aware flee thresholds:
    - Critical energy: Minimal flee distance (must risk danger for food)
    - Low energy: Moderate flee distance
    - Normal energy: Standard flee distance

    Args:
        fish: The fish to check for predator threats

    Returns:
        Tuple of (should_flee, velocity_x, velocity_y) where:
        - should_flee: True if fish should flee from a nearby predator
        - velocity_x: X component of flee velocity (0 if not fleeing)
        - velocity_y: Y component of flee velocity (0 if not fleeing)
    """
    from core.constants import (
        FLEE_SPEED_CRITICAL,
        FLEE_SPEED_NORMAL,
        FLEE_THRESHOLD_CRITICAL,
        FLEE_THRESHOLD_LOW,
        FLEE_THRESHOLD_NORMAL,
        PREDATOR_DEFAULT_FAR_DISTANCE,
    )
    from core.entities import Crab

    # Check energy state
    is_critical = fish.is_critical_energy()
    is_low = fish.is_low_energy()

    # Find nearest predator
    nearest_predator = self._find_nearest(fish, Crab)
    predator_distance = (
        (nearest_predator.pos - fish.pos).length()
        if nearest_predator
        else PREDATOR_DEFAULT_FAR_DISTANCE
    )

    # Determine flee threshold based on energy
    if is_critical:
        flee_threshold = FLEE_THRESHOLD_CRITICAL
        flee_speed = FLEE_SPEED_CRITICAL
    elif is_low:
        flee_threshold = FLEE_THRESHOLD_LOW
        flee_speed = FLEE_SPEED_NORMAL
    else:
        flee_threshold = FLEE_THRESHOLD_NORMAL
        flee_speed = FLEE_SPEED_NORMAL

    # Check if should flee
    if predator_distance < flee_threshold:
        direction = self._safe_normalize(fish.pos - nearest_predator.pos)
        return True, direction.x * flee_speed, direction.y * flee_speed

    return False, 0.0, 0.0


def _get_energy_state(self, fish: "Fish") -> Tuple[bool, bool, float]:
    """Get fish energy state information.

    Consolidates common energy checks into a single call.

    Args:
        fish: The fish to check energy state

    Returns:
        Tuple of (is_critical, is_low, energy_ratio) where:
        - is_critical: True if fish has critical energy level
        - is_low: True if fish has low energy level
        - energy_ratio: Current energy as ratio of max energy (0.0 to 1.0)
    """
    is_critical = fish.is_critical_energy()
    is_low = fish.is_low_energy()
    energy_ratio = fish.get_energy_ratio()
    return is_critical, is_low, energy_ratio


# Inject helper methods into base class
BehaviorAlgorithm._find_nearest = _find_nearest
BehaviorAlgorithm._safe_normalize = _safe_normalize
BehaviorAlgorithm._get_predator_threat = _get_predator_threat
BehaviorAlgorithm._find_nearest_food = _find_nearest_food
BehaviorAlgorithm._should_flee_predator = _should_flee_predator
BehaviorAlgorithm._get_energy_state = _get_energy_state
