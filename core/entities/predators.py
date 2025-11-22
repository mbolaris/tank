"""Predator entity logic for crabs and jellyfish."""

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


class Jellyfish(Agent):
    """A poker-evaluating jellyfish that plays poker with fish."""

    # Constants for jellyfish
    INITIAL_ENERGY = 1000.0
    ENERGY_DECAY_RATE = 0.5  # Energy lost per frame (slower than fish metabolism)
    POKER_AGGRESSION = 0.4  # Fixed conservative poker strategy (0.0-1.0)

    def __init__(
        self,
        environment: "Environment",
        x: float,
        y: float,
        jellyfish_id: int = 0,
        screen_width: int = 800,
        screen_height: int = 600,
    ) -> None:
        """Initialize a jellyfish."""
        # Jellyfish drift slowly
        speed = 0.8
        super().__init__(environment, x, y, speed, screen_width, screen_height)

        # Energy system
        self.max_energy: float = self.INITIAL_ENERGY
        self.energy: float = self.INITIAL_ENERGY

        # Tracking
        self.jellyfish_id: int = jellyfish_id
        self.age: int = 0

        # Poker system
        self.poker_cooldown: int = 0
        self.last_button_position: int = 2  # For button rotation in poker

        # Set size for collision detection
        self.set_size(40, 40)  # Slightly larger than fish

    def consume_energy(self) -> None:
        """Consume energy over time (jellyfish slowly dies)."""
        self.energy = max(0, self.energy - self.ENERGY_DECAY_RATE)

    def is_dead(self) -> bool:
        """Check if jellyfish should die (energy depleted)."""
        return self.energy <= 0

    def update(self, elapsed_time: int) -> None:
        """Update the jellyfish state."""
        super().update(elapsed_time)

        # Increment age
        self.age += 1

        # Decay energy
        self.consume_energy()

        # Update poker cooldown
        if self.poker_cooldown > 0:
            self.poker_cooldown -= 1

        # Gentle drifting movement (slow random walk)
        if self.age % 30 == 0:  # Change direction every second
            self.add_random_velocity_change([0.2, 0.6, 0.2], 20)  # Subtle movements
