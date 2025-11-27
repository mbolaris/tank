"""Predator entity logic for crabs."""

import random
from typing import TYPE_CHECKING, Optional

from core.constants import (
    CRAB_ATTACK_COOLDOWN,
    CRAB_ATTACK_ENERGY_TRANSFER,
    CRAB_IDLE_CONSUMPTION,
    CRAB_INITIAL_ENERGY,
    FRAME_RATE,
)
from core.entities.base import Agent
from core.entities.fish import Fish
from core.entities.resources import Food
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.environment import Environment
    from core.genetics import Genome


class Crab(Agent):
    """A predator crab that hunts fish and food (pure logic, no rendering)."""

    def __init__(
        self,
        environment: "Environment",
        genome: Optional["Genome"] = None,
        x: float = 100,
        y: float = 550,
        screen_width: int = 800,
        screen_height: int = 600,
    ) -> None:
        """Initialize a crab."""
        # Import here to avoid circular dependency
        from core.genetics import Genome

        # Crabs are slower and less aggressive now
        self.genome: Genome = genome if genome is not None else Genome.random()
        base_speed = 1.5  # Much slower than before (was 2)
        speed = base_speed * self.genome.speed_modifier

        super().__init__(environment, x, y, speed, screen_width, screen_height)

        # Energy system
        self.max_energy: float = CRAB_INITIAL_ENERGY * self.genome.max_energy
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

    def update(self, elapsed_time: int) -> None:
        """Update the crab state."""
        # Update cooldown
        if self.hunt_cooldown > 0:
            self.hunt_cooldown -= 1

        # Consume energy
        self.consume_energy()

        # Hunt for food (prefers food over fish now - less aggressive)
        food_sprites = self.environment.nearby_agents_by_type(
            self, 100, Food
        )  # Increased radius for food seeking
        if food_sprites:
            self.align_near(food_sprites, 1)
        else:
            # Only hunt fish if no food available and can hunt
            if self.can_hunt() and self.energy < self.max_energy * 0.7:  # Only hunt when hungry
                fish_sprites = self.environment.nearby_agents_by_type(
                    self, 80, Fish
                )  # Reduced hunting radius
                if fish_sprites:
                    # Move toward nearest fish slowly
                    self.align_near(fish_sprites, 1)

        # Stay on bottom
        self.vel.y = 0
        super().update(elapsed_time)
