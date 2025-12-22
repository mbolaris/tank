"""Energy management component for fish.

This module provides the EnergyComponent class which handles all energy-related
functionality for fish, including metabolism, consumption, and energy state checks.
Separating energy logic into its own component improves code organization and testability.

Protocol Conformance:
--------------------
EnergyComponent provides the implementation for the EnergyHolder protocol.
While the component itself doesn't directly inherit from the protocol (since
Protocols are structural, not nominal), it satisfies the EnergyHolder contract:
- energy property (read/write)
- max_energy property (read-only)
- modify_energy(amount) method

The Fish class wraps this component and exposes these as its own properties,
making Fish satisfy EnergyHolder.
"""

from typing import TYPE_CHECKING, Dict

from core.config.fish import (
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
    SMALL_FISH_METABOLISM_MIN_MULTIPLIER,
    SMALL_FISH_METABOLISM_THRESHOLD,
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

        # Apply size-based discount for small adult fish
        # Small fish (below threshold) get a metabolism reduction
        # Linearly interpolates from 1.0 at threshold to MIN_MULTIPLIER at size 0.5
        if size < SMALL_FISH_METABOLISM_THRESHOLD and life_stage != LifeStage.BABY:
            # Calculate how far below threshold (0 at threshold, 1 at size 0.5)
            size_below = (SMALL_FISH_METABOLISM_THRESHOLD - size) / (SMALL_FISH_METABOLISM_THRESHOLD - 0.5)
            size_below = min(1.0, max(0.0, size_below))  # Clamp to [0, 1]
            # Interpolate multiplier from 1.0 down to MIN_MULTIPLIER
            size_multiplier = 1.0 - (1.0 - SMALL_FISH_METABOLISM_MIN_MULTIPLIER) * size_below
            metabolism *= size_multiplier
            movement_cost *= size_multiplier

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

    def modify_energy(self, amount: float) -> None:
        """Modify energy by the specified amount.

        This implements the EnergyHolder protocol's modify_energy method.
        Positive amounts increase energy (capped at max_energy).
        Negative amounts decrease energy (floored at 0).

        Note: For Fish entities, use Fish.modify_energy() instead as it
        handles overflow routing (reproduction, food drops).

        Args:
            amount: Amount to add (positive) or subtract (negative).
        """
        new_energy = self.energy + amount
        self.energy = max(0.0, min(self.max_energy, new_energy))

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


# =============================================================================
# Protocol Conformance Verification
# =============================================================================
# This section verifies that EnergyComponent can satisfy the EnergyHolder
# protocol. While Python's Protocol is structural (duck typing), having
# an explicit check documents the intent and catches breaking changes early.


def _verify_protocol_conformance() -> None:
    """Verify EnergyComponent satisfies EnergyHolder protocol.

    This function is called at module load time to ensure the component
    implements the required interface. Any missing methods will raise
    an assertion error with a helpful message.
    """
    from core.interfaces import EnergyHolder

    # Create a minimal instance for protocol checking
    component = EnergyComponent(max_energy=100.0, base_metabolism=0.1)

    # Verify protocol conformance using isinstance (works with @runtime_checkable)
    assert isinstance(component, EnergyHolder), (
        "EnergyComponent does not satisfy EnergyHolder protocol. "
        "Missing required attributes or methods: energy, max_energy, modify_energy"
    )


# Run verification at module load time (disabled in production for performance)
# Uncomment the following line during development to enable runtime checks:
# _verify_protocol_conformance()
