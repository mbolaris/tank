"""Energy management component for fish.

This module provides the EnergyComponent class which handles all energy-related
functionality for fish, including metabolism, consumption, and energy state checks.
Separating energy logic into its own component improves code organization and testability.
"""

from typing import TYPE_CHECKING, Dict

from core.constants import (
    BABY_METABOLISM_MULTIPLIER,
    CRITICAL_ENERGY_THRESHOLD_RATIO,
    ELDER_METABOLISM_MULTIPLIER,
    EXISTENCE_ENERGY_COST,
    HIGH_SPEED_ENERGY_COST,
    HIGH_SPEED_THRESHOLD,
    INITIAL_ENERGY_RATIO,
    LOW_ENERGY_THRESHOLD_RATIO,
    MOVEMENT_ENERGY_COST,
    MOVEMENT_SIZE_MULTIPLIER,
    SAFE_ENERGY_THRESHOLD_RATIO,
    STARVATION_THRESHOLD_RATIO,
)
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities.base import LifeStage


class EnergyComponent:
    """Manages fish energy, metabolism, and starvation mechanics.

    This component encapsulates all energy-related logic for a fish, including:
    - Energy consumption based on metabolism and movement
    - Energy state checks (starving, low energy, safe energy)
    - Life stage-specific metabolism modifiers
    - Energy ratio calculations for decision-making

    Attributes:
        energy: Current energy level.
        max_energy: Maximum energy capacity.
        base_metabolism: Base metabolic rate (energy consumption per frame).
    """

    __slots__ = ("energy", "max_energy", "base_metabolism")

    def __init__(
        self,
        max_energy: float,
        base_metabolism: float,
        initial_energy_ratio: float = INITIAL_ENERGY_RATIO,
    ) -> None:
        """Initialize the energy component.

        Args:
            max_energy: Maximum energy capacity for the fish
            base_metabolism: Base metabolic rate (energy consumption per frame)
            initial_energy_ratio: Starting energy as a fraction of max (default 0.5)
        """
        self.max_energy = max_energy
        self.base_metabolism = base_metabolism
        self.energy = max_energy * initial_energy_ratio

    def consume_energy(
        self,
        velocity: Vector2,
        speed: float,
        life_stage: "LifeStage",
        time_modifier: float = 1.0,
        size: float = 1.0,
    ) -> Dict[str, float]:
        """Consume energy based on metabolism and activity.

        Energy consumption includes:
        - Existence cost: Fixed cost for being alive
        - Metabolic cost: Base metabolism adjusted by genetics and life stage
        - Movement cost: Based on current velocity and speed
        - Size scaling: Larger fish consume more energy

        Args:
            velocity: Current velocity vector of the fish.
            speed: Maximum speed of the fish.
            life_stage: Current life stage (affects metabolism).
            time_modifier: Time-based modifier (e.g., for day/night cycles).
            size: Body size multiplier (0.5 for baby, 1.0 for adult).
        """
        # Import LifeStage at runtime to avoid circular dependency
        from core.entities.base import LifeStage

        # Existence cost - scales with body size squared (larger fish need much more energy to exist)
        # Using size^1.3 makes existence more expensive for large fish while not punishing small ones too much
        existence_size_factor = size ** 1.3
        existence_cost = EXISTENCE_ENERGY_COST * time_modifier * existence_size_factor

        # Base metabolism (affected by genes and life stage)
        metabolism = self.base_metabolism * time_modifier
        movement_cost = 0.0

        # Additional cost for movement - scales with body size
        # Size scaling is non-linear: larger fish use disproportionately more energy
        vel_length = velocity.length()
        if vel_length > 0:
            size_factor = size ** MOVEMENT_SIZE_MULTIPLIER
            speed_ratio = vel_length / speed if speed > 0 else 0

            # Base movement cost (linear with speed)
            movement_cost = MOVEMENT_ENERGY_COST * speed_ratio * size_factor

            # Progressive speed cost - scales smoothly from 0 to max
            # Uses quadratic scaling so going faster is increasingly expensive
            # This replaces the threshold-based system with smooth progression
            # At 50% speed: 0.25x multiplier, at 100% speed: 1.0x multiplier
            progressive_speed_cost = HIGH_SPEED_ENERGY_COST * (speed_ratio ** 2) * size_factor
            movement_cost += progressive_speed_cost

            # Additional penalty above threshold for really fast movement (stacks with progressive)
            if speed_ratio > HIGH_SPEED_THRESHOLD:
                excess_speed = speed_ratio - HIGH_SPEED_THRESHOLD
                # Cubic scaling above threshold - very expensive to go full speed
                burst_speed_cost = HIGH_SPEED_ENERGY_COST * 2.0 * (excess_speed ** 3) * size_factor
                movement_cost += burst_speed_cost

            metabolism += movement_cost

        # Apply life stage modifiers to metabolism (not existence cost)
        stage_multiplier = 1.0
        if life_stage == LifeStage.BABY:
            stage_multiplier = BABY_METABOLISM_MULTIPLIER  # Babies need less energy
        elif life_stage == LifeStage.ELDER:
            stage_multiplier = ELDER_METABOLISM_MULTIPLIER  # Elders need more energy

        movement_cost *= stage_multiplier
        metabolism *= stage_multiplier

        # Total energy consumption
        total_cost = existence_cost + metabolism
        self.energy = max(0.0, self.energy - total_cost)

        return {
            "total": total_cost,
            "existence": existence_cost,
            "metabolism": metabolism - movement_cost,
            "movement": movement_cost,
        }

    def gain_energy(self, amount: float) -> None:
        """Gain energy from consuming food.

        Args:
            amount: Amount of energy to gain (will not exceed max_energy).
        """
        self.energy = min(self.max_energy, self.energy + amount)

    def is_starving(self) -> bool:
        """Check if fish is starving (will die soon).

        Uses ratio-based threshold to ensure consistent behavior across
        different fish sizes. A large fish at 10% is just as desperate
        as a small fish at 10%.

        Returns:
            True if energy ratio is below starvation threshold.
        """
        return self.get_energy_ratio() < STARVATION_THRESHOLD_RATIO

    def is_critical_energy(self) -> bool:
        """Check if fish is in critical energy state (emergency survival mode).

        Uses ratio-based threshold for size-independent behavior.

        Returns:
            True if energy ratio is critically low.
        """
        return self.get_energy_ratio() < CRITICAL_ENERGY_THRESHOLD_RATIO

    def is_low_energy(self) -> bool:
        """Check if fish has low energy (should prioritize finding food).

        Uses ratio-based threshold for size-independent behavior.

        Returns:
            True if energy ratio is low.
        """
        return self.get_energy_ratio() < LOW_ENERGY_THRESHOLD_RATIO

    def is_safe_energy(self) -> bool:
        """Check if fish has safe energy level (can explore/breed).

        Uses ratio-based threshold for size-independent behavior.

        Returns:
            True if energy ratio is at a safe level.
        """
        return self.get_energy_ratio() >= SAFE_ENERGY_THRESHOLD_RATIO

    def get_energy_ratio(self) -> float:
        """Get current energy as a ratio of maximum energy.

        This is useful for decision-making in behavior algorithms, as it provides
        a normalized value regardless of the fish's maximum energy capacity.

        Returns:
            Energy ratio between 0.0 (empty) and 1.0 (full).
        """
        return self.energy / self.max_energy if self.max_energy > 0 else 0.0

    @property
    def energy_percentage(self) -> float:
        """Get current energy as a percentage (0-100).

        Convenience property for UI display and logging.

        Returns:
            Energy percentage between 0.0 and 100.0.
        """
        return self.get_energy_ratio() * 100.0

    def has_enough_energy(self, threshold: float) -> bool:
        """Check if fish has at least the specified energy level.

        Args:
            threshold: Energy threshold to check against.

        Returns:
            True if current energy >= threshold.
        """
        return self.energy >= threshold

    def get_energy_state_description(self) -> str:
        """Get a human-readable description of the current energy state.

        Returns:
            Description of energy state (e.g., "Starving", "Low Energy", "Safe").
        """
        if self.is_starving():
            return "Starving"
        if self.is_critical_energy():
            return "Critical Energy"
        if self.is_low_energy():
            return "Low Energy"
        if self.is_safe_energy():
            return "Safe Energy"
        return "Moderate Energy"
