"""Energy management component for entities.

This module provides the EnergyComponent class which handles all energy-related
functionality for entities, including metabolism, consumption, and energy state checks.
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

from typing import TYPE_CHECKING

from core.config.fish import (
    BABY_METABOLISM_MULTIPLIER,
    CRITICAL_ENERGY_THRESHOLD_RATIO,
    ELDER_METABOLISM_MULTIPLIER,
    EXISTENCE_ENERGY_COST,
    EXISTENCE_SIZE_EXPONENT,
    INITIAL_ENERGY_RATIO,
    LOW_ENERGY_THRESHOLD_RATIO,
    MOVEMENT_ENERGY_COST,
    MOVEMENT_SIZE_EXPONENT,
    SAFE_ENERGY_THRESHOLD_RATIO,
    SPRINT_ENERGY_COST,
    SPRINT_THRESHOLD,
    STARVATION_THRESHOLD_RATIO,
)
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities.base import LifeStage


class EnergyComponent:
    """Manages entity energy, metabolism, and starvation mechanics.

    This component encapsulates all energy-related logic for an entity, including:
    - Energy consumption based on metabolism and movement
    - Energy state checks (starving, low energy, safe energy)
    - Life stage-specific metabolism modifiers
    - Energy ratio calculations for decision-making

    Attributes:
        energy: Current energy level.
        max_energy: Maximum energy capacity.
        base_metabolism: Base metabolic rate (energy consumption per frame).
    """

    __slots__ = ("base_metabolism", "energy", "max_energy")

    def __init__(
        self,
        max_energy: float,
        base_metabolism: float,
        initial_energy_ratio: float = INITIAL_ENERGY_RATIO,
    ) -> None:
        """Initialize the energy component.

        Args:
            max_energy: Maximum energy capacity for the entity
            base_metabolism: Base metabolic rate (energy consumption per frame)
            initial_energy_ratio: Starting energy as a fraction of max (default 0.5)
        """
        self.max_energy = max_energy
        self.base_metabolism = base_metabolism
        self.energy = max_energy * initial_energy_ratio

    def calculate_burn(
        self,
        velocity: Vector2,
        speed: float,
        life_stage: "LifeStage",
        time_modifier: float = 1.0,
        size: float = 1.0,
    ) -> dict[str, float]:
        """Calculate energy burn based on metabolism and activity.

        SIMPLIFIED ENERGY SYSTEM with 3 clear costs:
        1. EXISTENCE - just being alive (linear with size)
        2. MOVEMENT - swimming (linear with speed, size^1.5)
        3. SPRINT - penalty above 70% speed (quadratic)

        Args:
            velocity: Current velocity vector of the entity.
            speed: Maximum speed of the entity.
            life_stage: Current life stage (affects all costs).
            time_modifier: Time-based modifier (e.g., for day/night cycles).
            size: Body size multiplier (0.5 for baby, 1.0+ for adult).

        Returns:
            Dict with breakdown: total, existence, metabolism, movement
        """
        from core.entities.base import LifeStage

        # Life stage modifier (applied to all costs)
        stage_multiplier = 1.0
        if life_stage == LifeStage.BABY:
            stage_multiplier = BABY_METABOLISM_MULTIPLIER
        elif life_stage == LifeStage.ELDER:
            stage_multiplier = ELDER_METABOLISM_MULTIPLIER

        # ---------------------------------------------------------------------
        # 1. EXISTENCE COST - just being alive each frame
        # Linear with size: bigger fish pay proportionally more
        # ---------------------------------------------------------------------
        existence_cost = (
            EXISTENCE_ENERGY_COST
            * time_modifier
            * (size**EXISTENCE_SIZE_EXPONENT)
            * stage_multiplier
        )

        # ---------------------------------------------------------------------
        # 2. MOVEMENT COST - swimming around
        # Linear with speed ratio, size^1.5 scaling
        # ---------------------------------------------------------------------
        movement_cost = 0.0
        sprint_cost = 0.0
        vel_length = velocity.length()

        if vel_length > 0 and speed > 0:
            speed_ratio = vel_length / speed
            size_factor = size**MOVEMENT_SIZE_EXPONENT

            # Base movement cost (linear with speed)
            movement_cost = MOVEMENT_ENERGY_COST * speed_ratio * size_factor * stage_multiplier

            # -----------------------------------------------------------------
            # 3. SPRINT PENALTY - going above cruise threshold
            # Quadratic penalty: (excess_speed)^2
            # -----------------------------------------------------------------
            if speed_ratio > SPRINT_THRESHOLD:
                excess_speed = speed_ratio - SPRINT_THRESHOLD
                sprint_cost = (
                    SPRINT_ENERGY_COST * (excess_speed**2) * size_factor * stage_multiplier
                )

        # Base metabolism (from genome) - applied separately
        metabolism = self.base_metabolism * time_modifier * stage_multiplier

        # Total energy consumption
        total_cost = existence_cost + metabolism + movement_cost + sprint_cost
        # NOTE: Mutation removed. Caller must apply energy change via modify_energy.
        # self.energy = max(0.0, self.energy - total_cost)

        return {
            "total": total_cost,
            "existence": existence_cost,
            "metabolism": metabolism,
            "movement": movement_cost + sprint_cost,  # Combined for logging
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
        """Check if entity is starving (will die soon).

        Uses ratio-based threshold to ensure consistent behavior across
        different entity sizes. A large entity at 10% is just as desperate
        as a small entity at 10%.

        Returns:
            True if energy ratio is below starvation threshold.
        """
        return self.get_energy_ratio() < STARVATION_THRESHOLD_RATIO

    def is_critical_energy(self) -> bool:
        """Check if entity is in critical energy state (emergency survival mode).

        Uses ratio-based threshold for size-independent behavior.

        Returns:
            True if energy ratio is critically low.
        """
        return self.get_energy_ratio() < CRITICAL_ENERGY_THRESHOLD_RATIO

    def is_low_energy(self) -> bool:
        """Check if entity has low energy (should prioritize finding food).

        Uses ratio-based threshold for size-independent behavior.

        Returns:
            True if energy ratio is low.
        """
        return self.get_energy_ratio() < LOW_ENERGY_THRESHOLD_RATIO

    def is_safe_energy(self) -> bool:
        """Check if entity has safe energy level (can explore/breed).

        Uses ratio-based threshold for size-independent behavior.

        Returns:
            True if energy ratio is at a safe level.
        """
        return self.get_energy_ratio() >= SAFE_ENERGY_THRESHOLD_RATIO

    def get_energy_ratio(self) -> float:
        """Get current energy as a ratio of maximum energy.

        This is useful for decision-making in behavior algorithms, as it provides
        a normalized value regardless of the entity's maximum energy capacity.

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
        """Check if entity has at least the specified energy level.

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
