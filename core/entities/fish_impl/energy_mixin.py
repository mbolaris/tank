"""Energy management mixin for Fish."""

import random
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.config.fish import (
    ENERGY_MAX_DEFAULT,
    ENERGY_MODERATE_MULTIPLIER,
    OVERFLOW_ENERGY_BANK_MULTIPLIER,
)
from core.entities.base import EntityState
from core.fish.energy_component import EnergyComponent

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.genetics import Genome
    from core.fish.lifecycle_component import LifecycleComponent
    from core.fish.reproduction_component import ReproductionComponent
    from core.math_utils import Vector2
    from core.entities.base import _StateContainer  # internal detail of Agent/Entity


class FishEnergyMixin:
    """Mixin class for Fish energy management logic.
    
    Expected attributes on host:
        _energy_component: EnergyComponent
        _lifecycle_component: LifecycleComponent
        _reproduction_component: ReproductionComponent
        ecosystem: Optional[EcosystemManager]
        environment: World/Environment
        genome: Genome
        pos: Vector2
        vel: Vector2
        speed: float
        state: EntityState
        _cached_is_dead: bool
    """

    # Type hints for expected attributes (for mypy)
    if TYPE_CHECKING:
        _energy_component: EnergyComponent
        _lifecycle_component: "LifecycleComponent"
        _reproduction_component: "ReproductionComponent"
        ecosystem: Optional["EcosystemManager"]
        environment: Any
        genome: "Genome"
        pos: "Vector2"
        vel: "Vector2"
        speed: float
        state: "_StateContainer"  # Actually Entity._state logic, exposed via self.state logic
        _cached_is_dead: bool

    @property
    def energy(self) -> float:
        """Current energy level (read-only property delegating to EnergyComponent)."""
        return self._energy_component.energy

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level."""
        self._energy_component.energy = value
        # OPTIMIZATION: Update dead cache if energy drops to/below zero
        if value <= 0:
            if self.state.state == EntityState.ACTIVE:
                self.state.transition(EntityState.DEAD, reason="starvation")
            self._cached_is_dead = True

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity based on current size (age + genetics).

        A fish's max energy grows as they physically grow from baby to adult.
        Baby fish (size ~0.35-0.5) have less capacity than adults (adult size scales with genetic size_modifier which ranges 0.5-2.0).
        """
        return ENERGY_MAX_DEFAULT * self._lifecycle_component.size

    @property
    def bite_size(self) -> float:
        """Calculate the size of a bite this fish can take.

        Bite size scales with fish size.
        """
        # Base bite size is 20.0 energy units
        # Scales with size (larger fish take bigger bites)
        return 20.0 * self._lifecycle_component.size

    def gain_energy(self, amount: float) -> float:
        """Gain energy from consuming food, routing overflow productively.

        Uses the fish's dynamic max_energy (based on current size) rather than
        the static value in EnergyComponent. Any overflow is used for asexual
        reproduction if eligible, otherwise dropped as food.

        Args:
            amount: Amount of energy to gain.

        Returns:
            float: Actual energy gained by the fish (capped by max_energy)
        """
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if new_energy > self.max_energy:
            # We have overflow - route it productively
            overflow = new_energy - self.max_energy
            self._energy_component.energy = self.max_energy
            self._route_overflow_energy(overflow)
        else:
            self._energy_component.energy = new_energy

        # FIX: Ensure fish is marked alive if it has energy and state is active
        # This prevents "zombie" fish where cache says dead but energy > 0
        if self._energy_component.energy > 0 and self.state.state == EntityState.ACTIVE:
            self._cached_is_dead = False

        return self._energy_component.energy - old_energy

    def modify_energy(self, amount: float) -> float:
        """Adjust energy by a specified amount, routing overflow productively.

        Positive amounts are capped at max_energy. Any overflow is first used
        to attempt asexual reproduction, then dropped as food if reproduction
        isn't possible. Negative amounts won't go below zero.

        This provides a simple interface for external systems (like poker) to
        modify energy without embedding their logic in the fish.

        Returns:
            float: The actual energy change applied to the fish
        """
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if amount > 0:
            if new_energy > self.max_energy:
                # We have overflow - try to use it productively
                overflow = new_energy - self.max_energy
                self._energy_component.energy = self.max_energy
                self._route_overflow_energy(overflow)
            else:
                self._energy_component.energy = new_energy
        else:
            # Negative amount - don't go below zero
            final_energy = max(0.0, new_energy)
            self._energy_component.energy = final_energy
            # OPTIMIZATION: Update dead cache if energy drops to zero
            if final_energy <= 0:
                if self.state.state == EntityState.ACTIVE:
                    self.state.transition(EntityState.DEAD, reason="starvation")
                self._cached_is_dead = True
            elif self.state.state == EntityState.ACTIVE:
                # If energy is positive and state is active, ensure we aren't cached as dead
                self._cached_is_dead = False

        return self._energy_component.energy - old_energy

    def _route_overflow_energy(self, overflow: float) -> None:
        """Route overflow energy into reproduction bank.

        When a fish gains more energy than it can hold, this method banks
        the overflow for future reproduction. Actual reproduction is handled
        separately by update_reproduction in the normal lifecycle.

        If the bank is full, excess is dropped as food to maintain energy
        conservation.

        Args:
            overflow: Amount of energy exceeding max capacity
        """
        if overflow <= 0:
            return

        # Bank the overflow (capped) so it can fund future births even if the fish
        # is currently too young or on cooldown. Prefer banking over dropping food.
        max_bank = self.max_energy * OVERFLOW_ENERGY_BANK_MULTIPLIER
        banked = self._reproduction_component.bank_overflow_energy(overflow, max_bank=max_bank)
        remainder = overflow - banked

        # Note: We do NOT record banked energy as an outflow.
        # The energy stays within the fish population (in an internal bank).
        # Only overflow_food (energy dropped as food) is a true external outflow.

        # If the bank is full, spill the remainder as food to maintain energy conservation.
        if remainder > 0:
            self._spawn_overflow_food(remainder)

    def _spawn_overflow_food(self, overflow: float) -> None:
        """Convert overflow energy into a food drop near the fish.

        Args:
            overflow: Amount of energy to convert to food
        """
        # Only drop food if we have meaningful overflow
        if overflow < 1.0:
            return

        try:
            from core.entities.resources import Food

            # Create food near the fish
            # Use environment RNG if available, or fallback to seeded random if world provided none
            rng = getattr(self.environment, "rng", random)
            food = Food(
                environment=self.environment,
                x=self.pos.x + rng.uniform(-20, 20),
                y=self.pos.y + rng.uniform(-20, 20),
                food_type="energy",  # Use energy type for overflow
            )
            # Set food energy to match overflow
            food.energy = min(overflow, food.max_energy)
            food.max_energy = food.energy

            # Add to environment if possible
            if hasattr(self.environment, "add_entity"):
                self.environment.add_entity(food)

            # Track as ecosystem outflow (fish overflow → food)
            if self.ecosystem is not None:
                self.ecosystem.record_energy_burn("overflow_food", food.energy)
        except Exception:
            # If food creation fails, the energy is simply lost
            # This is acceptable - it's overflow energy anyway
            pass

    def consume_energy(self, time_modifier: float = 1.0) -> None:
        """Consume energy based on metabolism and activity.

        Delegates to EnergyComponent for cleaner code organization.
        Calculates and reports detailed breakdown of energy sinks to the ecosystem.

        Args:
            time_modifier: Modifier for time-based effects (e.g., day/night)
        """
        energy_breakdown = self._energy_component.consume_energy(
            self.vel,
            self.speed,
            self._lifecycle_component.life_stage,
            time_modifier,
            self._lifecycle_component.size,
        )

        # OPTIMIZATION: Update dead cache if energy drops to zero
        if self._energy_component.energy <= 0:
            if self.state.state == EntityState.ACTIVE:
                self.state.transition(EntityState.DEAD, reason="starvation")
            self._cached_is_dead = True

        if self.ecosystem is not None:
            # Report existence cost (size-based baseline)
            self.ecosystem.record_energy_burn("existence", energy_breakdown["existence"])

            # Report movement cost
            self.ecosystem.record_energy_burn("movement", energy_breakdown["movement"])

            # Split metabolism into Base vs Traits
            # The 'metabolism' value from component is (BaseRate * TimeMod * StageMod)
            # Genome.metabolism_rate = 1.0 (Base) + Traits
            # So we can split the cost proportionally
            metabolism_total = energy_breakdown["metabolism"]
            rate = self.genome.metabolism_rate

            # Avoid division by zero
            if rate > 0:
                # Calculate what fraction of the rate is due to traits (anything above 1.0)
                trait_fraction = max(0.0, (rate - 1.0) / rate)
                trait_cost = metabolism_total * trait_fraction
                base_cost = metabolism_total - trait_cost
            else:
                trait_cost = 0.0
                base_cost = metabolism_total

            self.ecosystem.record_energy_burn("metabolism", base_cost)
            self.ecosystem.record_energy_burn("trait_maintenance", trait_cost)

    def is_starving(self) -> bool:
        """Check if fish is starving (low energy)."""
        return self._energy_component.is_starving()

    def is_critical_energy(self) -> bool:
        """Check if fish is in critical energy state (emergency survival mode)."""
        return self._energy_component.is_critical_energy()

    def is_low_energy(self) -> bool:
        """Check if fish has low energy (should prioritize food)."""
        return self._energy_component.is_low_energy()

    def is_safe_energy(self) -> bool:
        """Check if fish has safe energy level (can explore/breed)."""
        return self._energy_component.is_safe_energy()

    def get_energy_ratio(self) -> float:
        """Get energy as a ratio of max energy (0.0-1.0)."""
        max_energy = self.max_energy
        return self.energy / max_energy if max_energy > 0 else 0.0
