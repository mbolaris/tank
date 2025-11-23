"""Base simulator class containing shared simulation logic.

This module provides a base class for both graphical and headless simulators,
eliminating code duplication and ensuring consistent simulation behavior.
"""

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

from core.algorithms import get_algorithm_index
from core.constants import (
    AUTO_FOOD_ENABLED,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
    AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
    AUTO_FOOD_HIGH_POP_THRESHOLD_1,
    AUTO_FOOD_HIGH_POP_THRESHOLD_2,
    AUTO_FOOD_LOW_ENERGY_THRESHOLD,
    AUTO_FOOD_SPAWN_RATE,
    AUTO_FOOD_ULTRA_LOW_ENERGY_THRESHOLD,
    COLLISION_QUERY_RADIUS,
    LIVE_FOOD_SPAWN_CHANCE,
    MATING_QUERY_RADIUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    POKER_ACTIVITY_ENABLED,
    FRACTAL_PLANT_POKER_COLLISION_DISTANCE,
)
from core.fish_poker import PokerInteraction
from core.jellyfish_poker import JellyfishPokerInteraction
from core.plant_poker import PlantPokerInteraction, check_fish_plant_poker_collision

# Type checking imports
if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.entities import Agent, Fish
    from core.environment import Environment


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
        self.ecosystem: Optional[EcosystemManager] = None
        self.environment: Optional[Environment] = None

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
        self.handle_fractal_plant_collisions()

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

        # Only remove food if it's fully consumed
        if food.is_fully_consumed():
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
        if POKER_ACTIVITY_ENABLED:
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

    def handle_fish_jellyfish_collision(self, fish: "Agent", jellyfish: "Agent") -> bool:
        """Handle collision between a fish and jellyfish (poker benchmark).

        Args:
            fish: The fish entity
            jellyfish: The jellyfish entity

        Returns:
            bool: True if fish died from the collision, False otherwise
        """
        # Fish-to-jellyfish poker interaction
        if POKER_ACTIVITY_ENABLED:
            poker = JellyfishPokerInteraction(fish, jellyfish)
            if poker.play_poker():
                # Add jellyfish poker event if available
                if (
                    hasattr(self, "add_jellyfish_poker_event")
                    and poker.result is not None
                    and poker.result.fish_hand is not None
                    and poker.result.jellyfish_hand is not None
                ):
                    self.add_jellyfish_poker_event(
                        fish_id=poker.result.fish_id,
                        fish_won=poker.result.fish_won,
                        fish_hand=poker.result.fish_hand.description,
                        jellyfish_hand=poker.result.jellyfish_hand.description,
                        energy_transferred=abs(poker.result.energy_transferred),
                    )
                # Check if fish died from poker
                if fish.is_dead() and fish in self.get_all_entities():
                    self.record_fish_death(fish)
                    return True
        return False

    def handle_fish_fractal_plant_collision(self, fish: "Agent", plant: "Agent") -> bool:
        """Handle collision between a fish and a fractal plant (poker interaction).

        Args:
            fish: The fish entity
            plant: The fractal plant entity

        Returns:
            bool: True if fish died from the collision, False otherwise
        """
        # Fish-to-plant poker interaction
        if POKER_ACTIVITY_ENABLED:
            poker = PlantPokerInteraction(fish, plant)
            if poker.play_poker():
                # Add plant poker event if available
                if (
                    hasattr(self, "add_plant_poker_event")
                    and poker.result is not None
                    and poker.result.fish_hand is not None
                    and poker.result.plant_hand is not None
                ):
                    self.add_plant_poker_event(
                        fish_id=poker.result.fish_id,
                        plant_id=poker.result.plant_id,
                        fish_won=poker.result.fish_won,
                        fish_hand=poker.result.fish_hand.description,
                        plant_hand=poker.result.plant_hand.description,
                        energy_transferred=abs(poker.result.energy_transferred),
                    )
                # Check if fish died from poker
                if fish.is_dead() and fish in self.get_all_entities():
                    self.record_fish_death(fish)
                    return True
        return False

    def handle_fractal_plant_collisions(self) -> None:
        """Handle collisions involving fractal plants.

        Fish can play poker against fractal plants to consume their energy.
        Uses spatial partitioning for efficient collision detection.
        """
        from core.entities import Fish
        from core.entities.fractal_plant import FractalPlant

        all_entities = self.get_all_entities()
        all_entities_set = set(all_entities)

        # Find all fractal plants
        plant_list = [e for e in all_entities if isinstance(e, FractalPlant)]

        if not plant_list:
            return

        # Find all fish
        fish_list = [e for e in all_entities if isinstance(e, Fish)]

        if not fish_list:
            return

        # Performance: Cache references
        environment = self.environment

        for plant in plant_list:
            if plant not in all_entities_set:
                continue

            if plant.is_dead():
                continue

            # Use spatial grid for nearby entity lookup
            # Use plant poker distance for query since we check poker collision below
            if environment is not None:
                nearby_entities = environment.nearby_agents(plant, radius=FRACTAL_PLANT_POKER_COLLISION_DISTANCE)
            else:
                nearby_entities = fish_list

            for fish in nearby_entities:
                if not isinstance(fish, Fish):
                    continue

                # Check if they're close enough for poker
                if check_fish_plant_poker_collision(fish, plant, FRACTAL_PLANT_POKER_COLLISION_DISTANCE):
                    # Try to play poker
                    self.handle_fish_fractal_plant_collision(fish, plant)

                    # Check if plant died from poker
                    if plant.is_dead():
                        plant.die()  # Release root spot
                        self.remove_entity(plant)
                        all_entities_set.discard(plant)
                        break

    def find_fish_groups_in_contact(self) -> List[List["Fish"]]:
        """Find groups of fish that are all in contact with each other.

        Uses a union-find approach to group fish that are within COLLISION_QUERY_RADIUS
        of each other. Returns groups where poker games should be played.

        Returns:
            List of fish groups, where each group is a list of Fish in contact
        """
        from core.entities import Fish

        # Get all fish entities
        all_entities = self.get_all_entities()
        fish_list = [e for e in all_entities if isinstance(e, Fish)]

        if len(fish_list) < 2:
            return []

        # Build adjacency list of fish that are in collision range
        fish_contacts = {fish: set() for fish in fish_list}

        for i, fish1 in enumerate(fish_list):
            # Use spatial grid to find nearby fish
            nearby_entities = []
            if self.environment is not None:
                nearby_entities = self.environment.nearby_agents(
                    fish1, radius=COLLISION_QUERY_RADIUS
                )
            else:
                nearby_entities = fish_list

            for fish2 in nearby_entities:
                if fish2 == fish1 or not isinstance(fish2, Fish):
                    continue

                # Check if they're actually in collision range
                if self.check_collision(fish1, fish2):
                    fish_contacts[fish1].add(fish2)
                    fish_contacts[fish2].add(fish1)

        # Find connected components using DFS
        visited = set()
        groups = []

        for fish in fish_list:
            if fish in visited:
                continue

            # Start a new group with DFS
            group = []
            stack = [fish]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue

                visited.add(current)
                group.append(current)

                # Add all connected fish to the stack
                for neighbor in fish_contacts[current]:
                    if neighbor not in visited:
                        stack.append(neighbor)

            # Only add groups with 2 or more fish
            if len(group) >= 2:
                groups.append(group)

        return groups

    def handle_fish_collisions(self) -> None:
        """Handle collisions involving fish.

        Uses spatial partitioning to reduce collision checks from O(n²) to O(n*k)
        where k is the number of nearby entities (typically much smaller than n).

        OPTIMIZATION: Merged poker group finding and general collision handling
        into a single pass to halve the number of spatial queries.

        Performance optimizations:
        - Pre-fetch type references outside loop
        - Use type() instead of isinstance() for common cases
        - Cache get_all_entities() result
        - Use set membership for removed_fish checks
        """
        from core.entities import Crab, Fish, Food, Jellyfish

        # Performance: Cache all_entities and avoid repeated calls
        all_entities = self.get_all_entities()
        all_entities_set = set(all_entities)  # O(1) membership test

        # Performance: Build fish list with type() check first (faster for exact match)
        fish_list = [e for e in all_entities if type(e) is Fish or isinstance(e, Fish)]

        if not fish_list:
            return

        # Data structures for poker groups
        fish_contacts = {fish: set() for fish in fish_list}

        # Track which fish have been removed (e.g. eaten) to avoid processing them further
        removed_fish: set = set()

        # Performance: Cache environment and check_collision references
        environment = self.environment
        check_collision = self.check_collision

        # Single pass over all fish
        for fish in fish_list:
            # Skip if fish was already removed in this frame
            if fish in removed_fish or fish not in all_entities_set:
                continue

            # Use spatial grid to get nearby entities (within collision range)
            if environment is not None:
                nearby_entities = environment.nearby_agents(fish, radius=COLLISION_QUERY_RADIUS)
            else:
                # Fallback to checking all entities if no environment
                nearby_entities = [e for e in all_entities if e is not fish]

            for other in nearby_entities:
                if other is fish:
                    continue

                # Skip if other entity was removed
                if other not in all_entities_set:
                    continue

                # Check collision
                if check_collision(fish, other):
                    # Performance: Use type() for exact match first
                    other_type = type(other)

                    if other_type is Fish:
                        # Record contact for poker group finding
                        fish_contacts[fish].add(other)

                    elif other_type is Crab or isinstance(other, Crab):
                        if self.handle_fish_crab_collision(fish, other):
                            removed_fish.add(fish)
                            all_entities_set.discard(fish)
                            break  # Fish died, stop checking collisions for it

                    elif other_type is Food or isinstance(other, Food):
                        self.handle_fish_food_collision(fish, other)

                    elif other_type is Jellyfish or isinstance(other, Jellyfish):
                        if self.handle_fish_jellyfish_collision(fish, other):
                            removed_fish.add(fish)
                            all_entities_set.discard(fish)
                            break  # Fish died, stop checking collisions for it

        # After processing all collisions, handle poker groups
        # Build full adjacency graph (make it symmetric)
        for fish, contacts in fish_contacts.items():
            for contact in contacts:
                if contact in fish_contacts:
                    fish_contacts[contact].add(fish)

        # Find connected components using DFS
        visited: set = set()
        processed_fish: set = set()  # For poker game tracking

        for fish in fish_list:
            if fish in visited or fish in removed_fish or fish not in all_entities_set:
                continue

            # Start a new group with DFS
            group = []
            stack = [fish]

            # Valid group members must be alive and in simulation
            while stack:
                current = stack.pop()
                if current in visited:
                    continue

                visited.add(current)
                if current not in removed_fish and current in all_entities_set:
                    group.append(current)

                # Add all connected fish to the stack
                contacts = fish_contacts.get(current)
                if contacts:
                    for neighbor in contacts:
                        if neighbor not in visited:
                            stack.append(neighbor)

            # Play poker if group has 2+ fish
            if len(group) >= 2:
                # Filter out fish that already played (just in case)
                valid_fish = [f for f in group if f not in processed_fish]

                if len(valid_fish) >= 2 and POKER_ACTIVITY_ENABLED:
                    # Only allow currently eligible fish to queue for poker.
                    # This lets groups of 3+ ready neighbors still play even if an
                    # exhausted or pregnant fish is touching them, which should
                    # increase multi-player games instead of skipping the whole
                    # contact cluster until everyone is ready again.
                    ready_fish = PokerInteraction.get_ready_players(valid_fish)

                    if len(ready_fish) < 2:
                        continue

                    # Build poker groups only from ready fish that are directly touching
                    ready_set = set(ready_fish)
                    ready_visited: set = set()

                    for start in ready_fish:
                        if start in ready_visited:
                            continue

                        stack = [start]
                        ready_group = []

                        while stack:
                            current = stack.pop()

                            if current in ready_visited:
                                continue

                            ready_visited.add(current)
                            ready_group.append(current)

                            for neighbor in fish_contacts.get(current, ()):  # type: ignore[arg-type]
                                if neighbor in ready_set and neighbor not in ready_visited:
                                    stack.append(neighbor)

                        if len(ready_group) < 2:
                            continue

                        poker = PokerInteraction(*ready_group)
                        if poker.play_poker():
                            self.handle_poker_result(poker)

                            # Check deaths
                            for f in ready_group:
                                if f.is_dead() and f in all_entities_set:
                                    self.record_fish_death(f)
                                    removed_fish.add(f)
                                    all_entities_set.discard(f)

                        processed_fish.update(ready_group)

    def handle_food_collisions(self) -> None:
        """Handle collisions involving food.

        Uses spatial partitioning to reduce collision checks from O(n²) to O(n*k).

        Performance optimizations:
        - Use set for entity membership tracking
        - Cache method references
        """
        from core.entities import Crab, Food

        all_entities = self.get_all_entities()
        all_entities_set = set(all_entities)

        # Performance: Use type() check first
        food_list = [e for e in all_entities if type(e) is Food or isinstance(e, Food)]

        if not food_list:
            return

        # Performance: Cache references
        environment = self.environment
        check_collision = self.check_collision

        for food in food_list:
            # Check if food is still in simulation (may have been eaten)
            if food not in all_entities_set:
                continue

            # Use spatial grid for nearby entity lookup
            if environment is not None:
                nearby_entities = environment.nearby_agents(food, radius=COLLISION_QUERY_RADIUS)
            else:
                # Fallback to checking all entities if no environment
                nearby_entities = [e for e in all_entities if e is not food]

            for other in nearby_entities:
                if other is food:
                    continue

                if check_collision(food, other):
                    # Fish-food collisions are handled in handle_fish_collisions()
                    if type(other) is Crab or isinstance(other, Crab):
                        other.eat_food(food)
                        food.get_eaten()
                        self.remove_entity(food)
                        all_entities_set.discard(food)
                        break

    def handle_reproduction(self) -> None:
        """Handle fish reproduction by finding mates.

        Uses spatial queries to only check nearby fish for mating compatibility.

        Performance optimizations:
        - Cache method references
        - Early termination on successful mating
        """
        from core.entities import Fish

        all_entities = self.get_all_entities()

        # Performance: Use type() check first
        fish_list = [e for e in all_entities if type(e) is Fish or isinstance(e, Fish)]

        if len(fish_list) < 2:
            return  # Need at least 2 fish for reproduction

        # Performance: Cache environment reference
        environment = self.environment

        # Try to mate fish that are ready
        for fish in fish_list:
            if not fish.can_reproduce():
                continue

            # Use spatial grid to find nearby fish (mating typically happens at close range)
            if environment is not None:
                nearby_fish = environment.nearby_agents_by_type(
                    fish, radius=MATING_QUERY_RADIUS, agent_class=Fish
                )
            else:
                # Fallback to checking all fish if no environment
                nearby_fish = [f for f in fish_list if f is not fish]

            # Look for nearby compatible mates
            for potential_mate in nearby_fish:
                if potential_mate is fish:
                    continue

                # Attempt mating
                if fish.try_mate(potential_mate):
                    break  # Found a mate, stop looking

    def spawn_auto_food(self, environment: "Environment") -> None:
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
            live_food_roll = random.random()
            if live_food_roll < LIVE_FOOD_SPAWN_CHANCE:
                food_x = random.randint(0, SCREEN_WIDTH)
                food_y = random.randint(0, SCREEN_HEIGHT)
                food = entities.LiveFood(
                    environment,
                    food_x,
                    food_y,
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT,
                )
            else:
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
