"""Resource-producing entities like plants and food."""

import random
from typing import TYPE_CHECKING, Optional

from core.config.food import (
    FOOD_SINK_ACCELERATION,
    FOOD_TYPES,
)
from core.entities.base import Agent
from core.entities.fish import Fish
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.environment import Environment
    from core.world import World
    from core.entities.plant import Plant


class Food(Agent):
    """A food entity with variable nutrients (pure logic, no rendering).

    Attributes:
        source_plant: Optional plant that produced this food
        food_type: Type of food (algae, protein, vitamin, energy, rare, nectar)
        food_properties: Dictionary containing energy and other properties
    """

    # Food type definitions (imported from constants.py)
    FOOD_TYPES = FOOD_TYPES

    def is_dead(self) -> bool:
        """Check if food is dead (it's not)."""
        return False


    def __init__(
        self,
        environment: "World",
        x: float,
        y: float,
        source_plant: Optional["Plant"] = None,
        food_type: Optional[str] = None,
        allow_stationary_types: bool = True,
        speed: float = 0.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Initialize a food item.

        Args:
            environment: The world the food lives in
            x: Initial x position
            y: Initial y position
            source_plant: Optional plant that produced this food
            food_type: Type of food (random if None)
            allow_stationary_types: Whether to allow stationary food types
            rng: Random number generator for deterministic food type selection
        """
        # Select random food type based on rarity if not specified
        if food_type is None:
            # Use provided rng, or fall back to environment._rng, or create new Random
            _rng = rng or getattr(environment, '_rng', None) or random.Random()
            food_type = self._select_random_food_type(
                include_stationary=allow_stationary_types, include_live=False, rng=_rng
            )

        self.food_type = food_type
        self.food_properties = self.FOOD_TYPES[food_type]
        self.is_stationary: bool = self.food_properties.get("stationary", False)

        super().__init__(environment, x, y, speed)
        self.source_plant: Optional["Plant"] = source_plant

        # Energy tracking for partial consumption
        self.max_energy: float = self.food_properties["energy"]
        self.energy: float = self.max_energy
        self.original_width: float = self.width
        self.original_height: float = self.height

    @staticmethod
    def _select_random_food_type(
        include_stationary: bool = True,
        include_live: bool = False,
        rng: Optional[random.Random] = None,
    ) -> str:
        """Select a random food type based on rarity weights.

        Args:
            include_stationary: Whether to include stationary food types
            include_live: Whether to include live food type
            rng: Random number generator (uses new Random if None)

        Returns:
            Selected food type string
        """
        _rng = rng if rng is not None else random.Random()
        food_types = [
            ft
            for ft, props in Food.FOOD_TYPES.items()
            if (include_stationary or not props.get("stationary", False))
            and (include_live or ft != "live")
        ]
        weights = [Food.FOOD_TYPES[ft]["rarity"] for ft in food_types]
        return _rng.choices(food_types, weights=weights)[0]

    def get_energy_value(self) -> float:
        """Get the current energy value this food provides."""
        return self.energy

    def take_bite(self, bite_size: float) -> float:
        """Take a bite from the food.

        Args:
            bite_size: Amount of energy to attempt to consume

        Returns:
            Amount of energy actually consumed
        """
        consumed = min(self.energy, bite_size)
        self.energy -= consumed

        # Update size based on remaining energy
        # Minimum size is 20% of original
        energy_ratio = self.energy / self.max_energy
        size_ratio = 0.2 + (0.8 * energy_ratio)

        self.set_size(
            self.original_width * size_ratio,
            self.original_height * size_ratio
        )

        return consumed

    def is_fully_consumed(self) -> bool:
        """Check if food is fully consumed."""
        return self.energy <= 0.1  # Small threshold for float comparison

    def update(self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None) -> "EntityUpdateResult":
        """Update the food state."""
        from core.entities.base import EntityUpdateResult

        if self.is_stationary:
            # Stationary food stays attached to plant
            if self.source_plant is not None:
                anchor_x = self.source_plant.pos.x + self.source_plant.width / 2 - self.width / 2
                anchor_y = self.source_plant.pos.y - self.height
                self.pos.update(anchor_x, anchor_y)
            return EntityUpdateResult()
        else:
            # Call super with all arguments
            super().update(frame_count, time_modifier, time_of_day)
            self.sink()
            return EntityUpdateResult()

    def sink(self) -> None:
        """Make the food sink at a rate based on its type."""
        if self.is_stationary:
            return

        sink_rate = FOOD_SINK_ACCELERATION * self.food_properties["sink_multiplier"]
        self.vel.y += sink_rate

    def get_eaten(self) -> None:
        """Get eaten and notify source plant if applicable."""
        # Notify plant that food was consumed
        if self.source_plant is not None:
            self.source_plant.notify_food_eaten()


class LiveFood(Food):
    """Active food that tries to avoid fish.

    Live food moves around the tank instead of sinking, making it harder to
    catch. It makes small wandering motions and steers away from nearby fish
    to simulate evasive movement.

    After a set lifespan, LiveFood expires and is removed to prevent accumulation.
    """

    def __init__(
        self,
        environment: "World",
        x: float,
        y: float,
        speed: float = 1.5,
        max_lifespan: int = 900,  # 30 seconds at 30fps
    ) -> None:
        super().__init__(
            environment,
            x,
            y,
            source_plant=None,
            food_type="live",
            allow_stationary_types=False,
            speed=speed,
        )
        # BALANCE: Reduced max_speed to 1.4 so average fish (speed ~1.87) can reliably catch it
        # Fish speed_modifier averages ~0.85, giving 2.2 * 0.85 = 1.87 base speed
        # LiveFood at 1.4 gives ~33% speed advantage to average fish
        self.max_speed = speed * 0.93  # 1.5 * 0.93 = 1.4
        # Use environment._rng if available, otherwise create new unseeded Random
        self._rng = getattr(environment, '_rng', None) or random.Random()
        self.wander_timer = self._rng.randint(20, 45)
        # BALANCE: Reduced avoid_radius from 180 to 80 so fish can get much closer
        # before triggering flee response - makes hunting more effective
        self.avoid_radius = 80
        self.wander_strength = 0.25

        # Lifespan tracking to prevent unbounded accumulation
        self.max_lifespan = max_lifespan
        self.age = 0

    def is_expired(self) -> bool:
        """Check if this LiveFood has exceeded its lifespan."""
        return self.age >= self.max_lifespan

    def update(self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None) -> "EntityUpdateResult":
        from core.entities.base import EntityUpdateResult

        self.age += 1
        self._apply_wander()
        self._avoid_nearby_fish()
        self._limit_speed()
        self.update_position()
        return EntityUpdateResult()

    def _apply_wander(self) -> None:
        self.wander_timer -= 1
        if self.wander_timer <= 0:
            self.add_random_velocity_change([0.3, 0.4, 0.3], 4)
            self.wander_timer = self._rng.randint(20, 45)

    def _avoid_nearby_fish(self) -> None:
        nearby_fish = self.environment.nearby_agents_by_type(self, self.avoid_radius, Fish)
        if not nearby_fish:
            return

        flee_vector = Vector2(0, 0)
        # BALANCE: Only consider the closest 2 fish to prevent chaotic flee vectors
        # when many fish chase simultaneously - makes behavior more predictable
        sorted_fish = sorted(nearby_fish, key=lambda f: (self.pos - f.pos).length_squared())
        for fish in sorted_fish[:2]:
            offset = self.pos - fish.pos
            distance_sq = max(offset.length_squared(), 1)
            # Avoidance using inverse square law
            flee_vector += offset / distance_sq

        if flee_vector.length_squared() > 0:
            # BALANCE: Reduced avoidance force from 0.9 to 0.5 to make catching easier
            # Combined with max_speed reduction and smaller avoid_radius, fish can now
            # reliably catch live food with coordinated pursuit
            self.vel += flee_vector.normalize() * 0.5

    def _limit_speed(self) -> None:
        speed = self.vel.length()
        if speed > self.max_speed:
            direction = self.vel.normalize()
            self.vel = direction * self.max_speed
