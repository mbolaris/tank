"""Resource-producing entities like plants and food."""

import random
from typing import TYPE_CHECKING, Optional

from core.constants import (
    FOOD_TYPES,
    PLANT_FOOD_PRODUCTION_ENERGY,
    PLANT_FOOD_PRODUCTION_INTERVAL,
    PLANT_PRODUCTION_CHANCE,
)
from core.entities.base import Agent
from core.entities.fish import Fish
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.environment import Environment

class Plant(Agent):
    """A plant entity that produces food over time (pure logic, no rendering).

    Attributes:
        food_production_timer: Frames until next food production
        food_production_rate: Base frames between food production
        max_food_capacity: Maximum food that can exist from this plant
        current_food_count: Current number of food items from this plant
    """

    def __init__(
        self,
        environment: "Environment",
        plant_type: int,
        x: float = 100,
        y: float = 400,
        screen_width: int = 800,
        screen_height: int = 600,
    ) -> None:
        """Initialize a plant.

        Args:
            environment: The environment the plant lives in
            plant_type: Type of plant (1, 2, etc.)
            x: Initial x position
            y: Initial y position
            screen_width: Width of simulation area
            screen_height: Height of simulation area
        """
        super().__init__(environment, x, y, 0, screen_width, screen_height)
        self.plant_type: int = plant_type

        # Food production
        self.food_production_timer: int = PLANT_FOOD_PRODUCTION_INTERVAL
        self.food_production_rate: int = PLANT_FOOD_PRODUCTION_INTERVAL
        self.current_food_count: int = 0

    def update_position(self) -> None:
        """Don't update the position of the plant (stationary)."""
        pass

    def should_produce_food(self, time_modifier: float = 1.0) -> bool:
        """Check if plant should produce food.

        Dynamically adjusts production chance based on ecosystem energy levels:
        - Higher production when total energy is low (fish are starving)
        - Lower production when total energy or population is high

        Args:
            time_modifier: Modifier based on day/night (produce more during day)

        Returns:
            True if food should be produced
        """
        from core.constants import (
            AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1,
            AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2,
            AUTO_FOOD_HIGH_POP_THRESHOLD_1,
            AUTO_FOOD_HIGH_POP_THRESHOLD_2,
            AUTO_FOOD_LOW_ENERGY_THRESHOLD,
        )

        # Update timer
        self.food_production_timer -= time_modifier

        if (
            self.food_production_timer <= 0
            and self.current_food_count < PLANT_FOOD_PRODUCTION_ENERGY
        ):
            self.food_production_timer = self.food_production_rate

            # Calculate ecosystem metrics for dynamic production
            fish_list = self.environment.get_agents_of_type(Fish)
            fish_count = len(fish_list)
            total_energy = sum(fish.energy for fish in fish_list)

            # Adjust production chance based on ecosystem state
            production_chance = PLANT_PRODUCTION_CHANCE

            # Increase production when energy is critically low
            if total_energy < AUTO_FOOD_LOW_ENERGY_THRESHOLD:
                production_chance = min(0.6, PLANT_PRODUCTION_CHANCE * 1.5)  # +50% chance
            # Decrease production when energy or population is very high
            elif (
                total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_2
                or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_2
            ):
                production_chance = PLANT_PRODUCTION_CHANCE * 0.3  # 70% reduction
            # Moderate decrease when energy or population is high
            elif (
                total_energy > AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1
                or fish_count > AUTO_FOOD_HIGH_POP_THRESHOLD_1
            ):
                production_chance = PLANT_PRODUCTION_CHANCE * 0.6  # 40% reduction

            # Roll for production with adjusted chance
            return random.random() < production_chance

        return False

    def _get_nectar_chance(self, time_of_day: Optional[float]) -> float:
        """Calculate the chance of producing nectar based on time of day."""
        if time_of_day is None:
            return PLANT_PRODUCTION_CHANCE

        is_dawn = 0.15 <= time_of_day < 0.35
        is_day = 0.35 <= time_of_day < 0.65
        is_dusk = 0.65 <= time_of_day < 0.85

        if is_day:
            return min(0.9, PLANT_PRODUCTION_CHANCE * 1.35)
        if is_dawn or is_dusk:
            return min(0.75, PLANT_PRODUCTION_CHANCE * 1.1)
        return PLANT_PRODUCTION_CHANCE * 0.6

    def produce_food(self, time_of_day: Optional[float] = None) -> "Food":
        """Produce a food item near or on the plant.

        Args:
            time_of_day: Normalized time of day (0.0-1.0) to shape nectar output.

        Returns:
            New food item
        """
        self.current_food_count += 1

        nectar_chance = self._get_nectar_chance(time_of_day)

        if random.random() < nectar_chance:
            # Grow nectar that clings to the top of the plant
            food = Food(
                self.environment,
                self.pos.x + self.width / 2,  # Center of plant
                self.pos.y,  # Top of plant
                source_plant=self,
                food_type="nectar",
                screen_width=self.screen_width,
                screen_height=self.screen_height,
            )
            anchor_x = self.pos.x + self.width / 2 - food.width / 2
            anchor_y = self.pos.y - food.height
            food.pos.update(anchor_x, anchor_y)
            return food

        # All other food falls from top of tank
        food_x = random.randint(0, self.screen_width)
        food_y = 0  # Top of tank

        return Food(
            self.environment,
            food_x,
            food_y,
            source_plant=self,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
        )

    def notify_food_eaten(self) -> None:
        """Notify plant that one of its food items was eaten."""
        self.current_food_count = max(0, self.current_food_count - 1)

    def update(
        self, elapsed_time: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ) -> Optional["Food"]:
        """Update the plant.

        Args:
            elapsed_time: Time elapsed since start
            time_modifier: Time-based modifier (higher during day)
            time_of_day: Normalized time of day (0.0-1.0) for nectar biasing

        Returns:
            New food item if produced, None otherwise
        """
        super().update(elapsed_time)

        # Check food production
        if self.should_produce_food(time_modifier):
            return self.produce_food(time_of_day)

        return None
