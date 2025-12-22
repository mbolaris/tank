"""Predator entity logic for crabs."""

import random
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
    from core.environment import Environment
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
        # Crabs are slower and less aggressive now
        self.genome: Genome = genome if genome is not None else Genome.random()
        base_speed = 1.5  # Much slower than before (was 2)
        speed = base_speed * self.genome.speed_modifier

        super().__init__(environment, x, y, speed)

        self.is_predator = True

        # Energy system - max energy based on size
        self.max_energy: float = (
            CRAB_INITIAL_ENERGY * self.genome.physical.size_modifier.value
        )
        self.energy: float = self.max_energy

        # Hunting mechanics
        self.hunt_cooldown: int = 0

    def can_hunt(self) -> bool:
        """Check if crab can hunt (cooldown expired)."""
        return self.hunt_cooldown <= 0

    def consume_energy(self) -> None:
        """Consume energy based on metabolism."""
        metabolism = CRAB_IDLE_CONSUMPTION * self.genome.metabolism_rate
        self.energy = max(0, self.energy - metabolism)

    def eat_fish(self, fish: Fish) -> None:
        """Eat a fish and gain energy."""
        self.energy = min(self.max_energy, self.energy + CRAB_ATTACK_ENERGY_TRANSFER)
        self.hunt_cooldown = CRAB_ATTACK_COOLDOWN

    def eat_food(self, food: "Food") -> None:
        """Eat food and gain energy."""
        energy_gained = food.get_energy_value()
        self.energy = min(self.max_energy, self.energy + energy_gained)



    def update(self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None) -> "EntityUpdateResult":
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
        # If no horizontal velocity, pick a random direction
        if abs(self.vel.x) < 0.1:
            direction = random.choice([-1, 1])
            self.vel.x = direction * self.speed

        # Stay on bottom (no vertical movement)
        self.vel.y = 0

        # Call parent update which handles position updates and boundary bouncing
        super().update(frame_count, time_modifier, time_of_day)

        return EntityUpdateResult()
