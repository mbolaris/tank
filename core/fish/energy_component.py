"""Energy management component for fish.

This module provides the EnergyComponent class which handles all energy-related
functionality for fish, including metabolism, consumption, and energy state checks.
Separating energy logic into its own component improves code organization and testability.
"""

from typing import TYPE_CHECKING
from core.math_utils import Vector2
from core.constants import (
    INITIAL_ENERGY_RATIO,
    BABY_METABOLISM_MULTIPLIER,
    ELDER_METABOLISM_MULTIPLIER,
    STARVATION_THRESHOLD,
    CRITICAL_ENERGY_THRESHOLD,
    LOW_ENERGY_THRESHOLD,
    SAFE_ENERGY_THRESHOLD
)

if TYPE_CHECKING:
    from core.entities import LifeStage


class EnergyComponent:
    """Manages fish energy, metabolism, and starvation mechanics.

    This component encapsulates all energy-related logic for a fish, including:
    - Energy consumption based on metabolism and movement
    - Energy state checks (starving, low energy, safe energy)
    - Life stage-specific metabolism modifiers
    - Energy ratio calculations for decision-making

    Attributes:
        energy: Current energy level
        max_energy: Maximum energy capacity
        base_metabolism: Base metabolic rate
        existence_cost: Energy cost for just being alive per frame
        movement_cost_multiplier: Multiplier for movement-based energy consumption
        sharp_turn_cost: Additional energy cost for sharp turns
    """

    # Energy consumption constants (reduced for sustainable evolution)
    EXISTENCE_ENERGY_COST = 0.01  # Cost just for being alive per frame (reduced for better survival)
    MOVEMENT_ENERGY_COST = 0.015  # Movement-based energy consumption multiplier (reduced)
    SHARP_TURN_ENERGY_COST = 0.05  # Additional cost for sharp turns (reduced from 0.08)
    SHARP_TURN_DOT_THRESHOLD = -0.85  # Dot product threshold for detecting sharp turns

    def __init__(self, max_energy: float, base_metabolism: float,
                 initial_energy_ratio: float = INITIAL_ENERGY_RATIO):
        """Initialize the energy component.

        Args:
            max_energy: Maximum energy capacity for the fish
            base_metabolism: Base metabolic rate (energy consumption per frame)
            initial_energy_ratio: Starting energy as a fraction of max (default 0.5)
        """
        self.max_energy = max_energy
        self.base_metabolism = base_metabolism
        self.energy = max_energy * initial_energy_ratio

    def consume_energy(self, velocity: Vector2, speed: float, life_stage: 'LifeStage',
                      time_modifier: float = 1.0) -> None:
        """Consume energy based on metabolism and activity.

        Energy consumption includes:
        - Existence cost: Fixed cost for being alive
        - Metabolic cost: Base metabolism adjusted by genetics and life stage
        - Movement cost: Based on current velocity and speed

        Args:
            velocity: Current velocity vector of the fish
            speed: Maximum speed of the fish
            life_stage: Current life stage (affects metabolism)
            time_modifier: Time-based modifier (e.g., for day/night cycles)
        """
        from core.entities import LifeStage

        # Existence cost - flat rate for just being alive
        total_cost = self.EXISTENCE_ENERGY_COST * time_modifier

        # Base metabolism (affected by genes and life stage)
        metabolism = self.base_metabolism * time_modifier

        # Additional cost for movement
        if velocity.length() > 0:
            movement_cost = self.MOVEMENT_ENERGY_COST * velocity.length() / speed
            metabolism += movement_cost

        # Apply life stage modifiers to metabolism (not existence cost)
        if life_stage == LifeStage.BABY:
            metabolism *= BABY_METABOLISM_MULTIPLIER  # Babies need less energy
        elif life_stage == LifeStage.ELDER:
            metabolism *= ELDER_METABOLISM_MULTIPLIER  # Elders need more energy

        # Total energy consumption
        total_cost += metabolism
        self.energy = max(0, self.energy - total_cost)

    def gain_energy(self, amount: float) -> None:
        """Gain energy from consuming food.

        Args:
            amount: Amount of energy to gain (will not exceed max_energy)
        """
        self.energy = min(self.max_energy, self.energy + amount)

    def is_starving(self) -> bool:
        """Check if fish is starving (will die soon).

        Returns:
            bool: True if energy is below starvation threshold
        """
        return self.energy < STARVATION_THRESHOLD

    def is_critical_energy(self) -> bool:
        """Check if fish is in critical energy state (emergency survival mode).

        Returns:
            bool: True if energy is critically low
        """
        return self.energy < CRITICAL_ENERGY_THRESHOLD

    def is_low_energy(self) -> bool:
        """Check if fish has low energy (should prioritize finding food).

        Returns:
            bool: True if energy is low
        """
        return self.energy < LOW_ENERGY_THRESHOLD

    def is_safe_energy(self) -> bool:
        """Check if fish has safe energy level (can explore/breed).

        Returns:
            bool: True if energy is at a safe level
        """
        return self.energy >= SAFE_ENERGY_THRESHOLD

    def get_energy_ratio(self) -> float:
        """Get current energy as a ratio of maximum energy.

        This is useful for decision-making in behavior algorithms, as it provides
        a normalized value regardless of the fish's maximum energy capacity.

        Returns:
            float: Energy ratio between 0.0 (empty) and 1.0 (full)
        """
        return self.energy / self.max_energy if self.max_energy > 0 else 0.0

    def has_enough_energy(self, threshold: float) -> bool:
        """Check if fish has at least the specified energy level.

        Args:
            threshold: Energy threshold to check against

        Returns:
            bool: True if current energy >= threshold
        """
        return self.energy >= threshold

    def get_energy_state_description(self) -> str:
        """Get a human-readable description of the current energy state.

        Returns:
            str: Description of energy state (e.g., "Starving", "Low Energy", "Safe")
        """
        if self.is_starving():
            return "Starving"
        elif self.is_critical_energy():
            return "Critical Energy"
        elif self.is_low_energy():
            return "Low Energy"
        elif self.is_safe_energy():
            return "Safe Energy"
        else:
            return "Moderate Energy"
