"""Collision detection and resolution system.

This module provides collision detection and handling for entities in the simulation.

Architecture Notes:
- CollisionDetector classes implement the Strategy pattern for different
  collision algorithms (AABB, circle-based, etc.)
- CollisionSystem is a simulation system that handles all collision logic
- The system extends BaseSystem and declares UpdatePhase.COLLISION

Design Decision:
--------------
This system owns ALL collision iteration and handling, providing clean
separation of concerns. The collision logic includes:
- Fish-Food collisions (eating)
- Fish-Crab collisions (predation)
- Fish-Fish proximity detection for poker games
- Food-Crab collisions

Plant sprouting logic is included here for simplicity (triggered when nectar is consumed).
"""

import logging
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from core.config.ecosystem import FISH_POKER_MAX_DISTANCE, FISH_POKER_MIN_DISTANCE
from core.config.plants import PLANT_SPROUTING_CHANCE
from core.config.server import PLANTS_ENABLED, POKER_ACTIVITY_ENABLED
from core.config.simulation import COLLISION_QUERY_RADIUS
from core.entities.plant import PlantNectar
from core.poker_interaction import (
    PokerInteraction,
    MAX_PLAYERS as POKER_MAX_PLAYERS,
    filter_mutually_proximate,
    get_ready_players,
)
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.entities import Agent, Crab, Fish, Food
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


class CollisionDetector:
    """Base class for collision detection strategies."""

    def collides(self, agent1: "Agent", agent2: "Agent") -> bool:
        """Check if two agents collide.

        Args:
            agent1: First agent
            agent2: Second agent

        Returns:
            True if agents are colliding
        """
        raise NotImplementedError("Subclasses must implement collides()")


class RectCollisionDetector(CollisionDetector):
    """Rectangle-based collision detection (AABB)."""

    def collides(self, agent1: "Agent", agent2: "Agent") -> bool:
        """Check if two agents' bounding boxes collide.

        Args:
            agent1: First agent
            agent2: Second agent

        Returns:
            True if bounding boxes overlap
        """
        # Get bounding boxes
        x1, y1, w1, h1 = agent1.get_rect()
        x2, y2, w2, h2 = agent2.get_rect()

        # AABB collision detection
        return not (
            x1 + w1 < x2  # agent1 is left of agent2
            or x1 > x2 + w2  # agent1 is right of agent2
            or y1 + h1 < y2  # agent1 is above agent2
            or y1 > y2 + h2  # agent1 is below agent2
        )


class CircleCollisionDetector(CollisionDetector):
    """Circle-based collision detection (distance-based)."""

    def collides(
        self, agent1: "Agent", agent2: "Agent", threshold: Optional[float] = None
    ) -> bool:
        """Check if two agents collide based on distance.

        Args:
            agent1: First agent
            agent2: Second agent
            threshold: Distance threshold (if None, uses average of widths)

        Returns:
            True if distance between centers is less than threshold
        """
        # Calculate centers
        x1, y1, w1, h1 = agent1.get_rect()
        x2, y2, w2, h2 = agent2.get_rect()

        center1_x = x1 + w1 / 2
        center1_y = y1 + h1 / 2
        center2_x = x2 + w2 / 2
        center2_y = y2 + h2 / 2

        # Calculate distance
        dx = center2_x - center1_x
        dy = center2_y - center1_y
        distance = (dx**2 + dy**2) ** 0.5

        # Default threshold is average of widths
        if threshold is None:
            threshold = (w1 + w2) / 2

        return distance < threshold


# Default collision detector
default_collision_detector = RectCollisionDetector()


