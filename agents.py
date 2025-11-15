import pygame
from pygame.math import Vector2
from pygame.surface import Surface
import os
from typing import List, TYPE_CHECKING, Optional
from image_loader import ImageLoader
from constants import (FILES, INIT_POS, SCREEN_WIDTH, SCREEN_HEIGHT, IMAGE_CHANGE_RATE,
                       AVOIDANCE_SPEED_CHANGE, ALIGNMENT_SPEED_CHANGE, RANDOM_MOVE_PROBABILITIES,
                       RANDOM_VELOCITY_DIVISOR, FISH_GROWTH_RATE, PLANT_SWAY_RANGE,
                       PLANT_SWAY_SPEED, FOOD_SINK_ACCELERATION)
import random
import math
from enum import Enum
from genetics import Genome

if TYPE_CHECKING:
    import environment
    from movement_strategy import MovementStrategy
    from ecosystem import EcosystemManager


class LifeStage(Enum):
    """Life stages of a fish."""
    BABY = "baby"
    JUVENILE = "juvenile"
    ADULT = "adult"
    ELDER = "elder"


class Agent(pygame.sprite.Sprite):
    """A base class for all sprites in the game."""

    def __init__(self, environment: 'environment.Environment', filenames: List[str],
                 x: float, y: float, speed: float) -> None:
        """Initialize a sprite."""
        super().__init__()
        self.animation_frames: List[Surface] = [ImageLoader.load_image(os.path.join('images', filename)) for filename in filenames]
        self.image_index: int = 0
        self.speed: float = speed
        self.vel: Vector2 = Vector2(speed, 0)
        self.pos: Vector2 = Vector2(x, y)
        self.image: Surface = self.get_current_image()
        self.rect: pygame.Rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.avoidance_velocity: Vector2 = Vector2(0, 0)
        self.environment: 'environment.Environment' = environment

    def update_position(self) -> None:
        """Update the position of the sprite."""
        effective_velocity = self.vel + self.avoidance_velocity
        self.pos += effective_velocity
        self.rect.topleft = self.pos
        self.handle_screen_edges()

    def handle_screen_edges(self) -> None:
        """Handle the sprite hitting the edge of the screen."""
        if self.rect.x < 0 or self.rect.right > SCREEN_WIDTH:
            self.vel.x *= -1
        if self.rect.y < 0:
            self.rect.y = 0
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

    def get_current_image(self) -> Surface:
        """Get the current image of the sprite."""
        if self.vel.x > 0:
            return self.animation_frames[self.image_index]
        else:
            return pygame.transform.flip(self.animation_frames[self.image_index], True, False)

    def update_image_index(self, elapsed_time: int) -> None:
        """Update the image index of the sprite."""
        if len(self.animation_frames) > 1:
            self.image_index = (elapsed_time // IMAGE_CHANGE_RATE) % len(self.animation_frames)

    def update(self, elapsed_time: int) -> None:
        """Update the sprite."""
        self.update_image_index(elapsed_time)
        self.update_position()
        self.image = self.get_current_image()

    def add_random_velocity_change(self) -> None:
        """Add a random direction change to the sprite."""
        random_x_direction = random.choices([-1, 0, 1], RANDOM_MOVE_PROBABILITIES)[0]
        random_y_direction = random.choices([-1, 0, 1], RANDOM_MOVE_PROBABILITIES)[0]
        self.vel.x += random_x_direction / RANDOM_VELOCITY_DIVISOR
        self.vel.y += random_y_direction / RANDOM_VELOCITY_DIVISOR

    def avoid(self, other_sprites: List['Agent'], min_distance: float) -> None:
        """Avoid other sprites."""
        any_sprite_close = False

        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()

            if 0 < dist_length < min_distance:
                any_sprite_close = True
                # Safety check: only normalize if vector has length
                if dist_length > 0:
                    velocity_change = dist_vector.normalize()
                    if isinstance(other, Crab):
                        velocity_change.y = abs(velocity_change.y)
                    self.avoidance_velocity -= velocity_change * AVOIDANCE_SPEED_CHANGE

        # Only reset avoidance_velocity when no sprites are close
        if not any_sprite_close:
            self.avoidance_velocity = Vector2(0, 0)

    def align_near(self, other_sprites: List['Agent'], min_distance: float) -> None:
        if not other_sprites:
            return
        avg_pos = self.get_average_position(other_sprites)
        self.adjust_velocity_towards_or_away_from_other_sprites(other_sprites, avg_pos, min_distance)
        if self.vel.x != 0 or self.vel.y != 0:  # Checking if it's a zero vector
            self.vel = self.vel.normalize() * abs(self.speed)

    def get_average_position(self, other_sprites: List['Agent']) -> Vector2:
        """Calculate the average position of other sprites."""
        return sum((other.pos for other in other_sprites), Vector2()) / len(other_sprites)

    def adjust_velocity_towards_or_away_from_other_sprites(self, other_sprites: List['Agent'],
                                                           avg_pos: Vector2, min_distance: float) -> None:
        """Adjust velocity based on the position of other sprites."""
        for other in other_sprites:
            dist_vector = other.pos - self.pos
            dist_length = dist_vector.length()
            if 0 < dist_length < min_distance:
                self.move_away(dist_vector)
            else:
                difference = avg_pos - self.pos
                difference_length = difference.length()

                if difference_length > 0:
                    self.move_towards(difference)

    def move_away(self, dist_vector: Vector2) -> None:
        """Adjust velocity to move away from another sprite."""
        dist_length = dist_vector.length()
        if dist_length > 0:
            self.vel -= dist_vector.normalize() * AVOIDANCE_SPEED_CHANGE

    def move_towards(self, difference: Vector2) -> None:
        """Adjust velocity to move towards the average position of other sprites."""
        diff_length = difference.length()
        if diff_length > 0:
            self.vel += difference.normalize() * ALIGNMENT_SPEED_CHANGE

class Fish(Agent):
    """A fish sprite with genetics, energy, and life cycle.

    Attributes:
        genome: Genetic traits
        energy: Current energy level
        max_energy: Maximum energy capacity
        age: Age in frames
        max_age: Maximum lifespan in frames
        life_stage: Current life stage
        generation: Generation number
        fish_id: Unique identifier
        is_pregnant: Whether fish is carrying offspring
        pregnancy_timer: Frames until birth
        reproduction_cooldown: Frames until can reproduce again
        species: Fish species identifier
    """

    # Class-level constants for life cycle
    BABY_AGE = 300  # 10 seconds at 30fps
    JUVENILE_AGE = 900  # 30 seconds
    ADULT_AGE = 1800  # 1 minute
    ELDER_AGE = 3600  # 2 minutes
    BASE_MAX_AGE = 5400  # 3 minutes base lifespan

    # Energy constants
    BASE_MAX_ENERGY = 100.0
    ENERGY_FROM_FOOD = 40.0  # More energy from food
    BASE_METABOLISM = 0.015  # Lower metabolism (was 0.02)
    MOVEMENT_ENERGY_COST = 0.005  # Lower movement cost (was 0.01)

    # Reproduction constants
    REPRODUCTION_ENERGY_THRESHOLD = 60.0
    REPRODUCTION_COOLDOWN = 600  # 20 seconds
    PREGNANCY_DURATION = 300  # 10 seconds
    MATING_DISTANCE = 50.0

    def __init__(self, environment: 'environment.Environment', movement_strategy: 'MovementStrategy',
                 filenames: List[str], x: float, y: float, speed: float,
                 genome: Optional[Genome] = None, generation: int = 0,
                 fish_id: Optional[int] = None, ecosystem: Optional['EcosystemManager'] = None) -> None:
        """Initialize a fish with genetics and life systems.

        Args:
            environment: The environment the fish lives in
            movement_strategy: Movement behavior strategy
            filenames: Image filenames for animation
            x: Initial x position
            y: Initial y position
            speed: Base speed
            genome: Genetic traits (random if None)
            generation: Generation number
            fish_id: Unique ID (assigned by ecosystem if None)
            ecosystem: Ecosystem manager for tracking
        """
        # Genetics
        self.genome: Genome = genome if genome is not None else Genome.random()
        self.generation: int = generation
        self.species: str = filenames[0]  # Use first filename as species identifier

        # Life cycle
        self.age: int = 0
        self.max_age: int = int(self.BASE_MAX_AGE * self.genome.max_energy)  # Hardier fish live longer
        self.life_stage: LifeStage = LifeStage.BABY

        # Energy & metabolism
        self.max_energy: float = self.BASE_MAX_ENERGY * self.genome.max_energy
        self.energy: float = self.max_energy  # Start with full energy

        # Reproduction
        self.is_pregnant: bool = False
        self.pregnancy_timer: int = 0
        self.reproduction_cooldown: int = 0
        self.mate_genome: Optional[Genome] = None  # Store mate's genome for offspring

        # ID tracking
        self.ecosystem: Optional['EcosystemManager'] = ecosystem
        if fish_id is None and ecosystem is not None:
            self.fish_id: int = ecosystem.get_next_fish_id()
        else:
            self.fish_id: int = fish_id if fish_id is not None else 0

        # Visual attributes
        self.size: float = 0.5 if self.life_stage == LifeStage.BABY else 1.0
        self.animation_frames = [ImageLoader.load_image(os.path.join('images', filename)) for filename in filenames]
        self.base_width: int = self.animation_frames[0].get_width()
        self.base_height: int = self.animation_frames[0].get_height()
        self.movement_strategy: 'MovementStrategy' = movement_strategy

        # Apply genetic modifiers to speed
        modified_speed = speed * self.genome.speed_modifier

        super().__init__(environment, filenames, x, y, modified_speed)

        # Record birth
        if ecosystem is not None:
            ecosystem.record_birth(self.fish_id, self.generation)

    def get_current_image(self) -> Surface:
        """Get the current image with genetic color tint applied."""
        # Get base image
        if self.vel.x > 0:
            base_image = self.animation_frames[self.image_index]
        else:
            base_image = pygame.transform.flip(self.animation_frames[self.image_index], True, False)

        # Scale based on size and genetics
        scale_factor = self.size * self.genome.size_modifier
        new_width = int(self.base_width * scale_factor)
        new_height = int(self.base_height * scale_factor)
        scaled_image = pygame.transform.scale(base_image, (new_width, new_height))

        # Apply genetic color tint
        color_tint = self.genome.get_color_tint()
        tinted_image = scaled_image.copy()
        tinted_image.fill(color_tint, special_flags=pygame.BLEND_RGB_MULT)

        return tinted_image

    def update_life_stage(self) -> None:
        """Update life stage based on age."""
        if self.age < self.BABY_AGE:
            self.life_stage = LifeStage.BABY
            self.size = 0.5 + 0.5 * (self.age / self.BABY_AGE)  # Grow from 0.5 to 1.0
        elif self.age < self.JUVENILE_AGE:
            self.life_stage = LifeStage.JUVENILE
            self.size = 1.0
        elif self.age < self.ELDER_AGE:
            self.life_stage = LifeStage.ADULT
            self.size = 1.0
        else:
            self.life_stage = LifeStage.ELDER
            self.size = 1.0

    def consume_energy(self, time_modifier: float = 1.0) -> None:
        """Consume energy based on metabolism and activity.

        Args:
            time_modifier: Modifier for time-based effects (e.g., day/night)
        """
        # Base metabolism
        metabolism = self.BASE_METABOLISM * self.genome.metabolism_rate * time_modifier

        # Additional cost for movement
        if self.vel.length() > 0:
            movement_cost = self.MOVEMENT_ENERGY_COST * self.vel.length() / self.speed
            metabolism += movement_cost

        # Life stage modifiers
        if self.life_stage == LifeStage.BABY:
            metabolism *= 0.7  # Babies need less energy
        elif self.life_stage == LifeStage.ELDER:
            metabolism *= 1.2  # Elders need more energy

        self.energy = max(0, self.energy - metabolism)

    def is_starving(self) -> bool:
        """Check if fish is starving (low energy)."""
        return self.energy < 20.0

    def is_dead(self) -> bool:
        """Check if fish should die."""
        return self.energy <= 0 or self.age >= self.max_age

    def get_death_cause(self) -> str:
        """Get the cause of death."""
        if self.energy <= 0:
            return 'starvation'
        elif self.age >= self.max_age:
            return 'old_age'
        return 'unknown'

    def can_reproduce(self) -> bool:
        """Check if fish can reproduce."""
        return (
            self.life_stage == LifeStage.ADULT and
            self.energy >= self.REPRODUCTION_ENERGY_THRESHOLD and
            self.reproduction_cooldown <= 0 and
            not self.is_pregnant
        )

    def try_mate(self, other: 'Fish') -> bool:
        """Attempt to mate with another fish.

        Args:
            other: Potential mate

        Returns:
            True if mating successful
        """
        # Check if both can reproduce and are same species
        if not (self.can_reproduce() and other.can_reproduce()):
            return False

        if self.species != other.species:
            return False

        # Check distance
        distance = (self.pos - other.pos).length()
        if distance > self.MATING_DISTANCE:
            return False

        # Success! Start pregnancy
        self.is_pregnant = True
        self.pregnancy_timer = self.PREGNANCY_DURATION
        self.mate_genome = other.genome
        self.reproduction_cooldown = self.REPRODUCTION_COOLDOWN

        # Other fish also goes on cooldown
        other.reproduction_cooldown = self.REPRODUCTION_COOLDOWN

        # Energy cost for reproduction
        self.energy -= 20.0

        return True

    def update_reproduction(self) -> Optional['Fish']:
        """Update reproduction state and potentially give birth.

        Returns:
            Newborn fish if birth occurred, None otherwise
        """
        # Update cooldown
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1

        # Update pregnancy
        if self.is_pregnant:
            self.pregnancy_timer -= 1

            if self.pregnancy_timer <= 0:
                # Give birth!
                self.is_pregnant = False

                # Create offspring genome
                if self.mate_genome is not None:
                    offspring_genome = Genome.from_parents(self.genome, self.mate_genome)
                else:
                    offspring_genome = Genome.random()

                # Create offspring near parent
                offset_x = random.uniform(-30, 30)
                offset_y = random.uniform(-30, 30)
                baby_x = self.pos.x + offset_x
                baby_y = self.pos.y + offset_y

                # Clamp to screen
                baby_x = max(0, min(SCREEN_WIDTH - 50, baby_x))
                baby_y = max(0, min(SCREEN_HEIGHT - 50, baby_y))

                # Create baby fish
                baby = Fish(
                    environment=self.environment,
                    movement_strategy=self.movement_strategy.__class__(),  # Same strategy type
                    filenames=[self.species],  # Same species
                    x=baby_x,
                    y=baby_y,
                    speed=self.speed / self.genome.speed_modifier,  # Base speed
                    genome=offspring_genome,
                    generation=self.generation + 1,
                    ecosystem=self.ecosystem
                )

                return baby

        return None

    def grow(self) -> None:
        """Increase the size of the fish (deprecated - now handled by life stage)."""
        # Keep for compatibility but size is now based on life stage
        pass

    def update(self, elapsed_time: int, time_modifier: float = 1.0) -> Optional['Fish']:
        """Update the fish state.

        Args:
            elapsed_time: Time elapsed since start
            time_modifier: Time-based modifier (e.g., for day/night)

        Returns:
            Newborn fish if reproduction occurred, None otherwise
        """
        super().update(elapsed_time)

        # Age
        self.age += 1
        self.update_life_stage()

        # Energy
        self.consume_energy(time_modifier)

        # Movement (only if not starving or very young)
        if not self.is_starving() and self.life_stage != LifeStage.BABY:
            self.movement_strategy.move(self)
        else:
            # Slow down when starving or baby
            self.vel *= 0.5

        # Reproduction
        newborn = self.update_reproduction()

        return newborn

    def eat(self, food: 'Food') -> None:
        """Eat food and gain energy.

        Args:
            food: The food being eaten
        """
        energy_gained = self.ENERGY_FROM_FOOD
        self.energy = min(self.max_energy, self.energy + energy_gained)

class Crab(Agent):
    def __init__(self, environment: 'environment.Environment') -> None:
        super().__init__(environment, FILES['crab'], *INIT_POS['crab'], 2)

    def update(self, elapsed_time: int) -> None:
        food_sprites = self.environment.agents_to_align_with(self, 1, Food)
        if food_sprites:
            self.align_near(food_sprites, 1)
        self.vel.y = 0
        super().update(elapsed_time)


def sway(image: Surface, angle: float, sway_range: float, sway_speed: float) -> Surface:
    """Sways (rotates) an image back and forth around a fixed point at the bottom."""
    pivot = image.get_rect().midbottom
    sway_angle = math.sin(angle * sway_speed) * sway_range
    rotated_image = pygame.transform.rotate(image, sway_angle)
    rect = rotated_image.get_rect(midbottom=pivot)

    # Create a new surface to hold the rotated image at the correct position
    result = pygame.Surface(rotated_image.get_size(), pygame.SRCALPHA)
    result.blit(rotated_image, rect.topleft)

    return result

class Plant(Agent):
    """A plant sprite that produces food over time.

    Attributes:
        food_production_timer: Frames until next food production
        food_production_rate: Base frames between food production
        max_food_capacity: Maximum food that can exist from this plant
        current_food_count: Current number of food items from this plant
    """

    BASE_FOOD_PRODUCTION_RATE = 150  # 5 seconds at 30fps (even faster production)
    MAX_FOOD_CAPACITY = 8  # Maximum food items per plant

    def __init__(self, environment: 'environment.Environment', plant_type: int) -> None:
        super().__init__(environment, [FILES['plant'][plant_type-1]], *INIT_POS[f'plant{plant_type}'], 0)
        self.sway_range: float = PLANT_SWAY_RANGE
        self.sway_speed: float = PLANT_SWAY_SPEED
        self.plant_type: int = plant_type

        # Food production
        self.food_production_timer: int = self.BASE_FOOD_PRODUCTION_RATE
        self.food_production_rate: int = self.BASE_FOOD_PRODUCTION_RATE
        self.current_food_count: int = 0

    def update_position(self) -> None:
        """Don't update the position of the plant."""
        pass

    def should_produce_food(self, time_modifier: float = 1.0) -> bool:
        """Check if plant should produce food.

        Args:
            time_modifier: Modifier based on day/night (produce more during day)

        Returns:
            True if food should be produced
        """
        # Update timer
        self.food_production_timer -= time_modifier

        if self.food_production_timer <= 0 and self.current_food_count < self.MAX_FOOD_CAPACITY:
            self.food_production_timer = self.food_production_rate
            return True

        return False

    def produce_food(self) -> 'Food':
        """Produce a food item near the plant.

        Returns:
            New food item
        """
        self.current_food_count += 1

        # Spawn food near plant with slight randomization
        food_x = self.pos.x + random.uniform(-20, 20)
        food_y = self.pos.y - 30  # Spawn above plant

        food = Food(self.environment, food_x, food_y, source_plant=self)

        return food

    def notify_food_eaten(self) -> None:
        """Notify plant that one of its food items was eaten."""
        self.current_food_count = max(0, self.current_food_count - 1)

    def update(self, elapsed_time: int, time_modifier: float = 1.0) -> Optional['Food']:
        """Update the plant.

        Args:
            elapsed_time: Time elapsed since start
            time_modifier: Time-based modifier (higher during day)

        Returns:
            New food item if produced, None otherwise
        """
        super().update(elapsed_time)

        # Sway the plant image back and forth
        self.image = sway(self.image, elapsed_time, self.sway_range, self.sway_speed)

        # Check food production
        if self.should_produce_food(time_modifier):
            return self.produce_food()

        return None

class Castle(Agent):
    """A castle sprite."""
    def __init__(self, environment: 'environment.Environment') -> None:
        super().__init__(environment, FILES['castle'], *INIT_POS['castle'], 0)

class Food(Agent):
    """A food sprite.

    Attributes:
        source_plant: Optional plant that produced this food
    """

    def __init__(self, environment: 'environment.Environment', x: float, y: float,
                 source_plant: Optional['Plant'] = None) -> None:
        super().__init__(environment, FILES['food'], x, y, 0)
        self.source_plant: Optional['Plant'] = source_plant

    def update(self, elapsed_time: int) -> None:
        """Update the sprite."""
        super().update(elapsed_time)
        self.sink()

    def sink(self) -> None:
        """Make the food sink."""
        self.vel.y += FOOD_SINK_ACCELERATION

    def get_eaten(self) -> None:
        """Get eaten and notify source plant if applicable."""
        # Notify plant that food was consumed
        if self.source_plant is not None:
            self.source_plant.notify_food_eaten()

        self.kill()


