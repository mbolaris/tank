"""Base simulator class containing shared simulation logic.

This module provides a base class for both graphical and headless simulators,
eliminating code duplication and ensuring consistent simulation behavior.
"""

import random
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING
from core.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    AUTO_FOOD_SPAWN_RATE,
    AUTO_FOOD_ENABLED,
    AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD,
    AUTO_FOOD_LOW_ENERGY_THRESHOLD,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
    AUTO_FOOD_HIGH_POP_THRESHOLD_1,
    AUTO_FOOD_HIGH_POP_THRESHOLD_2,
    COLLISION_QUERY_RADIUS,
    MATING_QUERY_RADIUS,
)
from core.algorithms import get_algorithm_index
from core.fish_poker import PokerInteraction

# Type checking imports
if TYPE_CHECKING:
    from core.entities import Agent, Fish, Food, Plant, Crab
    from core.ecosystem import EcosystemManager


class BaseSimulator(ABC):
    """Base class for simulation logic shared between graphical and headless modes.

    This class contains all the common simulation logic that was previously
    duplicated between FishTankSimulator and SimulationEngine.

    Attributes:
        frame_count: Total frames elapsed
        paused: Whether simulation is paused
        auto_food_timer: Timer for automatic food spawning
        ecosystem: Ecosystem manager for population tracking
    """

    def __init__(self) -> None:
        """Initialize base simulator state."""
        self.frame_count: int = 0
        self.paused: bool = False
        self.auto_food_timer: int = 0
        self.ecosystem: Optional["EcosystemManager"] = None
        self.environment: Optional["environment.Environment"] = None

    @abstractmethod
    def get_all_entities(self) -> List["Agent"]:
        """Get all entities in the simulation.

        Returns:
            List of all entities
        """
        pass

    @abstractmethod
    def add_entity(self, entity: "Agent") -> None:
        """Add an entity to the simulation.

        Args:
            entity: Entity to add
        """
        pass

    @abstractmethod
    def remove_entity(self, entity: "Agent") -> None:
        """Remove an entity from the simulation.

        Args:
            entity: Entity to remove
        """
        pass

    @abstractmethod
    def check_collision(self, e1: "Agent", e2: "Agent") -> bool:
        """Check if two entities collide.

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities collide
        """
        pass

    def record_fish_death(self, fish: "Fish", cause: Optional[str] = None) -> None:
        """Record a fish death in the ecosystem and remove it from the simulation.

        Args:
            fish: The fish that died
            cause: Optional death cause override (defaults to fish.get_death_cause())
        """
        if self.ecosystem is not None:
            algorithm_id = None
            if fish.genome.behavior_algorithm is not None:
                algorithm_id = get_algorithm_index(fish.genome.behavior_algorithm)

            death_cause = cause if cause is not None else fish.get_death_cause()
            self.ecosystem.record_death(
                fish.fish_id,
                fish.generation,
                fish.age,
                death_cause,
                fish.genome,
                algorithm_id=algorithm_id,
            )
        self.remove_entity(fish)

    def update_spatial_grid(self) -> None:
        """Update the spatial grid with current entity positions."""
        if self.environment is not None:
            self.environment.rebuild_spatial_grid()

    def handle_collisions(self) -> None:
        """Handle collisions between entities."""
        self.handle_fish_collisions()
        self.handle_food_collisions()

    def handle_fish_crab_collision(self, fish: "Agent", crab: "Agent") -> bool:
        """Handle collision between a fish and a crab (predator).

        Args:
            fish: The fish entity
            crab: The crab (predator) entity

        Returns:
            bool: True if the fish died from the collision, False otherwise
        """
        # Mark the predator encounter for death attribution
        fish.mark_predator_encounter()

        # Crab can only kill if hunt cooldown is ready
        if crab.can_hunt():
            crab.eat_fish(fish)
            self.record_fish_death(fish, "predation")
            return True
        return False

    def handle_fish_food_collision(self, fish: "Agent", food: "Agent") -> None:
        """Handle collision between a fish and food.

        Args:
            fish: The fish entity
            food: The food entity
        """
        fish.eat(food)
        food.get_eaten()
        self.remove_entity(food)

    def handle_fish_fish_collision(self, fish1: "Agent", fish2: "Agent") -> bool:
        """Handle collision between two fish (poker interaction).

        Args:
            fish1: The first fish entity
            fish2: The second fish entity

        Returns:
            bool: True if fish1 died from the collision, False otherwise
        """
        # Fish-to-fish poker interaction
        poker = PokerInteraction(fish1, fish2)
        if poker.play_poker():
            # Handle poker result (can be overridden by subclasses)
            self.handle_poker_result(poker)

            # Check if either fish died from poker
            fish1_died = False
            if fish1.is_dead() and fish1 in self.get_all_entities():
                self.record_fish_death(fish1)
                fish1_died = True

            if fish2.is_dead() and fish2 in self.get_all_entities():
                self.record_fish_death(fish2)

            return fish1_died
        return False

    def handle_fish_collisions(self) -> None:
        """Handle collisions involving fish.

        Uses spatial partitioning to reduce collision checks from O(n²) to O(n*k)
        where k is the number of nearby entities (typically much smaller than n).
        """
        from core.entities import Fish, Food, Crab

        # Get all fish entities
        all_entities = self.get_all_entities()
        fish_list = [e for e in all_entities if isinstance(e, Fish)]

        for fish in list(fish_list):
            # Check if fish is still in simulation (may have been removed)
            if fish not in self.get_all_entities():
                continue

            # Use spatial grid to get nearby entities (within collision range)
            # Typical fish size is ~30-50px, use generous radius for broad phase
            nearby_entities = []
            if self.environment is not None:
                nearby_entities = self.environment.nearby_agents(fish, radius=COLLISION_QUERY_RADIUS)
            else:
                # Fallback to checking all entities if no environment
                nearby_entities = [e for e in self.get_all_entities() if e != fish]

            for other in list(nearby_entities):
                if other == fish:
                    continue

                if self.check_collision(fish, other):
                    if isinstance(other, Crab):
                        if self.handle_fish_crab_collision(fish, other):
                            break  # Fish died, stop checking collisions for it
                    elif isinstance(other, Food):
                        # Check if food still exists (may have been eaten by another fish)
                        if other in self.get_all_entities():
                            self.handle_fish_food_collision(fish, other)
                    elif isinstance(other, Fish):
                        if self.handle_fish_fish_collision(fish, other):
                            break  # Fish died, stop checking collisions for it

    def handle_food_collisions(self) -> None:
        """Handle collisions involving food.

        Uses spatial partitioning to reduce collision checks from O(n²) to O(n*k).
        """
        from core.entities import Food, Fish, Crab

        all_entities = self.get_all_entities()
        food_list = [e for e in all_entities if isinstance(e, Food)]

        for food in list(food_list):
            # Check if food is still in simulation (may have been eaten)
            if food not in self.get_all_entities():
                continue

            # Use spatial grid for nearby entity lookup
            nearby_entities = []
            if self.environment is not None:
                nearby_entities = self.environment.nearby_agents(food, radius=COLLISION_QUERY_RADIUS)
            else:
                # Fallback to checking all entities if no environment
                nearby_entities = [e for e in self.get_all_entities() if e != food]

            for other in list(nearby_entities):
                if other == food:
                    continue

                if self.check_collision(food, other):
                    # Fish-food collisions are handled in handle_fish_collisions()
                    if isinstance(other, Crab):
                        other.eat_food(food)
                        food.get_eaten()
                        self.remove_entity(food)
                        break

    def handle_reproduction(self) -> None:
        """Handle fish reproduction by finding mates.

        Uses spatial queries to only check nearby fish for mating compatibility.
        """
        from core.entities import Fish

        fish_list = [e for e in self.get_all_entities() if isinstance(e, Fish)]

        # Try to mate fish that are ready
        for fish in fish_list:
            if not fish.can_reproduce():
                continue

            # Use spatial grid to find nearby fish (mating typically happens at close range)
            nearby_fish = []
            if self.environment is not None:
                nearby_fish = self.environment.nearby_agents_by_type(
                    fish, radius=MATING_QUERY_RADIUS, agent_class=Fish
                )
            else:
                # Fallback to checking all fish if no environment
                nearby_fish = [f for f in fish_list if f != fish]

            # Look for nearby compatible mates
            for potential_mate in nearby_fish:
                if potential_mate == fish:
                    continue

                # Attempt mating
                if fish.try_mate(potential_mate):
                    break  # Found a mate, stop looking

    def spawn_auto_food(self, environment: "environment.Environment") -> None:
        """Spawn automatic food if enabled.

        Dynamically adjusts spawn rate based on population size and total energy:
        - Faster spawning when fish are starving (total energy low)
        - Slower spawning when population or total energy is high

        Args:
            environment: Environment instance for creating food
        """
        if not AUTO_FOOD_ENABLED:
            return

        from core import entities

        # Calculate total energy and population
        all_entities = self.get_all_entities()
        fish_list = [e for e in all_entities if isinstance(e, entities.Fish)]
        fish_count = len(fish_list)
        total_energy = sum(fish.energy for fish in fish_list)

        # Dynamic spawn rate based on population and energy levels
        spawn_rate = AUTO_FOOD_SPAWN_RATE

        # Priority 1: Emergency feeding when energy is critically low
        if total_energy < AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD:
            # Critical starvation: Quadruple spawn rate (every 0.75 sec)
            spawn_rate = AUTO_FOOD_SPAWN_RATE // 4
        elif total_energy < AUTO_FOOD_LOW_ENERGY_THRESHOLD:
            # Low energy: Triple spawn rate (every 1 sec)
            spawn_rate = AUTO_FOOD_SPAWN_RATE // 3

        # Priority 2: Reduce feeding when energy or population is high
        elif (
            total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2
            or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_2
        ):
            # Very high energy/population: Slow down significantly (every 8 sec)
            spawn_rate = AUTO_FOOD_SPAWN_RATE * 3
        elif (
            total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1
            or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_1
        ):
            # High energy/population: Slow down moderately (every 5 sec)
            spawn_rate = int(AUTO_FOOD_SPAWN_RATE * 1.67)
        # else: use base rate (every 3 sec)

        self.auto_food_timer += 1
        if self.auto_food_timer >= spawn_rate:
            self.auto_food_timer = 0
            # Spawn food from the top at random x position
            x = random.randint(0, SCREEN_WIDTH)
            food = entities.Food(
                environment,
                x,
                0,
                source_plant=None,
                allow_stationary_types=False,
                screen_width=SCREEN_WIDTH,
                screen_height=SCREEN_HEIGHT,
            )
            # Ensure the food starts exactly at the top edge before falling
            food.pos.y = 0
            self.add_entity(food)

    def keep_entity_on_screen(
        self, entity: "Agent", screen_width: int = SCREEN_WIDTH, screen_height: int = SCREEN_HEIGHT
    ) -> None:
        """Keep an entity fully within the bounds of the screen.

        Args:
            entity: Entity to constrain
            screen_width: Screen width (default from constants)
            screen_height: Screen height (default from constants)
        """
        # Clamp horizontally
        if entity.pos.x < 0:
            entity.pos.x = 0
        elif entity.pos.x + entity.width > screen_width:
            entity.pos.x = screen_width - entity.width

        # Clamp vertically
        if entity.pos.y < 0:
            entity.pos.y = 0
        elif entity.pos.y + entity.height > screen_height:
            entity.pos.y = screen_height - entity.height

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle the result of a poker game.

        This method can be overridden by subclasses to add custom behavior
        (e.g., notifications in graphical mode, logging in headless mode).

        Args:
            poker: The poker interaction with result
        """
        # Default implementation does nothing
        # Subclasses can override to add notifications, logging, etc.
        pass

    def get_fish_list(self) -> List["Fish"]:
        """Get all fish entities in the simulation.

        Returns:
            List of all Fish entities
        """
        from core.entities import Fish

        return [e for e in self.get_all_entities() if isinstance(e, Fish)]

    def get_fish_count(self) -> int:
        """Get the count of fish in the simulation.

        Returns:
            Number of fish entities
        """
        return len(self.get_fish_list())