class Food(Agent):
    """A food entity with variable nutrients (pure logic, no rendering).

    Attributes:
        source_plant: Optional plant that produced this food
        food_type: Type of food (algae, protein, vitamin, energy, rare, nectar)
        food_properties: Dictionary containing energy and other properties
    """

    # Food type definitions (imported from constants.py)
    FOOD_TYPES = FOOD_TYPES

    def __init__(
        self,
        environment: "Environment",
        x: float,
        y: float,
        source_plant: Optional["Plant"] = None,
        food_type: Optional[str] = None,
        allow_stationary_types: bool = True,
        screen_width: int = 800,
        screen_height: int = 600,
        speed: float = 0.0,
    ) -> None:
        """Initialize a food item.

        Args:
            environment: The environment the food lives in
            x: Initial x position
            y: Initial y position
            source_plant: Optional plant that produced this food
            food_type: Type of food (random if None)
            allow_stationary_types: Whether to allow stationary food types
            screen_width: Width of simulation area
            screen_height: Height of simulation area
        """
        # Select random food type based on rarity if not specified
        if food_type is None:
            food_type = self._select_random_food_type(
                include_stationary=allow_stationary_types, include_live=False
            )

        self.food_type = food_type
        self.food_properties = self.FOOD_TYPES[food_type]
        self.is_stationary: bool = self.food_properties.get("stationary", False)

        super().__init__(environment, x, y, speed, screen_width, screen_height)
        self.source_plant: Optional[Plant] = source_plant

        # Energy tracking for partial consumption
        self.max_energy: float = self.food_properties["energy"]
        self.energy: float = self.max_energy
        self.original_width: float = self.width
        self.original_height: float = self.height

    @staticmethod
    def _select_random_food_type(include_stationary: bool = True, include_live: bool = False) -> str:
        """Select a random food type based on rarity weights."""
        food_types = [
            ft
            for ft, props in Food.FOOD_TYPES.items()
            if (include_stationary or not props.get("stationary", False))
            and (include_live or ft != "live")
        ]
        weights = [Food.FOOD_TYPES[ft]["rarity"] for ft in food_types]
        return random.choices(food_types, weights=weights)[0]

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

    def update(self, elapsed_time: int) -> None:
        """Update the food state."""
        if self.is_stationary:
            # Stationary food stays attached to plant
            if self.source_plant is not None:
                anchor_x = self.source_plant.pos.x + self.source_plant.width / 2 - self.width / 2
                anchor_y = self.source_plant.pos.y - self.height
                self.pos.update(anchor_x, anchor_y)
        else:
            super().update(elapsed_time)
            self.sink()

    def sink(self) -> None:
        """Make the food sink at a rate based on its type."""
        if self.is_stationary:
            return
        from core.constants import FOOD_SINK_ACCELERATION

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
        environment: "Environment",
        x: float,
        y: float,
        screen_width: int = 800,
        screen_height: int = 600,
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
            screen_width=screen_width,
            screen_height=screen_height,
            speed=speed,
        )
        # BALANCE: Reduced max_speed from 2.88 to 2.4 to make it catchable
        # Fast fish with speed_modifier=1.3 can now catch it (2.6 > 2.4)
        self.max_speed = speed * 1.6  # 1.5 * 1.6 = 2.4
        self.wander_timer = random.randint(20, 45)
        # BALANCE: Reduced avoid_radius from 180 to 120 so fish can get closer
        self.avoid_radius = 120
        self.wander_strength = 0.25
        
        # Lifespan tracking to prevent unbounded accumulation
        self.max_lifespan = max_lifespan
        self.age = 0

    def is_expired(self) -> bool:
        """Check if this LiveFood has exceeded its lifespan."""
        return self.age >= self.max_lifespan

    def update(self, elapsed_time: int) -> None:
        self.age += 1
        self._apply_wander()
        self._avoid_nearby_fish()
        self._limit_speed()
        self.update_position()

    def _apply_wander(self) -> None:
        self.wander_timer -= 1
        if self.wander_timer <= 0:
            self.add_random_velocity_change([0.3, 0.4, 0.3], 4)
            self.wander_timer = random.randint(20, 45)

    def _avoid_nearby_fish(self) -> None:
        nearby_fish = self.environment.nearby_agents_by_type(self, self.avoid_radius, Fish)
        if not nearby_fish:
            return

        flee_vector = Vector2(0, 0)
        for fish in nearby_fish:
            offset = self.pos - fish.pos
            distance_sq = max(offset.length_squared(), 1)
            # Avoidance using inverse square law
            flee_vector += offset / distance_sq

        if flee_vector.length_squared() > 0:
            # BALANCE: Reduced avoidance force from 1.2 to 0.9 to make catching easier
            self.vel += flee_vector.normalize() * 0.9

    def _limit_speed(self) -> None:
        speed = self.vel.length()
        if speed > self.max_speed:
            direction = self.vel.normalize()
            self.vel = direction * self.max_speed