@runs_in_phase(UpdatePhase.COLLISION)
class CollisionSystem(BaseSystem):
    """System for detecting and handling all collisions between entities.

    This system runs in the COLLISION phase and handles:
    - Fish-Food collisions (eating)
    - Fish-Crab collisions (predation)
    - Fish-Fish proximity for poker game triggering
    - Food-Crab collisions
    - Collision statistics for debugging

    Design Decision:
        All collision iteration is handled here, creating clean separation
        of concerns - CollisionSystem owns all collision-related logic,
        and the SimulationEngine only orchestrates system execution.
    """

    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the collision system.

        Args:
            engine: The simulation engine
        """
        super().__init__(engine, "Collision")
        # Cumulative stats (all-time)
        self._collisions_checked: int = 0
        self._collisions_detected: int = 0
        self._fish_food_collisions: int = 0
        self._fish_crab_collisions: int = 0
        self._poker_games_triggered: int = 0

        # Per-frame stats (reset each frame)
        self._frame_collisions_checked: int = 0
        self._frame_collisions_detected: int = 0
        self._frame_food_eaten: int = 0
        self._frame_entities_removed: int = 0
        self._frame_fish_deaths: int = 0

    def _do_update(self, frame: int) -> Optional[SystemResult]:
        """Process all collisions for this frame.

        This is now the main collision processing method. It handles:
        - Fish-Fish proximity for poker games
        - Fish-Food collisions (eating)
        - Fish-Crab collisions (predation)
        - Food-Crab collisions

        Returns:
            SystemResult with collision statistics
        """
        # Process all collision types
        self._handle_fish_collisions()
        self._handle_food_collisions()

        # Build result from per-frame stats
        result = SystemResult(
            entities_affected=self._frame_collisions_detected,
            entities_removed=self._frame_entities_removed,
            details={
                "collisions_checked": self._frame_collisions_checked,
                "collisions_detected": self._frame_collisions_detected,
                "food_eaten": self._frame_food_eaten,
                "fish_deaths": self._frame_fish_deaths,
            },
        )

        # Reset per-frame counters
        self._frame_collisions_checked = 0
        self._frame_collisions_detected = 0
        self._frame_food_eaten = 0
        self._frame_entities_removed = 0
        self._frame_fish_deaths = 0

        return result

    def check_collision(self, e1: "Agent", e2: "Agent") -> bool:
        """Check if two entities collide using bounding box collision.

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities are colliding
        """
        self._collisions_checked += 1
        self._frame_collisions_checked += 1
        collides = (
            e1.pos.x < e2.pos.x + e2.width
            and e1.pos.x + e1.width > e2.pos.x
            and e1.pos.y < e2.pos.y + e2.height
            and e1.pos.y + e1.height > e2.pos.y
        )
        if collides:
            self._collisions_detected += 1
            self._frame_collisions_detected += 1
        return collides

    def _handle_fish_collisions(self) -> None:
        """Handle all collisions involving fish.

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
        all_entities = self._engine.get_all_entities()
        all_entities_set = set(all_entities)  # O(1) membership test

        # Performance: Build fish list with type() check first (faster for exact match)
        fish_list = [e for e in all_entities if type(e) is Fish or isinstance(e, Fish)]

        if not fish_list:
            return

        # Data structures for poker groups (proximity-based, not collision)
        fish_poker_contacts: Dict["Fish", Set["Fish"]] = {fish: set() for fish in fish_list}

        # Track which fish have been removed (e.g. eaten) to avoid processing them further
        removed_fish: Set["Fish"] = set()

        # Performance: Cache environment and check_collision references
        environment = self._engine.environment
        check_collision = self.check_collision

        entity_order = {entity: idx for idx, entity in enumerate(all_entities)}
        grid = environment.spatial_grid if environment is not None else None
        agent_cells = grid.agent_cells if grid is not None else None

        def collision_sort_key(entity: "Agent") -> tuple:
            cell = agent_cells.get(entity) if agent_cells is not None else None
            if cell is None:
                cell = (0, 0)

            if isinstance(entity, Fish):
                type_rank = 0
            elif isinstance(entity, Food):
                type_rank = 1
            elif isinstance(entity, Crab):
                type_rank = 2
            else:
                type_rank = 3

            entity_id = getattr(entity, "fish_id", None)
            if entity_id is None:
                entity_id = getattr(entity, "plant_id", None)
            if entity_id is None:
                pos = getattr(entity, "pos", None)
                if pos is not None:
                    entity_id = (
                        1,
                        float(pos.x),
                        float(pos.y),
                        float(getattr(entity, "width", 0.0)),
                        float(getattr(entity, "height", 0.0)),
                        float(getattr(entity, "energy", 0.0)),
                        entity_order.get(entity, 0),
                    )
                else:
                    entity_id = (2, entity_order.get(entity, 0))
            else:
                entity_id = (0, int(entity_id))

            return (cell[0], cell[1], type_rank, entity_id)

        def poker_neighbor_key(entity: "Agent") -> int:
            return getattr(entity, "fish_id", entity_order.get(entity, 0))

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
                    nearby_entities = environment.nearby_interaction_candidates(
                        fish, radius=COLLISION_QUERY_RADIUS, crab_type=Crab
                    )
                elif hasattr(environment, "nearby_evolving_agents"):
                    # Fallback to multi-pass if combined query not available
                    nearby_entities = []
                    nearby_entities.extend(
                        environment.nearby_evolving_agents(fish, radius=COLLISION_QUERY_RADIUS)
                    )
                    nearby_entities.extend(
                        environment.nearby_resources(fish, radius=COLLISION_QUERY_RADIUS)
                    )
                    nearby_entities.extend(
                        environment.nearby_agents_by_type(
                            fish, radius=COLLISION_QUERY_RADIUS, agent_class=Crab
                        )
                    )
                else:
                    nearby_entities = environment.nearby_agents(fish, radius=COLLISION_QUERY_RADIUS)
            else:
                # Fallback to checking all entities if no environment
                nearby_entities = [e for e in all_entities if e is not fish]

            nearby_entities = sorted(nearby_entities, key=collision_sort_key)

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
                        if self._handle_fish_crab_collision(fish, other):
                            removed_fish.add(fish)
                            all_entities_set.discard(fish)
                            break  # Fish died, stop checking collisions for it

                elif other_type is Food or isinstance(other, Food):
                    # For food: use actual collision check
                    if check_collision(fish, other):
                        self.handle_fish_food_collision(fish, other)

        # After processing all collisions, handle poker groups
        self._process_poker_groups(
            fish_list, fish_poker_contacts, removed_fish, all_entities_set, poker_neighbor_key
        )

    def _handle_fish_crab_collision(self, fish: "Fish", crab: "Crab") -> bool:
        """Handle collision between a fish and a crab (predator).

        Args:
            fish: The fish entity
            crab: The crab (predator) entity

        Returns:
            bool: True if the fish died from the collision, False otherwise
        """
        from core.events import EntityDiedEvent

        self._fish_crab_collisions += 1

        # Mark the predator encounter for death attribution
        fish.mark_predator_encounter()

        # Crab can only kill if hunt cooldown is ready
        if crab.can_hunt():
            crab.eat_fish(fish)
            self._record_fish_death(fish, "predation")
            return True
        return False

    def _record_fish_death(self, fish: "Fish", cause: Optional[str] = None) -> None:
        """Record a fish death by delegating to the lifecycle system.

        Args:
            fish: The fish that died
            cause: Optional death cause override
        """
        self._frame_fish_deaths += 1
        self._engine.record_fish_death(fish, cause)

    def _process_poker_groups(
        self,
        fish_list: List["Fish"],
        fish_poker_contacts: Dict["Fish", Set["Fish"]],
        removed_fish: Set["Fish"],
        all_entities_set: Set["Agent"],
        poker_neighbor_key,
    ) -> None:
        """Process fish proximity groups and trigger poker games.

        Args:
            fish_list: All fish in the simulation
            fish_poker_contacts: Adjacency map of fish in poker proximity
            removed_fish: Fish that have been removed this frame
            all_entities_set: Set of all entities for membership testing
            poker_neighbor_key: Sort key function for deterministic ordering
        """
        # Build full adjacency graph (make it symmetric)
        for fish, contacts in fish_poker_contacts.items():
            for contact in contacts:
                if contact in fish_poker_contacts:
                    fish_poker_contacts[contact].add(fish)

        # Find connected components using DFS
        visited: Set["Fish"] = set()
        processed_fish: Set["Fish"] = set()  # For poker game tracking

        for fish in fish_list:
            if fish in visited or fish in removed_fish or fish not in all_entities_set:
                continue

            # Start a new group with DFS
            group: List["Fish"] = []
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
                    for neighbor in sorted(contacts, key=poker_neighbor_key):
                        if neighbor not in visited:
                            stack.append(neighbor)

            # Play poker if group has 2+ fish
            if len(group) >= 2:
                # Filter out fish that already played (just in case)
                valid_fish = [f for f in group if f not in processed_fish]

                if len(valid_fish) >= 2 and POKER_ACTIVITY_ENABLED:
                    # Only allow currently eligible fish to queue for poker.
                    ready_fish = get_ready_players(valid_fish)

                    if len(ready_fish) < 2:
                        continue

                    # Build poker groups only from ready fish that are directly touching
                    ready_set = set(ready_fish)
                    ready_visited: Set["Fish"] = set()

                    for start in ready_fish:
                        if start in ready_visited:
                            continue

                        stack = [start]
                        ready_group: List["Fish"] = []

                        while stack:
                            current = stack.pop()

                            if current in ready_visited:
                                continue

                            ready_visited.add(current)
                            ready_group.append(current)

                            for neighbor in sorted(
                                fish_poker_contacts.get(current, ()),
                                key=poker_neighbor_key,
                            ):
                                if neighbor in ready_set and neighbor not in ready_visited:
                                    stack.append(neighbor)

                        if len(ready_group) < 2:
                            continue

                        # IMPORTANT: Ensure ALL fish in the group are within max distance of each other
                        ready_group = filter_mutually_proximate(
                            ready_group, FISH_POKER_MAX_DISTANCE
                        )
                        if len(ready_group) < 2:
                            continue

                        # Limit to max players to avoid deck exhaustion
                        if len(ready_group) > POKER_MAX_PLAYERS:
                            ready_group = ready_group[:POKER_MAX_PLAYERS]

                        rng = getattr(self._engine, "rng", None)
                        poker = PokerInteraction(ready_group, rng=rng)
                        if poker.play_poker():
                            self._engine.handle_poker_result(poker)
                            self._poker_games_triggered += 1

                            # Check deaths
                            for f in ready_group:
                                if f.is_dead() and f in all_entities_set:
                                    self._record_fish_death(f)
                                    removed_fish.add(f)
                                    all_entities_set.discard(f)

                        processed_fish.update(ready_group)

    def _handle_food_collisions(self) -> None:
        """Handle collisions involving food.

        Uses spatial partitioning to reduce collision checks from O(n²) to O(n*k).

        Performance optimizations:
        - Use set for entity membership tracking
        - Cache method references
        """
        from core.entities import Crab, Food

        all_entities = self._engine.get_all_entities()
        all_entities_set = set(all_entities)

        # Performance: Use type() check first
        food_list = [e for e in all_entities if type(e) is Food or isinstance(e, Food)]

        if not food_list:
            return

        # Performance: Cache references
        environment = self._engine.environment
        check_collision = self.check_collision

        entity_order = {entity: idx for idx, entity in enumerate(all_entities)}
        grid = environment.spatial_grid if environment is not None else None
        agent_cells = grid.agent_cells if grid is not None else None

        def collision_sort_key(entity: "Agent") -> tuple:
            cell = agent_cells.get(entity) if agent_cells is not None else None
            if cell is None:
                cell = (0, 0)

            entity_id = getattr(entity, "fish_id", None)
            if entity_id is None:
                entity_id = getattr(entity, "plant_id", None)
            if entity_id is None:
                pos = getattr(entity, "pos", None)
                if pos is not None:
                    entity_id = (
                        1,
                        float(pos.x),
                        float(pos.y),
                        float(getattr(entity, "width", 0.0)),
                        float(getattr(entity, "height", 0.0)),
                        float(getattr(entity, "energy", 0.0)),
                        entity_order.get(entity, 0),
                    )
                else:
                    entity_id = (2, entity_order.get(entity, 0))
            else:
                entity_id = (0, int(entity_id))

            return (cell[0], cell[1], type(entity).__name__, entity_id)

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

            nearby_entities = sorted(nearby_entities, key=collision_sort_key)

            for other in nearby_entities:
                if other is food:
                    continue

                if check_collision(food, other):
                    # Fish-food collisions are handled in _handle_fish_collisions()
                    if type(other) is Crab or isinstance(other, Crab):
                        other.eat_food(food)
                        food.get_eaten()
                        self._engine.remove_entity(food)
                        all_entities_set.discard(food)
                        self._frame_entities_removed += 1
                        break

    def handle_fish_food_collision(self, fish: "Agent", food: "Agent") -> None:
        """Handle collision between a fish and food, including plant nectar.

        Args:
            fish: The fish entity
            food: The food entity being eaten

        Note: Plant sprouting logic is included here (when nectar is consumed,
        there's a chance to sprout a new plant nearby).
        """
        self._fish_food_collisions += 1
        self._frame_food_eaten += 1

        if isinstance(food, PlantNectar) and PLANTS_ENABLED:
            fish.eat(food)

            if food.is_consumed():
                parent_genome = food.consume()
                parent_x = food.source_plant.pos.x if food.source_plant else food.pos.x
                parent_y = food.source_plant.pos.y if food.source_plant else food.pos.y

                # Check sprouting chance (use engine RNG for determinism)
                rng = (
                    self._engine.rng
                    if hasattr(self._engine, "rng") and self._engine.rng
                    else random
                )
                if rng.random() < PLANT_SPROUTING_CHANCE:
                    self._engine.sprout_new_plant(parent_genome, parent_x, parent_y)

                self._engine.remove_entity(food)
                self._frame_entities_removed += 1
        else:
            fish.eat(food)

            if food.is_fully_consumed():
                food.get_eaten()
                self._engine.remove_entity(food)
                self._frame_entities_removed += 1

    def get_debug_info(self) -> Dict[str, Any]:
        """Return collision statistics for debugging."""
        return {
            **super().get_debug_info(),
            "collisions_checked": self._collisions_checked,
            "collisions_detected": self._collisions_detected,
            "fish_food_collisions": self._fish_food_collisions,
            "fish_crab_collisions": self._fish_crab_collisions,
            "poker_games_triggered": self._poker_games_triggered,
            "hit_rate": (
                self._collisions_detected / self._collisions_checked
                if self._collisions_checked > 0
                else 0.0
            ),
        }
