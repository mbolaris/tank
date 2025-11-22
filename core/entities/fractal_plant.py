"""Fractal plant entity with evolving L-system genetics.

This module implements fractal plants that grow from root spots,
collect energy passively, produce nectar for reproduction, and
can play poker against fish.
"""

import random
from typing import TYPE_CHECKING, Optional

from core.entities.base import Agent
from core.plant_genetics import PlantGenome

if TYPE_CHECKING:
    from core.environment import Environment
    from core.root_spots import RootSpot


# Plant lifecycle constants (can be moved to constants.py later)
from core.constants import (
    FRACTAL_PLANT_BASE_HEIGHT,
    FRACTAL_PLANT_BASE_WIDTH,
    FRACTAL_PLANT_DEATH_ENERGY,
    FRACTAL_PLANT_INITIAL_ENERGY,
    FRACTAL_PLANT_MAX_ENERGY,
    FRACTAL_PLANT_MAX_SIZE,
    FRACTAL_PLANT_MIN_POKER_ENERGY,
    FRACTAL_PLANT_MIN_SIZE,
    FRACTAL_PLANT_NECTAR_COOLDOWN,
    FRACTAL_PLANT_POKER_COOLDOWN,
)


class FractalPlant(Agent):
    """A fractal plant entity with evolving L-system genetics.

    Fractal plants:
    - Grow from fixed root spots at the tank bottom
    - Collect energy passively (more energy = bigger = more collection)
    - Produce nectar when large enough (triggers reproduction)
    - Can play poker against fish (fish can eat the plant's energy)
    - Have genetically inherited fractal shapes that evolve

    Attributes:
        plant_id: Unique identifier
        genome: PlantGenome with L-system parameters and traits
        energy: Current energy level (determines size)
        max_energy: Maximum energy capacity
        root_spot: The RootSpot this plant is anchored to
        poker_cooldown: Frames until can play poker again
        nectar_cooldown: Frames until can produce nectar again
        age: Frames since sprouting
        nectar_produced: Count of nectar produced
        poker_wins: Count of poker games won
        poker_losses: Count of poker games lost
    """

    # Class-level ID counter
    _next_id = 0

    def __init__(
        self,
        environment: "Environment",
        genome: PlantGenome,
        root_spot: "RootSpot",
        initial_energy: float = FRACTAL_PLANT_INITIAL_ENERGY,
        screen_width: int = 800,
        screen_height: int = 600,
    ) -> None:
        """Initialize a fractal plant.

        Args:
            environment: The environment the plant lives in
            genome: The plant's genetic information
            root_spot: The root spot this plant grows from
            initial_energy: Starting energy level
            screen_width: Width of simulation area
            screen_height: Height of simulation area
        """
        # Initialize at the root spot position
        super().__init__(
            environment,
            root_spot.x,
            root_spot.y,
            0,  # Plants don't move
            screen_width,
            screen_height,
        )

        # Assign unique ID
        self.plant_id = FractalPlant._next_id
        FractalPlant._next_id += 1

        # Core attributes
        self.genome = genome
        self.root_spot = root_spot
        self.energy = initial_energy
        self.max_energy = FRACTAL_PLANT_MAX_ENERGY * genome.growth_efficiency

        # Cooldowns
        self.poker_cooldown = 0
        self.nectar_cooldown = FRACTAL_PLANT_NECTAR_COOLDOWN // 2  # Start partially ready

        # Statistics
        self.age = 0
        self.nectar_produced = 0
        self.poker_wins = 0
        self.poker_losses = 0

        # Poker state
        self.last_button_position = 2

        # Rendering stability
        self._cached_iterations = 1  # Cache iterations to prevent flickering

        # Update size based on initial energy
        self._update_size()

    def _update_size(self) -> None:
        """Update plant size based on current energy."""
        # Size scales with energy
        energy_ratio = self.energy / self.max_energy
        size_multiplier = FRACTAL_PLANT_MIN_SIZE + (
            (FRACTAL_PLANT_MAX_SIZE - FRACTAL_PLANT_MIN_SIZE) * energy_ratio
        )

        self.set_size(
            FRACTAL_PLANT_BASE_WIDTH * size_multiplier,
            FRACTAL_PLANT_BASE_HEIGHT * size_multiplier,
        )
        
        # Anchor bottom of plant to root spot
        self.pos.y = self.root_spot.y - self.height
        self.rect.y = self.pos.y

    def update_position(self) -> None:
        """Plants are stationary - don't update position."""
        pass

    def update(
        self,
        elapsed_time: int,
        time_modifier: float = 1.0,
        time_of_day: Optional[float] = None,
    ) -> Optional["PlantNectar"]:
        """Update the plant state.

        Args:
            elapsed_time: Time elapsed since start
            time_modifier: Time-based modifier (day/night effects)
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            PlantNectar if produced, None otherwise
        """
        super().update(elapsed_time)

        self.age += 1

        # Update cooldowns
        if self.poker_cooldown > 0:
            self.poker_cooldown -= 1
        if self.nectar_cooldown > 0:
            self.nectar_cooldown -= 1

        # Passive energy collection (compound growth)
        self._collect_energy(time_modifier)

        # Update size based on new energy
        self._update_size()

        # Update fitness
        self.genome.update_fitness(
            energy_gained=self.genome.base_energy_rate,
            survived_frames=1,
        )

        # Check if can produce nectar
        nectar = self._try_produce_nectar(time_of_day)

        return nectar

    def _collect_energy(self, time_modifier: float = 1.0) -> None:
        """Collect passive energy.

        Energy collection rate increases with current energy (compound growth).

        Args:
            time_modifier: Modifier based on time of day
        """
        # Base rate from genome
        base_rate = self.genome.base_energy_rate

        # Compound growth factor: more energy = faster collection
        # Uses sqrt to prevent runaway growth
        growth_factor = 1.0 + (self.energy / self.max_energy) ** 0.5 * 0.5

        # Time of day affects photosynthesis
        # Day = 1.0, Dawn/Dusk = 0.7, Night = 0.3
        energy_gain = base_rate * growth_factor * time_modifier

        self.energy = min(self.max_energy, self.energy + energy_gain)

    def _try_produce_nectar(self, time_of_day: Optional[float]) -> Optional["PlantNectar"]:
        """Try to produce nectar if conditions are met.

        Args:
            time_of_day: Normalized time of day

        Returns:
            PlantNectar if produced, None otherwise
        """
        # Check if plant is large enough
        energy_ratio = self.energy / self.max_energy
        if energy_ratio < self.genome.nectar_threshold_ratio:
            return None

        # Check cooldown
        if self.nectar_cooldown > 0:
            return None

        # Produce nectar
        self.nectar_cooldown = FRACTAL_PLANT_NECTAR_COOLDOWN
        self.nectar_produced += 1
        self.genome.update_fitness(nectar_produced=1)

        # Nectar spawns at top of plant
        nectar_x = self.pos.x + self.width / 2
        nectar_y = self.pos.y - self.height

        # Import here to avoid circular imports
        from core.entities.fractal_plant import PlantNectar

        return PlantNectar(
            environment=self.environment,
            x=nectar_x,
            y=nectar_y,
            source_plant=self,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
        )

    def can_play_poker(self) -> bool:
        """Check if plant can play poker.

        Returns:
            True if poker game can proceed
        """
        if self.is_dead():
            return False
        if self.energy < FRACTAL_PLANT_MIN_POKER_ENERGY:
            return False
        if self.poker_cooldown > 0:
            return False
        return True

    def lose_energy(self, amount: float) -> float:
        """Lose energy (from poker loss or being eaten).

        Args:
            amount: Energy to lose

        Returns:
            Actual amount lost
        """
        actual_loss = min(self.energy, amount)
        self.energy -= actual_loss
        self._update_size()
        return actual_loss

    def gain_energy(self, amount: float) -> float:
        """Gain energy (from poker win).

        Args:
            amount: Energy to gain

        Returns:
            Actual amount gained
        """
        actual_gain = min(self.max_energy - self.energy, amount)
        self.energy += actual_gain
        self._update_size()
        return actual_gain

    def is_dead(self) -> bool:
        """Check if plant is dead (energy too low).

        Returns:
            True if plant should be removed
        """
        return self.energy < FRACTAL_PLANT_DEATH_ENERGY

    def get_size_multiplier(self) -> float:
        """Get current size multiplier for rendering.

        Returns:
            Size multiplier (0.3 to 1.5)
        """
        energy_ratio = self.energy / self.max_energy
        return FRACTAL_PLANT_MIN_SIZE + (
            (FRACTAL_PLANT_MAX_SIZE - FRACTAL_PLANT_MIN_SIZE) * energy_ratio
        )

    def get_fractal_iterations(self) -> int:
        """Get number of L-system iterations based on size.

        Larger plants have more detailed fractals.

        Returns:
            Number of iterations (1-3)
        """
        size = self.get_size_multiplier()
        
        # Use hysteresis to prevent flickering between iteration levels
        # Only upgrade when well past the threshold, downgrade when well below
        
        target_iterations = 1
        if size >= 1.0:
            target_iterations = 3
        elif size >= 0.6:
            target_iterations = 2
            
        # Apply hysteresis
        if target_iterations > self._cached_iterations:
            # Upgrade requires being 10% past the threshold to prevent rapid switching
            if (target_iterations == 2 and size > 0.65) or (target_iterations == 3 and size > 1.05):
                self._cached_iterations = target_iterations
        elif target_iterations < self._cached_iterations:
            # Downgrade is immediate to reflect energy loss, but we respect the thresholds
            self._cached_iterations = target_iterations
            
        return self._cached_iterations

    def get_poker_aggression(self) -> float:
        """Get poker aggression level.

        Returns:
            Aggression value for poker decisions (0.0-1.0)
        """
        return self.genome.aggression

    def die(self) -> None:
        """Handle plant death - release root spot."""
        if self.root_spot is not None:
            self.root_spot.release()

    def to_state_dict(self) -> dict:
        """Serialize plant state for frontend rendering.

        Returns:
            Dictionary with plant state
        """
        return {
            "type": "fractal_plant",
            "id": self.plant_id,
            "x": self.pos.x,
            "y": self.pos.y,
            "width": self.width,
            "height": self.height,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "size_multiplier": self.get_size_multiplier(),
            "iterations": self.get_fractal_iterations(),
            "genome": self.genome.to_dict(),
            "age": self.age,
            "nectar_ready": self.nectar_cooldown == 0 and (
                self.energy / self.max_energy >= self.genome.nectar_threshold_ratio
            ),
        }


