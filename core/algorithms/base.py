"""Base classes and utilities for behavior algorithms.

This module contains:
- BehaviorAlgorithm base class with BehaviorHelpersMixin
- ALGORITHM_PARAMETER_BOUNDS configuration
- Helper methods for spatial queries, predator detection, and energy state

Architecture Notes:
    The BehaviorHelpersMixin provides common functionality that all behavior
    algorithms need (finding food, detecting predators, checking energy).
    This mixin pattern is preferred over method injection because:
    - Methods are visible in class definition (better IDE support)
    - Easier to understand inheritance hierarchy
    - More explicit than monkey-patching
    - Type checkers can verify method signatures
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from core.behavior.primitives.steering import safe_normalize
from core.config.fish import (
    FLEE_SPEED_CRITICAL,
    FLEE_SPEED_NORMAL,
    FLEE_THRESHOLD_CRITICAL,
    FLEE_THRESHOLD_LOW,
    FLEE_THRESHOLD_NORMAL,
)
from core.config.food import BASE_FOOD_DETECTION_RANGE, PREDATOR_DEFAULT_FAR_DISTANCE
from core.entities import Crab, Food
from core.math_utils import Vector2
from core.util.rng import require_rng_param

if TYPE_CHECKING:
    from core.entities import Fish
    from core.world import World


ALGORITHM_PARAMETER_BOUNDS = {
    # Survivor foragers only (ADR-006 / ADR-016); composable sub-behavior
    # bounds live in core/algorithms/composable/definitions.py.
    "cooperative_forager": {
        "follow_strength": (0.5, 0.9),
        "independence": (0.2, 0.5),
    },
    "food_quality_optimizer": {
        "distance_weight": (0.3, 0.7),
        "quality_weight": (0.5, 1.0),
    },
    "opportunistic_feeder": {
        "max_pursuit_distance": (50.0, 200.0),
        "speed": (0.6, 1.0),
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


class BehaviorStrategyBase(ABC):
    """Base class for registrable behavior strategies.

    Note: For type hints and protocol checking, use the BehaviorStrategy Protocol
    from core.interfaces instead. This ABC exists for implementation inheritance
    and algorithm registration. The Protocol and ABC define the same contract.
    """

    algorithm_id: str


class BehaviorHelpersMixin:
    """Reusable helper methods for behavior algorithms.

    This mixin provides common functionality needed by most behavior algorithms:
    - Spatial queries (finding nearest agents, food, predators)
    - Vector operations (safe normalization)
    - Energy state checking
    - Predator threat assessment

    Design Philosophy:
        These helpers are factored into a mixin to:
        1. Keep BehaviorAlgorithm focused on the algorithm contract
        2. Make helpers explicit and discoverable (vs method injection)
        3. Allow independent testing of helper logic
        4. Provide clear type signatures for IDE support

    Usage:
        All BehaviorAlgorithm subclasses automatically inherit these methods:

        def execute(self, fish: "Fish") -> Tuple[float, float]:
            # Use inherited helpers
            nearest_food = self._find_nearest_food(fish)
            is_critical, is_low, ratio = self._get_energy_state(fish)
            should_flee, vx, vy = self._should_flee_predator(fish)
    """

    def _find_nearest(
        self, fish: "Fish", agent_type: type, max_distance: float | None = None
    ) -> Any | None:
        """Find nearest agent of given type within optional distance limit.

        PERFORMANCE: Uses spatial queries when max_distance is specified (O(k) vs O(n)).
        Falls back to get_agents_of_type only when no distance limit is given.

        Args:
            fish: The fish searching for agents
            agent_type: Type of agent to search for
            max_distance: Optional maximum detection distance (None = unlimited)

        Returns:
            Nearest agent within range, or None if no agents found/in range
        """
        env: World = fish.environment
        fish_x = fish.pos.x
        fish_y = fish.pos.y

        if max_distance is not None:
            # OPTIMIZATION: closest_type is mathematically equivalent to
            # building the nearby_agents_by_type list and scanning it for the
            # minimum distance (same grid cells, same tie-break order - see
            # core/spatial/grid.py::closest_type) but with no intermediate list
            # allocation. Falls back to the list-then-scan path otherwise.
            closest_of_type = getattr(env, "closest_type", None)
            if closest_of_type is not None:
                return closest_of_type(fish, max_distance, agent_type)

            # OPTIMIZATION: Use spatial query instead of get_agents_of_type
            # This reduces from O(n) to O(k) where k is nearby agents
            agents = env.nearby_agents_by_type(fish, int(max_distance) + 1, agent_type)
            if not agents:
                return None

            max_distance_sq = max_distance * max_distance
            min_dist_sq = float("inf")
            nearest = None

            for agent in agents:
                # Inline distance calculation to avoid function call overhead
                dx = agent.pos.x - fish_x
                dy = agent.pos.y - fish_y
                dist_sq = dx * dx + dy * dy

                if dist_sq < min_dist_sq and dist_sq <= max_distance_sq:
                    min_dist_sq = dist_sq
                    nearest = agent

            return nearest
        else:
            # No distance limit - must check all agents
            agents = env.get_agents_of_type(agent_type)
            if not agents:
                return None

            min_dist_sq = float("inf")
            nearest = None

            for agent in agents:
                dx = agent.pos.x - fish_x
                dy = agent.pos.y - fish_y
                dist_sq = dx * dx + dy * dy
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
        return safe_normalize(vector)

    def _get_predator_threat(
        self, fish: "Fish", max_distance: float = float("inf")
    ) -> tuple[Any | None, float, Vector2]:
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
        nearest_predator = self._find_nearest(fish, Crab)
        if not nearest_predator:
            return None, float("inf"), Vector2(0, 0)

        distance = (nearest_predator.pos - fish.pos).length()

        if distance > max_distance:
            return None, float("inf"), Vector2(0, 0)

        escape_direction = self._safe_normalize(fish.pos - nearest_predator.pos)
        return nearest_predator, distance, escape_direction

    def _find_nearest_food(self, fish: "Fish") -> Any | None:
        """Find nearest food within time-based detection range.

        PERFORMANCE: Prefers the spatial grid's single-pass closest_food query
        when the environment exposes one. It is mathematically equivalent to
        building the nearby_resources list and scanning it for the minimum
        distance - same grid cells (an axis-aligned box of a given radius always
        contains the circle of that radius, so no padding is needed), same
        tie-break order (identical column/row iteration) - but with no
        intermediate list allocation. See core/spatial/grid.py::closest_food.
        Falls back to the list-then-scan path for environments without it.

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
        env: World = fish.environment

        # Performance: Use cached detection modifier from environment (updated once per frame)
        # Note: access specific property, safe to duck-type or check hasattr if strict
        detection_modifier = getattr(env, "get_detection_modifier", lambda: 1.0)()
        max_distance = BASE_FOOD_DETECTION_RANGE * detection_modifier

        closest_food = getattr(env, "closest_food", None)
        if closest_food is not None:
            return closest_food(fish, max_distance)

        max_distance_sq = max_distance * max_distance

        # OPTIMIZATION: Use dedicated nearby_resources spatial query
        # This uses the optimized food_grid in SpatialGrid
        if hasattr(env, "nearby_resources"):
            nearby = env.nearby_resources(fish, int(max_distance) + 1)
        else:
            nearby = env.nearby_agents_by_type(fish, int(max_distance) + 1, Food)

        if not nearby:
            return None

        fish_x = fish.pos.x
        fish_y = fish.pos.y
        min_dist_sq = float("inf")
        nearest = None

        for food in nearby:
            dx = food.pos.x - fish_x
            dy = food.pos.y - fish_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < min_dist_sq and dist_sq <= max_distance_sq:
                min_dist_sq = dist_sq
                nearest = food

        return nearest

    def _should_flee_predator(self, fish: "Fish") -> tuple[bool, float, float]:
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
        if nearest_predator is not None and predator_distance < flee_threshold:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return True, direction.x * flee_speed, direction.y * flee_speed

        return False, 0.0, 0.0

    def _get_energy_state(self, fish: "Fish") -> tuple[bool, bool, float]:
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


