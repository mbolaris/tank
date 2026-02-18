"""Collision detection and resolution system.

This module provides collision detection and handling for entities in the simulation.

Architecture Notes:
- CollisionDetector classes implement the Strategy pattern for different
  collision algorithms (AABB, circle-based, etc.)
- CollisionSystem is a simulation system that handles physical collisions
- The system extends BaseSystem and declares UpdatePhase.COLLISION

Design Decision:
--------------
This system handles PHYSICAL collision logic only:
- Fish-Food collisions (eating)
- Fish-Crab collisions (predation)
- Food-Crab collisions

Fish-Fish poker proximity is handled by PokerProximitySystem in the INTERACTION phase.
Plant sprouting logic is included here for simplicity (triggered when nectar is consumed).

Protocol-Based Architecture:
----------------------------
This system uses isinstance(entity, ConcreteType) for collision routing,
which is appropriate since different entity types need different handlers.

However, within collision handlers, we could use protocols for capability checking:
    # Current approach (type-based routing):
    if isinstance(food, PlantNectar):
        handle_nectar_consumption(food)

    # Protocol-based alternative (capability checking):
    if isinstance(food, Consumable):
        food.consume()

The type-based routing pattern is fine here since we're dispatching to
type-specific handlers. Protocols are more valuable for checking capabilities
within handlers (see core/protocols.py for examples).
"""

import logging
from typing import TYPE_CHECKING, Any, Optional, cast

from core.config.plants import PLANT_SPROUTING_CHANCE
from core.config.server import PLANTS_ENABLED
from core.config.simulation import COLLISION_QUERY_RADIUS
from core.entities.plant import PlantNectar
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.entities import Agent, Crab, Fish
    from core.entities.resources import Food
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

    def collides(self, agent1: "Agent", agent2: "Agent", threshold: Optional[float] = None) -> bool:
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

        # Calculate squared distance (avoid sqrt)
        dx = center2_x - center1_x
        dy = center2_y - center1_y
        dist_sq = dx * dx + dy * dy

        # Default threshold is average of widths
        threshold_value = (w1 + w2) / 2 if threshold is None else float(threshold)

        return dist_sq < threshold_value * threshold_value


# Default collision detector
default_collision_detector = RectCollisionDetector()