from core.entities.resources import Food

class PlantNectar(Food):
    """Nectar produced by fractal plants.

    When consumed by fish, triggers plant reproduction at a nearby root spot.

    Attributes:
        source_plant: The plant that produced this nectar
        parent_genome: Copy of parent plant's genome for inheritance
        energy: Energy value when consumed
    """

    NECTAR_ENERGY = 50.0
    NECTAR_SIZE = 15

    def __init__(
        self,
        environment: "Environment",
        x: float,
        y: float,
        source_plant: FractalPlant,
        screen_width: int = 800,
        screen_height: int = 600,
    ) -> None:
        """Initialize plant nectar.

        Args:
            environment: The environment
            x: X position
            y: Y position
            source_plant: The plant that produced this
            screen_width: Screen width
            screen_height: Screen height
        """
        super().__init__(
            environment,
            x,
            y,
            source_plant=source_plant,
            food_type="nectar",
            allow_stationary_types=True,
            screen_width=screen_width,
            screen_height=screen_height,
        )

        self.source_plant = source_plant
        self.parent_genome = source_plant.genome  # Reference to parent genome
        # Override energy from Food init (which uses default 90.0 from constants)
        self.energy = self.NECTAR_ENERGY
        self.max_energy = self.NECTAR_ENERGY

        self.set_size(self.NECTAR_SIZE, self.NECTAR_SIZE)

    def update_position(self) -> None:
        """Nectar stays attached to its source plant."""
        if self.source_plant is not None and not self.source_plant.is_dead():
            # Stay at top of plant
            self.pos.x = self.source_plant.pos.x + self.source_plant.width / 2 - self.width / 2
            self.pos.y = self.source_plant.pos.y - self.source_plant.height - self.height

    def update(self, elapsed_time: int) -> None:
        """Update nectar state."""
        super().update(elapsed_time)
        self.update_position()

    def get_energy_value(self) -> float:
        """Get energy provided when consumed.

        Returns:
            Energy value
        """
        return self.energy

    def is_consumed(self) -> bool:
        """Check if nectar has been consumed.

        Returns:
            True if fully consumed
        """
        return self.energy <= 0

    def take_bite(self, bite_size: float) -> float:
        """Take a bite from the nectar.

        Overrides Food.take_bite to trigger reproduction logic when fully consumed.
        """
        consumed = super().take_bite(bite_size)
        
        # If fully consumed (or close enough), trigger reproduction logic
        if self.energy <= 0.1:
            self.energy = 0
            # Logic for reproduction is handled by the consumer (Fish)
            # But we need to ensure the consumer knows this is special nectar
            pass
            
        return consumed

    def consume(self) -> "PlantGenome":
        """Consume this nectar.

        Returns:
            The parent genome for reproduction
        """
        self.energy = 0
        return self.parent_genome

    def to_state_dict(self) -> dict:
        """Serialize for frontend.

        Returns:
            State dictionary
        """
        return {
            "type": "plant_nectar",
            "x": self.pos.x,
            "y": self.pos.y,
            "width": self.width,
            "height": self.height,
            "energy": self.energy,
            "source_plant_id": self.source_plant.plant_id if self.source_plant else None,
        }