@dataclass
class BehaviorAlgorithm(BehaviorHelpersMixin, BehaviorStrategyBase):
    """Base class for all behavior algorithms.

    Each algorithm has:
    - A unique algorithm_id
    - A set of parameters that can mutate
    - An execute method that determines fish movement
    - Helper methods inherited from BehaviorHelpersMixin

    Inheritance:
        BehaviorAlgorithm inherits from:
        - BehaviorHelpersMixin: Provides _find_nearest, _safe_normalize, etc.
        - BehaviorStrategy: Marker for registrable strategies
    """

    algorithm_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    parameter_bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    rng: random.Random = field(default=cast(random.Random, None), repr=False)

    def __post_init__(self) -> None:
        if not self.parameter_bounds:
            bounds = ALGORITHM_PARAMETER_BOUNDS.get(self.algorithm_id)
            if bounds:
                self.parameter_bounds = {
                    key: (float(low), float(high)) for key, (low, high) in bounds.items()
                }
        # Ensure and validate RNG
        self.rng = require_rng_param(self.rng, f"BehaviorAlgorithm '{self.algorithm_id}'")

    @abstractmethod
    def execute(self, fish: "Fish") -> tuple[float, float]:
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
        rng: random.Random | None = None,
    ) -> None:
        """Mutate the algorithm's parameters with parameter-specific strategies.

        Args:
            mutation_rate: Base probability of each parameter mutating
            mutation_strength: Base magnitude of mutations
            use_parameter_specific: Use parameter-specific mutation rates
            adaptive_factor: Multiplier for mutation rates (1.0 = normal, <1.0 = less mutation, >1.0 = more mutation)
            rng: Random number generator for determinism. If None, uses self.rng.
        """
        _rng = rng or self.rng

        # Optimization: If mutation is disabled, return early
        if mutation_rate <= 1e-9 and mutation_strength <= 1e-9:
            return

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
            if _rng.random() >= effective_rate:
                continue

            # Apply mutation within bounds
            bounds = self.parameter_bounds.get(key)
            if bounds:
                lower, upper = bounds
                span = upper - lower
                if span <= 0:
                    span = max(abs(current_value), 1.0)
                mutated = current_value + _rng.gauss(0, effective_strength) * span
                mutated = max(lower, min(upper, mutated))
            else:
                scale = max(abs(current_value), 1.0)
                mutated = current_value + _rng.gauss(0, effective_strength) * scale
                mutated = max(0.0, mutated)

            self.parameters[key] = mutated

        # Bounds enforcement: clamp every bounded parameter, not just the ones
        # mutated above, so values arriving out of range (e.g. via crossover or
        # deserialization) cannot silently stay outside their design range.
        # Deterministic: consumes no RNG and leaves in-range values unchanged.
        for key, (lower, upper) in self.parameter_bounds.items():
            value = self.parameters.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            if value < lower:
                self.parameters[key] = lower
            elif value > upper:
                self.parameters[key] = upper

    @classmethod
    def random_instance(cls, rng: random.Random | None = None) -> "BehaviorAlgorithm":
        """Create a random instance of this algorithm with random parameters.

        Args:
            rng: Optional random.Random instance for deterministic construction.
        """
        raise NotImplementedError("Subclasses must implement random_instance")

    def to_dict(self) -> dict[str, Any]:
        """Serialize algorithm for migration/storage.

        Returns dictionary containing class name and parameters needed to
        reconstruct this algorithm instance.
        """
        return {
            "class": self.__class__.__name__,
            "algorithm_id": self.algorithm_id,
            "parameters": dict(self.parameters),  # shallow copy
        }
