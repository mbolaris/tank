"""Base simulator class containing shared simulation logic.

This module provides a base class for both graphical and headless simulators,
eliminating code duplication and ensuring consistent simulation behavior.
"""

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Union

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
    FISH_POKER_MAX_DISTANCE,
    FISH_POKER_MIN_DISTANCE,
    FRACTAL_PLANT_POKER_MAX_DISTANCE,
    FRACTAL_PLANT_POKER_MIN_DISTANCE,
    LIVE_FOOD_SPAWN_CHANCE,
    MATING_QUERY_RADIUS,
    POKER_ACTIVITY_ENABLED,
    POKER_MAX_PLAYERS,
    POKER_PROXIMITY_QUERY_RADIUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.fish_poker import PokerInteraction
from core.mixed_poker import MixedPokerInteraction, check_poker_proximity
from core.plant_poker import PlantPokerInteraction, check_fish_plant_poker_proximity

# Type checking imports
if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.entities import Agent, Fish
    from core.entities.fractal_plant import FractalPlant
    from core.environment import Environment

# Type alias for poker-eligible entities
PokerPlayer = Union["Fish", "FractalPlant"]

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
        # OPTIMIZATION: Throttle poker games to run every N frames when population is high
        self._poker_throttle_counter: int = 0

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

    def check_poker_proximity(
        self, entity1: "Agent", entity2: "Agent", 
        min_distance: float = FISH_POKER_MIN_DISTANCE,
        max_distance: float = FISH_POKER_MAX_DISTANCE
    ) -> bool:
        """Check if two entities are in poker proximity (close but not touching).

        Poker triggers when entities are near each other but not overlapping.
        Works for any combination of fish and plants.

        Args:
            entity1: First entity
            entity2: Second entity
            min_distance: Minimum center-to-center distance
            max_distance: Maximum center-to-center distance

        Returns:
            True if entities are in the poker proximity zone
        """
        # Calculate centers
        e1_cx = entity1.pos.x + entity1.width / 2
        e1_cy = entity1.pos.y + entity1.height / 2
        e2_cx = entity2.pos.x + entity2.width / 2
        e2_cy = entity2.pos.y + entity2.height / 2

        dx = e1_cx - e2_cx
        dy = e1_cy - e2_cy
        distance_sq = dx * dx + dy * dy

        min_dist_sq = min_distance * min_distance
        max_dist_sq = max_distance * max_distance

        # Must be within max distance but farther than min distance (not touching)
        return min_dist_sq < distance_sq <= max_dist_sq

    def check_fish_poker_proximity(self, fish1: "Agent", fish2: "Agent") -> bool:
        """Check if two fish are in poker proximity (close but not touching).

        Legacy method - calls check_poker_proximity with fish defaults.
        """
        return self.check_poker_proximity(
            fish1, fish2, FISH_POKER_MIN_DISTANCE, FISH_POKER_MAX_DISTANCE
        )

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
        """Handle collisions between entities.
        
        OPTIMIZATION: Throttle expensive poker games based on population size.
        - Under 100 entities: every frame
        - 100-200 entities: every 2 frames  
        - 200+ entities: every 3 frames
        """
        self.handle_fish_collisions()
        self.handle_food_collisions()
        
        # OPTIMIZATION: Throttle poker games at high populations
        entity_count = len(self.get_all_entities())
        throttle_interval = 1  # Default: every frame
        if entity_count >= 200:
            throttle_interval = 3
        elif entity_count >= 100:
            throttle_interval = 2
            
        self._poker_throttle_counter += 1
        if self._poker_throttle_counter >= throttle_interval:
            self._poker_throttle_counter = 0
            # Mixed poker handles both fish-plant and plant-plant interactions
            self.handle_mixed_poker_games()

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
            # Add buffer for entity sizes since query uses position but proximity uses center
            search_radius = FRACTAL_PLANT_POKER_MAX_DISTANCE + max(plant.width, plant.height) / 2
            if environment is not None:
                # Optimize: Only look for fish
                if hasattr(environment, "nearby_fish"):
                    nearby_entities = environment.nearby_fish(plant, radius=search_radius)
                else:
                    nearby_entities = environment.nearby_agents_by_type(plant, radius=search_radius, agent_class=Fish)
            else:
                nearby_entities = fish_list

            for fish in nearby_entities:
                if not isinstance(fish, Fish):
                    continue

                # Check if fish is in poker proximity zone (close but not touching)
                if check_fish_plant_poker_proximity(
                    fish, plant, 
                    min_distance=FRACTAL_PLANT_POKER_MIN_DISTANCE, 
                    max_distance=FRACTAL_PLANT_POKER_MAX_DISTANCE
                ):
                    # Try to play poker
                    self.handle_fish_fractal_plant_collision(fish, plant)

                    # Check if plant died from poker
                    if plant.is_dead():
                        plant.die()  # Release root spot
                        self.remove_entity(plant)
                        all_entities_set.discard(plant)
                        break

    def handle_mixed_poker_games(self) -> None:
        """Handle poker games between any mix of fish and plants.
        
        Finds groups of fish and plants that are in poker proximity
        and initiates mixed poker games with up to POKER_MAX_PLAYERS players.
        
        PERFORMANCE OPTIMIZATIONS:
        - Single combined spatial query instead of separate fish+plant queries
        - Inline proximity check to avoid method call overhead
        - Pre-compute squared distances to avoid sqrt
        - Use local variables for frequently accessed attributes
        - Cache entity positions to avoid repeated attribute access
        - Skip spatial query for entities with no nearby_poker_entities method
        """
        from core.entities import Fish
        from core.entities.fractal_plant import FractalPlant

        if not POKER_ACTIVITY_ENABLED:
            return

        all_entities = self.get_all_entities()
        
        # Early exit if not enough entities
        if len(all_entities) < 2:
            return

        all_entities_set = set(all_entities)
        
        # Performance: Use type() for exact match (faster than isinstance)
        fish_list = [e for e in all_entities if type(e) is Fish]
        
        # For plants, we need isinstance since we also check is_dead
        plant_list = [e for e in all_entities if isinstance(e, FractalPlant) and not e.is_dead()]

        # Need at least 1 fish and 1 other entity for poker
        n_fish = len(fish_list)
        n_plants = len(plant_list)
        if n_fish < 1 or (n_fish + n_plants) < 2:
            return

        # Combine into one list for proximity checking
        all_poker_entities: List[PokerPlayer] = fish_list + plant_list  # type: ignore
        n_entities = len(all_poker_entities)

        # Pre-compute squared proximity values
        proximity_max = max(FISH_POKER_MAX_DISTANCE, FRACTAL_PLANT_POKER_MAX_DISTANCE)
        proximity_min = min(FISH_POKER_MIN_DISTANCE, FRACTAL_PLANT_POKER_MIN_DISTANCE)
        proximity_max_sq = proximity_max * proximity_max
        proximity_min_sq = proximity_min * proximity_min
        
        # Cache entity center positions for fast access
        # Store as (center_x, center_y) tuples
        entity_centers = {}
        for e in all_poker_entities:
            entity_centers[e] = (e.pos.x + e.width * 0.5, e.pos.y + e.height * 0.5)

        # Build adjacency graph for entities in poker proximity
        entity_contacts: Dict[PokerPlayer, Set[PokerPlayer]] = {e: set() for e in all_poker_entities}

        environment = self.environment
        poker_entity_set = set(all_poker_entities)

        for entity in all_poker_entities:
            if entity not in all_entities_set:
                continue

            e1_cx, e1_cy = entity_centers[entity]

            # Get nearby entities - OPTIMIZATION: Single combined query
            search_radius = proximity_max + max(entity.width, entity.height) * 0.5
            nearby: List[PokerPlayer] = []
            
            if environment is not None:
                # OPTIMIZATION: Use nearby_poker_entities if available, else combined query
                if hasattr(environment, "nearby_poker_entities"):
                    nearby = environment.nearby_poker_entities(entity, radius=search_radius)
                else:
                    # Get nearby fish and plants in single pass through nearby_agents
                    if hasattr(environment, "nearby_agents"):
                        nearby_all = environment.nearby_agents(entity, radius=search_radius)
                        nearby = [e for e in nearby_all if e in poker_entity_set]
                    else:
                        # Fallback to separate queries
                        if hasattr(environment, "nearby_fish"):
                            nearby.extend(environment.nearby_fish(entity, radius=search_radius))
                        if hasattr(environment, "nearby_agents_by_type"):
                            nearby_plants = environment.nearby_agents_by_type(entity, radius=search_radius, agent_class=FractalPlant)
                            for plant in nearby_plants:
                                if plant not in nearby:
                                    nearby.append(plant)
            else:
                nearby = [e for e in all_poker_entities if e is not entity]

            for other in nearby:
                if other is entity:
                    continue
                if other not in all_entities_set:
                    continue
                # Skip if already connected (avoid redundant checks)
                entity_contact_set = entity_contacts[entity]
                if other in entity_contact_set:
                    continue

                # OPTIMIZATION: Direct dict access (we know all poker entities are in the dict)
                e2_cx, e2_cy = entity_centers[other]
                dx = e1_cx - e2_cx
                dy = e1_cy - e2_cy
                distance_sq = dx * dx + dy * dy

                # Must be within max distance but farther than min distance
                if proximity_min_sq < distance_sq <= proximity_max_sq:
                    entity_contact_set.add(other)
                    entity_contacts[other].add(entity)

        # Find connected components using DFS
        visited: Set[PokerPlayer] = set()
        processed: Set[PokerPlayer] = set()
        removed_entities: Set[PokerPlayer] = set()

        for start_entity in all_poker_entities:
            if start_entity in visited or start_entity in removed_entities:
                continue
            if start_entity not in all_entities_set:
                continue

            # Build connected group via DFS
            group: List[PokerPlayer] = []
            stack = [start_entity]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue

                visited.add(current)
                if current not in removed_entities and current in all_entities_set:
                    group.append(current)

                # Direct access - all poker entities are in the dict
                for neighbor in entity_contacts[current]:
                    if neighbor not in visited:
                        stack.append(neighbor)

            # Need at least 2 players for poker
            if len(group) < 2:
                continue

            # Filter to only unprocessed entities
            valid_players = [p for p in group if p not in processed]
            if len(valid_players) < 2:
                continue

            # Filter to only ready players (not on cooldown, not pregnant, etc.)
            ready_players = self._get_ready_poker_players(valid_players)
            if len(ready_players) < 2:
                continue

            # IMPORTANT: Ensure ALL players in the group are within max distance of each other
            # The DFS can connect A-B-C where A and C are far apart (chain connection)
            # We need to filter to only players that are ALL mutually within proximity
            ready_players = self._filter_mutually_proximate_players(
                ready_players, proximity_max
            )
            if len(ready_players) < 2:
                continue

            # IMPORTANT: Require at least 1 fish in the game
            # Plant-only poker games are not allowed
            fish_in_group = [p for p in ready_players if isinstance(p, Fish)]
            if len(fish_in_group) < 1:
                continue

            # Limit to max players
            if len(ready_players) > POKER_MAX_PLAYERS:
                ready_players = ready_players[:POKER_MAX_PLAYERS]

            # Play mixed poker game
            try:
                poker = MixedPokerInteraction(ready_players)
                if poker.play_poker():
                    self._handle_mixed_poker_result(poker)

                    # Check for deaths
                    for player in ready_players:
                        if isinstance(player, Fish) and player.is_dead():
                            if player in all_entities_set:
                                self.record_fish_death(player)
                                removed_entities.add(player)
                                all_entities_set.discard(player)
                        elif isinstance(player, FractalPlant) and player.is_dead():
                            if player in all_entities_set:
                                player.die()
                                self.remove_entity(player)
                                removed_entities.add(player)
                                all_entities_set.discard(player)

                processed.update(ready_players)

            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Mixed poker game error: {e}", exc_info=True)

    def _filter_mutually_proximate_players(
        self, players: List[PokerPlayer], max_distance: float
    ) -> List[PokerPlayer]:
        """Filter players to only those where ALL are within max_distance of each other.
        
        This prevents chain-connected players (A near B, B near C, but A far from C)
        from ending up in the same poker game.
        
        PERFORMANCE OPTIMIZATIONS:
        - Use squared distances throughout (avoid sqrt)
        - Use 2D list instead of dict (no hash/get overhead)
        - Pre-cache player positions
        - Early exit when best possible group is found
        - Inline distance calculations
        
        Args:
            players: List of potential players
            max_distance: Maximum distance between any two players
            
        Returns:
            Largest subset where all players are mutually within max_distance
        """
        n = len(players)
        if n <= 2:
            # For 2 players, they were already verified as proximate
            return players
        
        # Pre-compute squared max distance (avoid sqrt entirely)
        max_dist_sq = max_distance * max_distance
        
        # Pre-cache player positions for faster access
        positions = [(p.pos.x + p.width / 2, p.pos.y + p.height / 2) for p in players]
        
        # OPTIMIZATION: Use 2D list instead of dict for O(1) access without hash overhead
        # Build adjacency matrix as boolean: True = within distance
        # Only upper triangle needed (i < j)
        adjacent = [[False] * n for _ in range(n)]
        
        for i in range(n):
            x1, y1 = positions[i]
            for j in range(i + 1, n):
                x2, y2 = positions[j]
                dx = x1 - x2
                dy = y1 - y2
                if dx * dx + dy * dy <= max_dist_sq:
                    adjacent[i][j] = True
                    adjacent[j][i] = True  # Symmetric
        
        # Simple greedy approach: start with each player, build largest valid group
        best_group: List[int] = []
        best_size = 0
        
        for start_idx in range(n):
            # Early exit: can't beat current best if remaining players aren't enough
            if n - start_idx <= best_size:
                break
                
            group = [start_idx]
            adj_row = adjacent[start_idx]  # Cache row for start player
            
            for candidate_idx in range(start_idx + 1, n):
                # Quick check: must be adjacent to start player
                if not adj_row[candidate_idx]:
                    continue
                    
                # Check if candidate is within distance of ALL current group members
                can_add = True
                for member_idx in group:
                    if not adjacent[member_idx][candidate_idx]:
                        can_add = False
                        break
                if can_add:
                    group.append(candidate_idx)
            
            if len(group) > best_size:
                best_group = group
                best_size = len(group)
                # Early exit if we found a group with all remaining players
                if best_size == n - start_idx:
                    break
        
        return [players[i] for i in best_group]

    def _get_ready_poker_players(self, players: List[PokerPlayer]) -> List[PokerPlayer]:
        """Filter players to those ready to play poker.

        Args:
            players: List of potential players (fish and plants)

        Returns:
            List of players ready to play (not on cooldown, not pregnant, etc.)
        """
        from core.entities import Fish
        from core.entities.fractal_plant import FractalPlant

        ready = []
        for player in players:
            # Check cooldown
            if getattr(player, "poker_cooldown", 0) > 0:
                continue

            # Fish-specific checks
            if isinstance(player, Fish):
                if hasattr(player, "is_pregnant") and player.is_pregnant:
                    continue
                if player.energy < MixedPokerInteraction.MIN_ENERGY_TO_PLAY:
                    continue

            # Plant-specific checks
            if isinstance(player, FractalPlant):
                if player.is_dead():
                    continue

            ready.append(player)

        return ready

    def _handle_mixed_poker_result(self, poker: MixedPokerInteraction) -> None:
        """Handle the result of a mixed poker game.

        Args:
            poker: The completed poker interaction
        """
        if poker.result is None:
            return

        result = poker.result

        # Add poker event for display
        if hasattr(self, "add_plant_poker_event") and result.plant_count > 0:
            # Use plant poker event format for games with plants
            winner_is_fish = result.winner_type == "fish"
            
            # Safely get hand descriptions (hands can be None if player folded)
            winner_hand_desc = "Unknown"
            if result.winner_hand is not None:
                winner_hand_desc = result.winner_hand.description
            
            loser_hand_desc = "Folded"
            if result.loser_hands and result.loser_hands[0] is not None:
                loser_hand_desc = result.loser_hands[0].description
            
            self.add_plant_poker_event(
                fish_id=result.winner_id if winner_is_fish else (result.loser_ids[0] if result.loser_ids else 0),
                plant_id=result.winner_id if not winner_is_fish else 0,
                fish_won=winner_is_fish,
                fish_hand=winner_hand_desc,
                plant_hand=loser_hand_desc,
                energy_transferred=abs(result.energy_transferred),
            )

        # Record plant-fish energy transfer stats
        if self.ecosystem is not None and result.plant_count > 0:
            # Calculate net energy flow to fish in this mixed game
            # Positive = fish gained from plants, negative = plants gained from fish
            if result.winner_type == "fish":
                # Fish won - energy flowed from plants to fish
                energy_to_fish = abs(result.energy_transferred)
            else:
                # Plant won - energy flowed from fish to plants
                energy_to_fish = -abs(result.energy_transferred)
            
            self.ecosystem.record_mixed_poker_energy_transfer(
                energy_to_fish=energy_to_fish,
                is_plant_game=True,
            )

    def find_fish_groups_in_contact(self) -> List[List["Fish"]]:
        """Find groups of fish that are in poker proximity (close but not touching).

        Uses a union-find approach to group fish that are within poker proximity
        of each other. Returns groups where poker games should be played.

        Returns:
            List of fish groups, where each group is a list of Fish in proximity
        """
        from core.entities import Fish

        # Get all fish entities
        all_entities = self.get_all_entities()
        fish_list = [e for e in all_entities if isinstance(e, Fish)]

        if len(fish_list) < 2:
            return []

        # Build adjacency list of fish that are in poker proximity range
        fish_contacts = {fish: set() for fish in fish_list}

        for i, fish1 in enumerate(fish_list):
            # Use spatial grid to find nearby fish
            nearby_entities = []
            if self.environment is not None:
                # Optimize: Only look for fish - use max poker distance for query
                if hasattr(self.environment, "nearby_fish"):
                    nearby_entities = self.environment.nearby_fish(fish1, radius=FISH_POKER_MAX_DISTANCE)
                else:
                    nearby_entities = self.environment.nearby_agents_by_type(
                        fish1, radius=FISH_POKER_MAX_DISTANCE, agent_class=Fish
                    )
            else:
                nearby_entities = fish_list

            for fish2 in nearby_entities:
                if fish2 == fish1 or not isinstance(fish2, Fish):
                    continue

                # Check if they're in poker proximity (close but not touching)
                if self.check_fish_poker_proximity(fish1, fish2):
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
        from core.entities import Crab, Fish, Food

        # Performance: Cache all_entities and avoid repeated calls
        all_entities = self.get_all_entities()
        all_entities_set = set(all_entities)  # O(1) membership test

        # Performance: Build fish list with type() check first (faster for exact match)
        fish_list = [e for e in all_entities if type(e) is Fish or isinstance(e, Fish)]

        if not fish_list:
            return

        # Data structures for poker groups (proximity-based, not collision)
        fish_poker_contacts = {fish: set() for fish in fish_list}

        # Track which fish have been removed (e.g. eaten) to avoid processing them further
        removed_fish: set = set()

        # Performance: Cache environment and check_collision references
        environment = self.environment
        check_collision = self.check_collision
        
        # Pre-compute squared distance constants for inline proximity check
        poker_min_sq = FISH_POKER_MIN_DISTANCE * FISH_POKER_MIN_DISTANCE
        poker_max_sq = FISH_POKER_MAX_DISTANCE * FISH_POKER_MAX_DISTANCE

        # Single pass over all fish
        for fish in fish_list:
            # Skip if fish was already removed in this frame
            if fish in removed_fish or fish not in all_entities_set:
                continue

            # Use spatial grid to get nearby entities (within collision range)
            if environment is not None:
                # Optimize: Get all interaction candidates (Fish, Food, Crabs) in a single pass
                if hasattr(environment, "nearby_interaction_candidates"):
                    nearby_entities = environment.nearby_interaction_candidates(fish, radius=COLLISION_QUERY_RADIUS, crab_type=Crab)
                elif hasattr(environment, "nearby_fish"):
                    # Fallback to multi-pass if combined query not available (shouldn't happen with new code)
                    nearby_entities = []
                    nearby_entities.extend(environment.nearby_fish(fish, radius=COLLISION_QUERY_RADIUS))
                    nearby_entities.extend(environment.nearby_food(fish, radius=COLLISION_QUERY_RADIUS))
                    nearby_entities.extend(environment.nearby_agents_by_type(fish, radius=COLLISION_QUERY_RADIUS, agent_class=Crab))
                else:
                    nearby_entities = environment.nearby_agents(fish, radius=COLLISION_QUERY_RADIUS)
            else:
                # Fallback to checking all entities if no environment
                nearby_entities = [e for e in all_entities if e is not fish]

            # Cache fish position for inner loop
            fish_cx = fish.pos.x + fish.width * 0.5
            fish_cy = fish.pos.y + fish.height * 0.5

            for other in nearby_entities:
                if other is fish:
                    continue

                # Skip if other entity was removed
                if other not in all_entities_set:
                    continue

                # Performance: Use type() for exact match first
                other_type = type(other)

                if other_type is Fish:
                    # OPTIMIZATION: Inline poker proximity check to avoid method call overhead
                    # Calculate center-to-center distance squared
                    o_cx = other.pos.x + other.width * 0.5
                    o_cy = other.pos.y + other.height * 0.5
                    dx = fish_cx - o_cx
                    dy = fish_cy - o_cy
                    dist_sq = dx * dx + dy * dy
                    
                    # Must be within max distance but farther than min distance
                    if poker_min_sq < dist_sq <= poker_max_sq:
                        fish_poker_contacts[fish].add(other)

                elif other_type is Crab or isinstance(other, Crab):
                    # For crabs: use actual collision check
                    if check_collision(fish, other):
                        if self.handle_fish_crab_collision(fish, other):
                            removed_fish.add(fish)
                            all_entities_set.discard(fish)
                            break  # Fish died, stop checking collisions for it

                elif other_type is Food or isinstance(other, Food):
                    # For food: use actual collision check
                    if check_collision(fish, other):
                        self.handle_fish_food_collision(fish, other)

        # After processing all collisions, handle poker groups
        # Build full adjacency graph (make it symmetric)
        for fish, contacts in fish_poker_contacts.items():
            for contact in contacts:
                if contact in fish_poker_contacts:
                    fish_poker_contacts[contact].add(fish)

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
                contacts = fish_poker_contacts.get(current)
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

                            for neighbor in fish_poker_contacts.get(current, ()):  # type: ignore[arg-type]
                                if neighbor in ready_set and neighbor not in ready_visited:
                                    stack.append(neighbor)

                        if len(ready_group) < 2:
                            continue

                        # IMPORTANT: Ensure ALL fish in the group are within max distance of each other
                        # The DFS can connect A-B-C where A and C are far apart (chain connection)
                        ready_group = self._filter_mutually_proximate_players(
                            ready_group, FISH_POKER_MAX_DISTANCE
                        )
                        if len(ready_group) < 2:
                            continue

                        # Limit to max players to avoid deck exhaustion
                        if len(ready_group) > PokerInteraction.MAX_PLAYERS:
                            ready_group = ready_group[:PokerInteraction.MAX_PLAYERS]

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
                if hasattr(environment, "nearby_fish"):
                    nearby_fish = environment.nearby_fish(fish, radius=MATING_QUERY_RADIUS)
                else:
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
        # Default implementation ensures offspring created from poker
        # reproduction are added to the simulation so evolution can proceed.
        if (
            poker.result is not None
            and poker.result.reproduction_occurred
            and poker.result.offspring is not None
        ):
            self.add_entity(poker.result.offspring)

        # Subclasses can override to add notifications, logging, etc.

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
