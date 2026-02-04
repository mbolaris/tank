"""Energy management mixin for Fish entities.

Encapsulates all energy-related behavior:
- Energy properties (current, max, bite_size, size)
- Energy gain/loss with overflow routing
- Energy status checks (starving, critical, low, safe)
- Overflow routing to reproduction bank and food drops
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.config.fish import ENERGY_MAX_DEFAULT, OVERFLOW_ENERGY_BANK_MULTIPLIER
from core.constants import DEATH_REASON_STARVATION
from core.entities.base import EntityState
from core.fish.energy_state import EnergyState

if TYPE_CHECKING:
    from core.agents.components.reproduction_component import ReproductionComponent
    from core.energy.energy_component import EnergyComponent

logger = logging.getLogger(__name__)


class EnergyManagementMixin:
    """Mixin providing energy management for Fish entities.

    Expects the host class to have:
        _energy_component: EnergyComponent
        _lifecycle_component: LifecycleComponent (for size)
        _reproduction_component: ReproductionComponent (for overflow banking)
        state: EntityStateMachine
        _cached_is_dead: bool
        pos: Vector2
        vel: Vector2
        speed: float
        environment: World
    """

    _energy_component: "EnergyComponent"
    _reproduction_component: "ReproductionComponent"

    @property
    def energy(self) -> float:
        """Current energy level (read-only property delegating to EnergyComponent)."""
        return self._energy_component.energy

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level."""
        self._energy_component.energy = value
        if value <= 0:
            if self.state.state == EntityState.ACTIVE:
                self.state.transition(EntityState.DEAD, reason=DEATH_REASON_STARVATION)
            self._cached_is_dead = True

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity based on current size (age + genetics)."""
        return ENERGY_MAX_DEFAULT * self._lifecycle_component.size

    @property
    def bite_size(self) -> float:
        """Calculate the size of a bite this fish can take (scales with size)."""
        return 20.0 * self._lifecycle_component.size

    @property
    def size(self) -> float:
        """Current size multiplier combining age and genetics.

        Affects visual rendering scale, max energy, bite size, and turn cost.
        """
        return self._lifecycle_component.size

    def get_energy_state(self) -> EnergyState:
        """Get immutable snapshot of current energy state."""
        return EnergyState(
            current_energy=self.energy,
            max_energy=self._energy_component.max_energy,
        )

    def gain_energy(self, amount: float) -> float:
        """Gain energy from consuming food.

        Applies energy gain via modify_energy so it is recorded properly.
        Returns the amount requested to satisfy legacy callers.
        """
        self.modify_energy(amount, source="ate_food")
        return amount

    def _apply_energy_gain_internal(self, amount: float) -> float:
        """Internal logic to apply energy gain and route overflow."""
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if new_energy > self.max_energy:
            overflow = new_energy - self.max_energy
            self._energy_component.energy = self.max_energy
            self._route_overflow_energy(overflow)
        else:
            self._energy_component.energy = new_energy

        if self._energy_component.energy > 0 and self.state.state == EntityState.ACTIVE:
            self._cached_is_dead = False

        return self._energy_component.energy - old_energy

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Adjust energy by a specified amount, routing overflow productively.

        Positive amounts are capped at max_energy with overflow handling.
        Negative amounts won't go below zero.

        Returns:
            float: The actual energy change applied to the fish
        """
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if amount > 0:
            if new_energy > self.max_energy:
                overflow = new_energy - self.max_energy
                self._energy_component.energy = self.max_energy
                self._route_overflow_energy(overflow)
            else:
                self._energy_component.energy = new_energy
        else:
            final_energy = max(0.0, new_energy)
            self._energy_component.energy = final_energy
            if final_energy <= 0:
                if self.state.state == EntityState.ACTIVE:
                    self.state.transition(EntityState.DEAD, reason=DEATH_REASON_STARVATION)
                self._cached_is_dead = True
            elif self.state.state == EntityState.ACTIVE:
                self._cached_is_dead = False

        if hasattr(self, "environment") and hasattr(self.environment, "record_energy_delta"):
            delta = self._energy_component.energy - old_energy
            self.environment.record_energy_delta(self, delta, source)

        return self._energy_component.energy - old_energy

    def _route_overflow_energy(self, overflow: float) -> None:
        """Route overflow energy into reproduction bank.

        When a fish gains more energy than it can hold, this method banks
        the overflow for future reproduction. If the bank is full, excess
        is dropped as food.
        """
        if overflow <= 0:
            return

        max_bank = self.max_energy * OVERFLOW_ENERGY_BANK_MULTIPLIER
        banked = self._reproduction_component.bank_overflow_energy(overflow, max_bank=max_bank)
        remainder = overflow - banked

        if remainder > 0:
            self._spawn_overflow_food(remainder)

    def _spawn_overflow_food(self, overflow: float) -> None:
        """Convert overflow energy into a food drop near the fish."""
        if overflow < 1.0:
            return

        try:
            from core.entities.resources import Food
            from core.util.mutations import request_spawn_in
            from core.util.rng import require_rng

            rng = require_rng(self.environment, "Fish._spawn_overflow_food")
            food = Food(
                environment=self.environment,
                x=self.pos.x + rng.uniform(-20, 20),
                y=self.pos.y + rng.uniform(-20, 20),
                food_type="energy",
            )
            food.energy = min(overflow, food.max_energy)
            food.max_energy = food.energy

            if not request_spawn_in(self.environment, food, reason="overflow_food"):
                logger.warning("spawn requester unavailable, overflow food lost")

        except Exception:
            pass  # Energy lost on failure is acceptable

    def consume_energy(self, time_modifier: float = 1.0) -> None:
        """Consume energy based on metabolism and activity."""
        energy_breakdown = self._energy_component.calculate_burn(
            self.vel,
            self.speed,
            self._lifecycle_component.life_stage,
            time_modifier,
            self._lifecycle_component.size,
        )
        self.modify_energy(-energy_breakdown["total"], source="metabolism")

    def is_starving(self) -> bool:
        return self._energy_component.is_starving()

    def is_critical_energy(self) -> bool:
        return self._energy_component.is_critical_energy()

    def is_low_energy(self) -> bool:
        return self._energy_component.is_low_energy()

    def is_safe_energy(self) -> bool:
        return self._energy_component.is_safe_energy()

    def get_energy_ratio(self) -> float:
        """Get energy as a ratio of max energy (0.0-1.0)."""
        max_e = self.max_energy
        return self.energy / max_e if max_e > 0 else 0.0
