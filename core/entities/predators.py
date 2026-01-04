"""Predator entity logic for crabs."""

from typing import TYPE_CHECKING, Optional

from core.config.entities import (
    CRAB_ATTACK_COOLDOWN,
    CRAB_ATTACK_ENERGY_TRANSFER,
    CRAB_IDLE_CONSUMPTION,
    CRAB_INITIAL_ENERGY,
)
from core.entities.base import Agent
from core.entities.fish import Fish
from core.entities.resources import Food
from core.genetics import Genome

if TYPE_CHECKING:
    from core.world import World


class Crab(Agent):
    """A predator crab that hunts fish and food (pure logic, no rendering)."""

    def __init__(
        self,
        environment: "World",
        genome: Optional["Genome"] = None,
        x: float = 100,
        y: float = 550,
    ) -> None:
        """Initialize a crab."""
        # Use require_rng for deterministic genome creation
        from core.util.rng import require_rng

        # Crabs are slower and less aggressive now
        if genome is not None:
            self.genome: Genome = genome
        else:
            rng = require_rng(environment, "Crab.__init__.genome")
            self.genome = Genome.random(rng=rng)
        base_speed = 1.5  # Much slower than before (was 2)
        speed = base_speed * self.genome.speed_modifier

        super().__init__(environment, x, y, speed)

        self.is_predator = True

        # Energy system - max energy based on size
        self.max_energy: float = CRAB_INITIAL_ENERGY * self.genome.physical.size_modifier.value
        self.energy: float = self.max_energy

        # Hunting mechanics
        self.hunt_cooldown: int = 0

    def can_hunt(self) -> bool:
        """Check if crab can hunt (cooldown expired)."""
        return self.hunt_cooldown <= 0

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Modify energy and record delta."""
        old_energy = self.energy
        new_energy = self.energy + amount
        self.energy = max(0.0, min(self.max_energy, new_energy))

        delta = self.energy - old_energy
        if delta != 0 and hasattr(self.environment, "record_energy_delta"):
            self.environment.record_energy_delta(self, delta, source)
        return delta

    def consume_energy(self) -> None:
        """Consume energy based on metabolism."""
        metabolism = CRAB_IDLE_CONSUMPTION * self.genome.metabolism_rate
        self.modify_energy(-metabolism, source="metabolism")

    def eat_fish(self, fish: Fish) -> None:
        """Eat a fish and gain energy."""
        self.modify_energy(CRAB_ATTACK_ENERGY_TRANSFER, source="ate_fish")
        self.hunt_cooldown = CRAB_ATTACK_COOLDOWN

    def eat_food(self, food: "Food") -> None:
        """Eat food and gain energy."""
        energy_gained = food.get_energy_value()
        self.modify_energy(energy_gained, source="ate_food")

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ) -> "EntityUpdateResult":
        """Update the crab state.

        Simple patrol behavior: crab walks back and forth across the tank bottom.
        Eating is handled by the collision system when the crab bumps into food/fish.
        """
        from core.entities.base import EntityUpdateResult

        # Update cooldown
        if self.hunt_cooldown > 0:
            self.hunt_cooldown -= 1

        # Consume energy
        self.consume_energy()

        # Simple patrol: just keep walking in current direction
        # If no horizontal velocity, pick a random direction (use environment RNG)
        if abs(self.vel.x) < 0.1:
            from core.util.rng import require_rng

            rng = require_rng(self.environment, "Crab.update.patrol")
            direction = rng.choice([-1, 1])
            self.vel.x = direction * self.speed

        # Stay on bottom (no vertical movement)
        self.vel.y = 0

        # Call parent update which handles position updates and boundary bouncing
        super().update(frame_count, time_modifier, time_of_day)

        return EntityUpdateResult()