@runs_in_phase(UpdatePhase.COLLISION)
class CollisionSystem(BaseSystem):
    """System for detecting and handling physical collisions between entities.

    This system runs in the COLLISION phase and handles:
    - Fish-Food collisions (eating)
    - Fish-Crab collisions (predation)
    - Food-Crab collisions
    - Collision statistics for debugging

    Note: Fish-Fish poker proximity is handled by PokerProximitySystem.

    Design Decision:
        Physical collision iteration is handled here, creating clean separation
        of concerns - CollisionSystem owns physical collision logic,
        PokerProximitySystem owns social game triggering.
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

        # Track which fish have been removed (e.g. eaten) to avoid processing them further
        removed_fish: set[Fish] = set()

        # Performance: Cache environment and check_collision references
        environment = self._engine.environment
        check_collision = self.check_collision

        # PERF: Simple sort key for determinism
        # Replaced id() with stable properties (fish_id or position) to ensure
        # cross-process reproducibility (essential for benchmarks).
        Fish_type = Fish
        Food_type = Food
        Crab_type = Crab

        def collision_sort_key(entity: "Agent") -> tuple:
            # Fast type ranking using identity comparison
            e_type = type(entity)
            if e_type is Fish_type:
                type_rank = 0
                # Fish have stable IDs
                secondary = cast(Any, entity).fish_id
            elif e_type is Food_type:
                type_rank = 1
                # Food doesn't have ID, use X pos
                secondary = entity.pos.x
            elif e_type is Crab_type:
                type_rank = 2
                # Crabs use X pos
                secondary = entity.pos.x
            else:
                type_rank = 3
                secondary = entity.pos.x

            # Use Y pos as final tie breaker
            return (type_rank, secondary, entity.pos.y)

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
                            fish, radius=COLLISION_QUERY_RADIUS, agent_type=Crab
                        )
                    )
                else:
                    nearby_entities = environment.nearby_agents(fish, radius=COLLISION_QUERY_RADIUS)
            else:
                # Fallback to checking all entities if no environment
                nearby_entities = [e for e in all_entities if e is not fish]

            nearby_entities = sorted(nearby_entities, key=collision_sort_key)

            # Cache fish position for inner loop
            fish.pos.x + fish.width * 0.5
            fish.pos.y + fish.height * 0.5

            for other in nearby_entities:
                if other is fish:
                    continue

                # Skip if other entity was removed
                if other not in all_entities_set:
                    continue

                if isinstance(other, Crab):
                    # For crabs: use actual collision check
                    if check_collision(fish, other):
                        if self._handle_fish_crab_collision(fish, other):
                            removed_fish.add(fish)
                            all_entities_set.discard(fish)
                            break  # Fish died, stop checking collisions for it

                elif isinstance(other, Food):
                    if self._engine.is_pending_removal(other):
                        continue
                    # For food: use actual collision check
                    if check_collision(fish, other):
                        self.handle_fish_food_collision(fish, other)
                        if self._engine.is_pending_removal(other):
                            all_entities_set.discard(other)

        # Note: Fish-fish poker proximity is now handled by PokerProximitySystem

    def _handle_fish_crab_collision(self, fish: "Fish", crab: "Crab") -> bool:
        """Handle collision between a fish and a crab (predator).

        Args:
            fish: The fish entity
            crab: The crab (predator) entity

        Returns:
            bool: True if the fish died from the collision, False otherwise
        """
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

    def _handle_food_collisions(self) -> None:
        """Handle collisions involving food.

        Optimized to iterate Crabs instead of Food, as Crabs are fewer and actively hunt Food.
        This reduces complexity from O(Food * Neighbors) to O(Crabs * FoodNeighbors).
        """
        from core.entities import Crab, Food

        all_entities = self._engine.get_all_entities()

        # Find all crabs
        # OPTIMIZATION: Manually filter for crabs instead of iterating all food
        crabs = [e for e in all_entities if isinstance(e, Crab)]

        if not crabs:
            return

        # Sort crabs for deterministic processing order
        # Use position instead of id() for cross-process reproducibility
        crabs.sort(key=lambda c: (c.pos.x, c.pos.y))

        environment = self._engine.environment
        check_collision = self.check_collision

        # Helper for deterministic sorting of food
        def food_sort_key(f):
            # Use position instead of id() for cross-process reproducibility
            return (f.pos.x, f.pos.y)

        for crab in crabs:
            if self._engine.is_pending_removal(crab):
                continue

            # Find nearby food only
            if environment:
                nearby_food_agents = environment.nearby_agents_by_type(
                    crab, radius=COLLISION_QUERY_RADIUS, agent_type=Food
                )
                nearby_food = [f for f in nearby_food_agents if isinstance(f, Food)]
            else:
                nearby_food = [e for e in all_entities if isinstance(e, Food)]

            if not nearby_food:
                continue

            # Sort nearby food deterministically
            nearby_food.sort(key=food_sort_key)

            for food in nearby_food:
                # Check if food is already eaten (pending removal)
                if self._engine.is_pending_removal(food):
                    continue

                if check_collision(crab, food):
                    crab.eat_food(food)
                    food.get_eaten()
                    self._engine.request_remove(food, reason="crab_food_collision")
                    self._frame_entities_removed += 1

    def handle_fish_food_collision(self, fish: "Fish", food: "Food") -> None:
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
                from core.util.rng import require_rng

                rng = require_rng(self._engine, "CollisionSystem.handle_fish_food_collision")
                if rng.random() < PLANT_SPROUTING_CHANCE:
                    self._engine.sprout_new_plant(parent_genome, parent_x, parent_y)

                self._engine.request_remove(food, reason="plant_nectar_consumed")
                self._frame_entities_removed += 1
        else:
            fish.eat(food)

            if food.is_fully_consumed():
                food.get_eaten()
                self._engine.request_remove(food, reason="food_consumed")
                self._frame_entities_removed += 1

    def get_debug_info(self) -> dict[str, Any]:
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
