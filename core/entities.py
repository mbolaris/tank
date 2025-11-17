"""Pure entity classes without pygame dependencies.

This module contains the core simulation logic for all entities in the fish tank.
No pygame-specific code is included - all rendering is handled separately.
"""

from typing import List, TYPE_CHECKING, Optional, Tuple
import random
import math
from enum import Enum

# Use a simple Vector2 class or import from pygame.math (we'll create a pure version)
from core.math_utils import Vector2
from core.constants import (
    INITIAL_ENERGY_RATIO, BABY_METABOLISM_MULTIPLIER,
    ELDER_METABOLISM_MULTIPLIER, STARVATION_THRESHOLD,
    CRITICAL_ENERGY_THRESHOLD, LOW_ENERGY_THRESHOLD, SAFE_ENERGY_THRESHOLD,
    FISH_TOP_MARGIN
)

if TYPE_CHECKING:
    from core.environment import Environment
    from core.movement_strategy import MovementStrategy
    from core.ecosystem import EcosystemManager
    from core.genetics import Genome


class LifeStage(Enum):
    """Life stages of a fish."""
    BABY = "baby"
    JUVENILE = "juvenile"
    ADULT = "adult"
    ELDER = "elder"


class Agent:
    """Base class for all entities in the simulation (pure logic, no rendering)."""

    def __init__(self, environment: 'Environment', x: float, y: float, speed: float,
                 screen_width: int = 800, screen_height: int = 600) -> None:
        """Initialize an agent.

        Args:
            environment: The environment the agent lives in
            x: Initial x position
            y: Initial y position
            speed: Base speed
            screen_width: Width of the simulation area
            screen_height: Height of the simulation area
        """
        self.speed: float = speed
        self.vel: Vector2 = Vector2(speed, 0)
        self.pos: Vector2 = Vector2(x, y)
        self.avoidance_velocity: Vector2 = Vector2(0, 0)
        self.environment: 'Environment' = environment
        self.screen_width: int = screen_width
        self.screen_height: int = screen_height

        # Bounding box for collision detection (will be updated by size)
        self.width: float = 50.0  # Default size
        self.height: float = 50.0

    def get_rect(self) -> Tuple[float, float, float, float]:
        """Get bounding rectangle (x, y, width, height) for collision detection."""
        return (self.pos.x, self.pos.y, self.width, self.height)

    def set_size(self, width: float, height: float) -> None:
        """Set the size of the agent's bounding box."""
        self.width = width
        self.height = height

    def update_position(self) -> None:
        """Update the position of the agent."""
        effective_velocity = self.vel + self.avoidance_velocity
        self.pos += effective_velocity
        self.handle_screen_edges()

    def handle_screen_edges(self) -> None:
        """Handle the agent hitting the edge of the screen."""
        # Horizontal boundaries - reverse velocity and clamp position
        if self.pos.x < 0:
            self.pos.x = 0
            self.vel.x = abs(self.vel.x)  # Bounce right
        elif self.pos.x + self.width > self.screen_width:
            self.pos.x = self.screen_width - self.width
            self.vel.x = -abs(self.vel.x)  # Bounce left

        # Vertical boundaries - reverse velocity and clamp position
        if self.pos.y < 0:
            self.pos.y = 0
            self.vel.y = abs(self.vel.y)  # Bounce down
        elif self.pos.y + self.height > self.screen_height:
            self.pos.y = self.screen_height - self.height
            self.vel.y = -abs(self.vel.y)  # Bounce up

    def update(self, elapsed_time: int) -> None:
        """Update the agent state (pure logic, no rendering)."""
        self.update_position()

    def add_random_velocity_change(self, probabilities: List[float], divisor: float) -> None:
        """Add a random direction change to the agent."""
        random_x_direction = random.choices([-1, 0, 1], probabilities)[0]
        random_y_direction = random.choices([-1, 0, 1], probabilities)[0]
        self.vel.x += random_x_direction / divisor
        self.vel.y += random_y_direction / divisor

    def avoid(self, other_sprites: List['Agent'], min_distance: float) -> None:
        """Avoid other agents."""
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
                    self.avoidance_velocity -= velocity_change * 0.15  # AVOIDANCE_SPEED_CHANGE

        # Only reset avoidance_velocity when no sprites are close
        if not any_sprite_close:
            self.avoidance_velocity = Vector2(0, 0)

    def align_near(self, other_sprites: List['Agent'], min_distance: float) -> None:
        """Align with nearby agents."""
        if not other_sprites:
            return
        avg_pos = self.get_average_position(other_sprites)
        self.adjust_velocity_towards_or_away_from_other_sprites(other_sprites, avg_pos, min_distance)
        if self.vel.x != 0 or self.vel.y != 0:  # Checking if it's a zero vector
            self.vel = self.vel.normalize() * abs(self.speed)

    def get_average_position(self, other_sprites: List['Agent']) -> Vector2:
        """Calculate the average position of other agents."""
        return sum((other.pos for other in other_sprites), Vector2()) / len(other_sprites)

    def adjust_velocity_towards_or_away_from_other_sprites(self, other_sprites: List['Agent'],
                                                           avg_pos: Vector2, min_distance: float) -> None:
        """Adjust velocity based on the position of other agents."""
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
        """Adjust velocity to move away from another agent."""
        dist_length = dist_vector.length()
        if dist_length > 0:
            self.vel -= dist_vector.normalize() * 0.15  # AVOIDANCE_SPEED_CHANGE

    def move_towards(self, difference: Vector2) -> None:
        """Adjust velocity to move towards the average position of other agents."""
        diff_length = difference.length()
        if diff_length > 0:
            self.vel += difference.normalize() * 0.1  # ALIGNMENT_SPEED_CHANGE


class Fish(Agent):
    """A fish entity with genetics, energy, and life cycle (pure logic, no rendering).

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

    # Energy constants (DIFFICULTY INCREASED - survival is more challenging)
    BASE_MAX_ENERGY = 100.0
    ENERGY_FROM_FOOD = 1.0  # Energy from food is determined by food type in constants.py
    EXISTENCE_ENERGY_COST = 0.01  # Reduced for better survival and evolution
    BASE_METABOLISM = 0.025  # Reduced from 0.045 to allow fish to maintain energy
    MOVEMENT_ENERGY_COST = 0.015  # Reduced from 0.025 to make movement less punishing
    SHARP_TURN_DOT_THRESHOLD = -0.85  # Threshold for detecting near-180 degree turns
    SHARP_TURN_ENERGY_COST = 0.05  # Reduced from 0.08 for less harsh turning cost

    # Predator encounter tracking
    PREDATOR_ENCOUNTER_WINDOW = 150  # 5 seconds - recent conflict window for death attribution

    # Reproduction constants (OPTIMIZED FOR SUSTAINABLE BREEDING)
    REPRODUCTION_ENERGY_THRESHOLD = 35.0  # Lowered to 35 for better reproduction rates
    REPRODUCTION_COOLDOWN = 360  # 12 seconds (reduced from 15s to increase breeding opportunities)
    PREGNANCY_DURATION = 300  # 10 seconds
    MATING_DISTANCE = 60.0  # Increased from 50 to make mating easier

    def __init__(self, environment: 'Environment', movement_strategy: 'MovementStrategy',
                 species: str, x: float, y: float, speed: float,
                 genome: Optional['Genome'] = None, generation: int = 0,
                 fish_id: Optional[int] = None, ecosystem: Optional['EcosystemManager'] = None,
                 screen_width: int = 800, screen_height: int = 600,
                 initial_energy: Optional[float] = None) -> None:
        """Initialize a fish with genetics and life systems.

        Args:
            environment: The environment the fish lives in
            movement_strategy: Movement behavior strategy
            species: Species identifier (e.g., 'fish1.png')
            x: Initial x position
            y: Initial y position
            speed: Base speed
            genome: Genetic traits (random if None)
            generation: Generation number
            fish_id: Unique ID (assigned by ecosystem if None)
            ecosystem: Ecosystem manager for tracking
            screen_width: Width of simulation area
            screen_height: Height of simulation area
            initial_energy: Override initial energy (for reproduction energy transfer)
        """
        # Import here to avoid circular dependency
        from core.genetics import Genome

        # Genetics
        self.genome: 'Genome' = genome if genome is not None else Genome.random()
        self.generation: int = generation
        self.species: str = species

        # Life cycle
        self.age: int = 0
        self.max_age: int = int(self.BASE_MAX_AGE * self.genome.max_energy)  # Hardier fish live longer
        self.life_stage: LifeStage = LifeStage.BABY

        # Energy & metabolism - managed by EnergyComponent for better code organization
        from core.fish.energy_component import EnergyComponent
        max_energy = self.BASE_MAX_ENERGY * self.genome.max_energy
        base_metabolism = self.BASE_METABOLISM * self.genome.metabolism_rate
        # Use custom initial energy if provided (for reproduction), otherwise use default ratio
        if initial_energy is not None:
            self._energy_component = EnergyComponent(max_energy, base_metabolism, initial_energy_ratio=0.0)
            self._energy_component.energy = initial_energy
        else:
            self._energy_component = EnergyComponent(max_energy, base_metabolism, INITIAL_ENERGY_RATIO)

        # Backward compatibility: expose energy and max_energy as properties
        # This allows existing code to access fish.energy and fish.max_energy directly

        # Predator tracking (for death attribution)
        self.last_predator_encounter_age: int = -1000  # Age when last encountered a predator

        # Reproduction - managed by ReproductionComponent for better code organization
        from core.fish.reproduction_component import ReproductionComponent
        self._reproduction_component = ReproductionComponent()

        # Backward compatibility: expose reproduction attributes as properties

        # IMPROVEMENT: Memory and learning system (legacy - kept for compatibility)
        self.food_memory: List[Tuple[Vector2, int]] = []  # (position, age_when_found) for food hotspots
        self.last_food_found_age: int = -1000  # Age when last found food
        self.successful_food_finds: int = 0  # Track learning success
        self.MAX_FOOD_MEMORIES = 5  # Remember up to 5 good food locations
        self.FOOD_MEMORY_DECAY = 600  # Forget food locations after 20 seconds

        # NEW: Enhanced memory system
        from core.fish_memory import FishMemorySystem
        self.memory_system = FishMemorySystem(
            max_memories_per_type=10,
            decay_rate=0.001,
            learning_rate=0.05
        )

        # ID tracking
        self.ecosystem: Optional['EcosystemManager'] = ecosystem
        if fish_id is None and ecosystem is not None:
            self.fish_id: int = ecosystem.get_next_fish_id()
        else:
            self.fish_id: int = fish_id if fish_id is not None else 0

        # Visual attributes (for rendering, but stored in entity)
        self.size: float = 0.5 if self.life_stage == LifeStage.BABY else 1.0
        self.base_width: int = 50  # Will be updated by sprite adapter
        self.base_height: int = 50
        self.movement_strategy: 'MovementStrategy' = movement_strategy

        # Apply genetic modifiers to speed
        modified_speed = speed * self.genome.speed_modifier

        super().__init__(environment, x, y, modified_speed, screen_width, screen_height)

        # Record birth
        if ecosystem is not None:
            # Get algorithm ID if fish has a behavior algorithm
            algorithm_id = None
            if self.genome.behavior_algorithm is not None:
                from core.behavior_algorithms import get_algorithm_index
                algorithm_id = get_algorithm_index(self.genome.behavior_algorithm)
            ecosystem.record_birth(self.fish_id, self.generation, algorithm_id=algorithm_id)

        self.last_direction: Optional[Vector2] = (self.vel.normalize()
                                                  if self.vel.length_squared() > 0 else None)

    # Energy properties for backward compatibility
    @property
    def energy(self) -> float:
        """Current energy level (read-only property delegating to EnergyComponent)."""
        return self._energy_component.energy

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level (setter for backward compatibility)."""
        self._energy_component.energy = value

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity (read-only property delegating to EnergyComponent)."""
        return self._energy_component.max_energy

    # Reproduction properties for backward compatibility
    @property
    def is_pregnant(self) -> bool:
        """Whether fish is currently pregnant (delegating to ReproductionComponent)."""
        return self._reproduction_component.is_pregnant

    @is_pregnant.setter
    def is_pregnant(self, value: bool) -> None:
        """Set pregnancy state (setter for backward compatibility)."""
        self._reproduction_component.is_pregnant = value

    @property
    def pregnancy_timer(self) -> int:
        """Frames until birth (delegating to ReproductionComponent)."""
        return self._reproduction_component.pregnancy_timer

    @pregnancy_timer.setter
    def pregnancy_timer(self, value: int) -> None:
        """Set pregnancy timer (setter for backward compatibility)."""
        self._reproduction_component.pregnancy_timer = value

    @property
    def reproduction_cooldown(self) -> int:
        """Frames until can reproduce again (delegating to ReproductionComponent)."""
        return self._reproduction_component.reproduction_cooldown

    @reproduction_cooldown.setter
    def reproduction_cooldown(self, value: int) -> None:
        """Set reproduction cooldown (setter for backward compatibility)."""
        self._reproduction_component.reproduction_cooldown = value

    @property
    def mate_genome(self) -> Optional['Genome']:
        """Mate's genome stored for offspring (delegating to ReproductionComponent)."""
        return self._reproduction_component.mate_genome

    @mate_genome.setter
    def mate_genome(self, value: Optional['Genome']) -> None:
        """Set mate genome (setter for backward compatibility)."""
        self._reproduction_component.mate_genome = value

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

        Delegates to EnergyComponent for cleaner code organization.

        Args:
            time_modifier: Modifier for time-based effects (e.g., day/night)
        """
        self._energy_component.consume_energy(self.vel, self.speed, self.life_stage, time_modifier)

    def is_starving(self) -> bool:
        """Check if fish is starving (low energy).

        Delegates to EnergyComponent.

        Returns:
            bool: True if energy is below starvation threshold
        """
        return self._energy_component.is_starving()

    def is_critical_energy(self) -> bool:
        """Check if fish is in critical energy state (emergency survival mode).

        Delegates to EnergyComponent.

        Returns:
            bool: True if energy is critically low
        """
        return self._energy_component.is_critical_energy()

    def is_low_energy(self) -> bool:
        """Check if fish has low energy (should prioritize food).

        Delegates to EnergyComponent.

        Returns:
            bool: True if energy is low
        """
        return self._energy_component.is_low_energy()

    def is_safe_energy(self) -> bool:
        """Check if fish has safe energy level (can explore/breed).

        Delegates to EnergyComponent.

        Returns:
            bool: True if energy is at a safe level
        """
        return self._energy_component.is_safe_energy()

    def get_energy_ratio(self) -> float:
        """Get energy as a ratio of max energy (0.0-1.0).

        Delegates to EnergyComponent.

        Returns:
            float: Energy ratio between 0.0 and 1.0
        """
        return self._energy_component.get_energy_ratio()

    def remember_food_location(self, position: Vector2) -> None:
        """Remember a food location for future reference.

        Args:
            position: Position where food was found
        """
        # Add to memory
        self.food_memory.append((position, self.age))
        self.last_food_found_age = self.age
        self.successful_food_finds += 1

        # Keep only recent memories (FIFO)
        if len(self.food_memory) > self.MAX_FOOD_MEMORIES:
            self.food_memory.pop(0)

    def get_remembered_food_locations(self) -> List[Vector2]:
        """Get list of remembered food locations (excluding expired memories).

        Returns:
            List of Vector2 positions where food was previously found
        """
        current_memories = []
        for position, found_age in self.food_memory:
            # Only keep memories that haven't decayed
            if self.age - found_age < self.FOOD_MEMORY_DECAY:
                current_memories.append(position)

        return current_memories

    def clean_old_memories(self) -> None:
        """Remove expired food memories."""
        self.food_memory = [
            (pos, age) for pos, age in self.food_memory
            if self.age - age < self.FOOD_MEMORY_DECAY
        ]

    def is_dead(self) -> bool:
        """Check if fish should die."""
        return self.energy <= 0 or self.age >= self.max_age

    def get_death_cause(self) -> str:
        """Get the cause of death.

        Note: Fish that run out of energy after a recent predator encounter
        (within PREDATOR_ENCOUNTER_WINDOW) count as predation deaths.
        Otherwise, energy depletion counts as starvation.
        """
        if self.energy <= 0:
            # Check if there was a recent predator encounter
            if self.age - self.last_predator_encounter_age <= self.PREDATOR_ENCOUNTER_WINDOW:
                return 'predation'  # Death after conflict
            else:
                return 'starvation'  # Death without recent conflict
        elif self.age >= self.max_age:
            return 'old_age'
        return 'unknown'

    def mark_predator_encounter(self) -> None:
        """Mark that this fish has encountered a predator.

        This is used to determine death attribution - if the fish dies from
        energy depletion shortly after this encounter, it counts as predation.
        """
        self.last_predator_encounter_age = self.age

    def can_reproduce(self) -> bool:
        """Check if fish can reproduce.

        Delegates to ReproductionComponent.

        Returns:
            bool: True if fish can reproduce
        """
        return self._reproduction_component.can_reproduce(self.life_stage, self.energy)

    def should_offer_post_poker_reproduction(self, opponent: 'Fish', is_winner: bool,
                                            energy_gained: float = 0.0) -> bool:
        """Decide whether to offer reproduction after a poker game.

        This implements voluntary sexual reproduction where fish can choose to
        reproduce with poker opponents based on multiple factors.

        Args:
            opponent: The fish we just played poker with
            is_winner: True if this fish won the poker game
            energy_gained: Energy won/lost in poker (positive for winners)

        Returns:
            bool: True if fish wants to offer reproduction
        """
        from core.constants import (
            POST_POKER_REPRODUCTION_ENERGY_THRESHOLD,
            POST_POKER_REPRODUCTION_WINNER_PROB,
            POST_POKER_REPRODUCTION_LOSER_PROB,
        )

        # Must have enough energy
        if self.energy < POST_POKER_REPRODUCTION_ENERGY_THRESHOLD:
            return False

        # Can't reproduce if pregnant or on cooldown
        if self.is_pregnant or self.reproduction_cooldown > 0:
            return False

        # Must be adult
        if self.life_stage.value < LifeStage.ADULT.value:
            return False

        # Must be same species
        if self.species != opponent.species:
            return False

        # Calculate opponent's fitness appeal
        opponent_fitness = 0.0
        if opponent.genome is not None:
            # Consider opponent's fitness score
            opponent_fitness += min(opponent.genome.fitness_score / 100.0, 1.0) * 0.3

            # Consider opponent's energy level (healthy mates are attractive)
            energy_ratio = opponent.energy / opponent.max_energy if opponent.max_energy > 0 else 0
            opponent_fitness += energy_ratio * 0.2

            # Consider genetic compatibility
            if self.genome is not None:
                compatibility = self.genome.calculate_mate_compatibility(opponent.genome)
                opponent_fitness += compatibility * 0.3

            # Winners are more attractive (they proved their fitness)
            if not is_winner:  # If we lost, opponent won
                opponent_fitness += 0.2

        # Base probability depends on whether we won or lost
        base_prob = POST_POKER_REPRODUCTION_WINNER_PROB if is_winner else POST_POKER_REPRODUCTION_LOSER_PROB

        # Modify probability based on opponent's fitness
        final_prob = base_prob * (0.5 + opponent_fitness)

        # Random decision
        return random.random() < final_prob

    def try_mate(self, other: 'Fish') -> bool:
        """Attempt to mate with another fish.

        Delegates to ReproductionComponent for cleaner code organization.

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

        # Calculate distance to mate
        distance = (self.pos - other.pos).length()

        # Attempt mating through reproduction component
        mating_successful = self._reproduction_component.attempt_mating(
            self.genome, other.genome,
            self.energy, self.max_energy,
            other.energy, other.max_energy,
            distance
        )

        if not mating_successful:
            return False

        # Other fish also goes on cooldown
        other.reproduction_cooldown = self._reproduction_component.REPRODUCTION_COOLDOWN

        # Energy cost for reproduction (reduced to prevent post-mating starvation)
        self.energy -= self._reproduction_component.REPRODUCTION_ENERGY_COST

        # Record successful reproduction in ecosystem
        if self.ecosystem is not None and self.genome.behavior_algorithm is not None:
            from core.behavior_algorithms import get_algorithm_index
            algorithm_id = get_algorithm_index(self.genome.behavior_algorithm)
            if algorithm_id >= 0:
                self.ecosystem.record_reproduction(algorithm_id)

        return True

    def update_reproduction(self) -> Optional['Fish']:
        """Update reproduction state and potentially give birth.

        Delegates state updates to ReproductionComponent for cleaner code organization.

        Returns:
            Newborn fish if birth occurred, None otherwise
        """
        # Update reproduction state (cooldown and pregnancy timer)
        should_give_birth = self._reproduction_component.update_state()

        if not should_give_birth:
            return None

        # Calculate population stress for adaptive mutations
        population_stress = 0.0
        if self.ecosystem is not None:
            # Stress increases when population is low or death rate is high
            fish_count = len([e for e in self.environment.agents if isinstance(e, Fish)])
            target_population = 15  # Desired stable population
            population_ratio = fish_count / target_population if target_population > 0 else 1.0

            # Stress is higher when population is below target (inverse relationship)
            if population_ratio < 1.0:
                population_stress = (1.0 - population_ratio) * 0.8  # 0-80% stress from low population

            # Add stress from recent death rate if available
            if hasattr(self.ecosystem, 'recent_death_rate'):
                death_rate_stress = min(0.4, self.ecosystem.recent_death_rate)  # Up to 40% stress
                population_stress = min(1.0, population_stress + death_rate_stress)

        # Generate offspring genome using reproduction component
        offspring_genome, energy_transfer_fraction = self._reproduction_component.give_birth(
            self.genome, population_stress
        )

        # Calculate energy to transfer to baby (parent loses this energy)
        energy_to_transfer = self.energy * energy_transfer_fraction
        self.energy -= energy_to_transfer  # Parent pays the energy cost

        # Create offspring near parent
        offset_x = random.uniform(-30, 30)
        offset_y = random.uniform(-30, 30)
        baby_x = self.pos.x + offset_x
        baby_y = self.pos.y + offset_y

        # Clamp to screen
        baby_x = max(0, min(self.screen_width - 50, baby_x))
        baby_y = max(0, min(self.screen_height - 50, baby_y))

        # Create baby fish with transferred energy
        # Baby gets ONLY the energy transferred from parent (no free energy!)
        baby = Fish(
            environment=self.environment,
            movement_strategy=self.movement_strategy.__class__(),  # Same strategy type
            species=self.species,  # Same species
            x=baby_x,
            y=baby_y,
            speed=self.speed / self.genome.speed_modifier,  # Base speed
            genome=offspring_genome,
            generation=self.generation + 1,
            ecosystem=self.ecosystem,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            initial_energy=energy_to_transfer  # Baby gets only transferred energy
        )

        return baby

    def handle_screen_edges(self) -> None:
        """Handle the fish hitting the edge of the screen with top margin for energy bar visibility."""
        # Horizontal boundaries - reverse velocity and clamp position
        if self.pos.x < 0:
            self.pos.x = 0
            self.vel.x = abs(self.vel.x)  # Bounce right
        elif self.pos.x + self.width > self.screen_width:
            self.pos.x = self.screen_width - self.width
            self.vel.x = -abs(self.vel.x)  # Bounce left

        # Vertical boundaries with top margin for energy bar visibility
        if self.pos.y < FISH_TOP_MARGIN:
            self.pos.y = FISH_TOP_MARGIN
            self.vel.y = abs(self.vel.y)  # Bounce down
        elif self.pos.y + self.height > self.screen_height:
            self.pos.y = self.screen_height - self.height
            self.vel.y = -abs(self.vel.y)  # Bounce up

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

        # NEW: Update fitness for survival
        energy_ratio = self.energy / self.max_energy
        self.genome.update_fitness(
            survived_frames=1,
            energy_ratio=energy_ratio
        )

        # NEW: Update enhanced memory system
        self.memory_system.update(self.age)

        # IMPROVEMENT: Clean old food memories every second
        if self.age % 30 == 0:  # Every second at 30fps
            self.clean_old_memories()

        # Poker cooldown
        if hasattr(self, 'poker_cooldown') and self.poker_cooldown > 0:
            self.poker_cooldown -= 1

        # Energy
        self.consume_energy(time_modifier)

        previous_direction = self.last_direction

        # Movement (only if not starving or very young)
        if not self.is_starving() and self.life_stage != LifeStage.BABY:
            self.movement_strategy.move(self)
        else:
            # Slow down when starving or baby
            self.vel *= 0.5

        self._apply_turn_energy_cost(previous_direction)

        # Reproduction
        newborn = self.update_reproduction()

        # NEW: Track reproduction in fitness
        if newborn is not None:
            self.genome.update_fitness(reproductions=1)

        return newborn

    def eat(self, food: 'Food') -> None:
        """Eat food and gain energy.

        Delegates energy gain to EnergyComponent for cleaner code organization.

        Args:
            food: The food being eaten
        """
        energy_gained = food.get_energy_value()
        self._energy_component.gain_energy(energy_gained)

        # NEW: Track food consumption in fitness
        self.genome.update_fitness(food_eaten=1)

        # IMPROVEMENT: Remember this food location for future reference
        self.remember_food_location(food.pos)

        # Record food consumption for algorithm performance tracking
        if self.ecosystem is not None and self.genome.behavior_algorithm is not None:
            from core.behavior_algorithms import get_algorithm_index
            algorithm_id = get_algorithm_index(self.genome.behavior_algorithm)
            if algorithm_id >= 0:
                self.ecosystem.record_food_eaten(algorithm_id)

    def _apply_turn_energy_cost(self, previous_direction: Optional[Vector2]) -> None:
        """Apply an energy penalty for sharp 180-degree turns."""
        if self.vel.length_squared() == 0:
            self.last_direction = None
            return

        new_direction = self.vel.normalize()

        if (previous_direction is not None and
                previous_direction.dot(new_direction) <= self.SHARP_TURN_DOT_THRESHOLD):
            self.energy = max(0, self.energy - self.SHARP_TURN_ENERGY_COST)

        self.last_direction = new_direction


class Crab(Agent):
    """A predator crab that hunts fish and food (pure logic, no rendering).

    Attributes:
        genome: Genetic traits for the crab (speed, aggression, etc.)
        energy: Current energy level
        max_energy: Maximum energy capacity
        hunt_cooldown: Frames until can hunt again
    """

    BASE_MAX_ENERGY = 150.0
    ENERGY_FROM_FISH = 60.0  # Substantial energy from catching fish
    ENERGY_FROM_FOOD = 20.0
    BASE_METABOLISM = 0.01  # Slower metabolism than fish
    HUNT_COOLDOWN = 120  # 4 seconds between kills - more aggressive predation

    def __init__(self, environment: 'Environment', genome: Optional['Genome'] = None,
                 x: float = 100, y: float = 550, screen_width: int = 800, screen_height: int = 600) -> None:
        """Initialize a crab.

        Args:
            environment: The environment the crab lives in
            genome: Genetic traits (random if None)
            x: Initial x position
            y: Initial y position
            screen_width: Width of simulation area
            screen_height: Height of simulation area
        """
        # Import here to avoid circular dependency
        from core.genetics import Genome

        # Crabs are slower and less aggressive now
        self.genome: 'Genome' = genome if genome is not None else Genome.random()
        base_speed = 1.5  # Much slower than before (was 2)
        speed = base_speed * self.genome.speed_modifier

        super().__init__(environment, x, y, speed, screen_width, screen_height)

        # Energy system
        self.max_energy: float = self.BASE_MAX_ENERGY * self.genome.max_energy
        self.energy: float = self.max_energy

        # Hunting mechanics
        self.hunt_cooldown: int = 0

    def can_hunt(self) -> bool:
        """Check if crab can hunt (cooldown expired)."""
        return self.hunt_cooldown <= 0

    def consume_energy(self) -> None:
        """Consume energy based on metabolism."""
        metabolism = self.BASE_METABOLISM * self.genome.metabolism_rate
        self.energy = max(0, self.energy - metabolism)

    def eat_fish(self, fish: Fish) -> None:
        """Eat a fish and gain energy."""
        self.energy = min(self.max_energy, self.energy + self.ENERGY_FROM_FISH)
        self.hunt_cooldown = self.HUNT_COOLDOWN

    def eat_food(self, food: 'Food') -> None:
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
        food_sprites = self.environment.agents_to_align_with(self, 100, Food)  # Increased radius for food seeking
        if food_sprites:
            self.align_near(food_sprites, 1)
        else:
            # Only hunt fish if no food available and can hunt
            if self.can_hunt() and self.energy < self.max_energy * 0.7:  # Only hunt when hungry
                fish_sprites = self.environment.agents_to_align_with(self, 80, Fish)  # Reduced hunting radius
                if fish_sprites:
                    # Move toward nearest fish slowly
                    self.align_near(fish_sprites, 1)

        # Stay on bottom
        self.vel.y = 0
        super().update(elapsed_time)


class Plant(Agent):
    """A plant entity that produces food over time (pure logic, no rendering).

    Attributes:
        food_production_timer: Frames until next food production
        food_production_rate: Base frames between food production
        max_food_capacity: Maximum food that can exist from this plant
        current_food_count: Current number of food items from this plant
    """

    BASE_FOOD_PRODUCTION_RATE = 75  # 2.5 seconds at 30fps - Increased for sustainable population
    MAX_FOOD_CAPACITY = 15  # Maximum food items per plant - Increased for better food availability
    STATIONARY_FOOD_CHANCE = 0.35  # Increased from 0.25 to grow more stationary nectar
    STATIONARY_FOOD_TYPE = 'nectar'

    def __init__(self, environment: 'Environment', plant_type: int,
                 x: float = 100, y: float = 400, screen_width: int = 800, screen_height: int = 600) -> None:
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
        self.food_production_timer: int = self.BASE_FOOD_PRODUCTION_RATE
        self.food_production_rate: int = self.BASE_FOOD_PRODUCTION_RATE
        self.current_food_count: int = 0

    def update_position(self) -> None:
        """Don't update the position of the plant (stationary)."""
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
        """Produce a food item near or on the plant.

        Returns:
            New food item
        """
        self.current_food_count += 1

        if random.random() < self.STATIONARY_FOOD_CHANCE:
            # Grow nectar that clings to the top of the plant
            food = Food(
                self.environment,
                self.pos.x + self.width / 2,  # Center of plant
                self.pos.y,  # Top of plant
                source_plant=self,
                food_type=self.STATIONARY_FOOD_TYPE,
                screen_width=self.screen_width,
                screen_height=self.screen_height
            )
            anchor_x = self.pos.x + self.width / 2 - food.width / 2
            anchor_y = self.pos.y - food.height
            food.pos.update(anchor_x, anchor_y)
            return food

        # All other food falls from top of tank
        food_x = random.randint(0, self.screen_width)
        food_y = 0  # Top of tank

        return Food(self.environment, food_x, food_y, source_plant=self,
                   screen_width=self.screen_width, screen_height=self.screen_height)

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

        # Check food production
        if self.should_produce_food(time_modifier):
            return self.produce_food()

        return None


class Castle(Agent):
    """A castle entity (decorative, pure logic)."""

    def __init__(self, environment: 'Environment', x: float = 375, y: float = 475,
                 screen_width: int = 800, screen_height: int = 600) -> None:
        """Initialize a castle.

        Args:
            environment: The environment the castle lives in
            x: Initial x position
            y: Initial y position
            screen_width: Width of simulation area
            screen_height: Height of simulation area
        """
        super().__init__(environment, x, y, 0, screen_width, screen_height)


class Food(Agent):
    """A food entity with variable nutrients (pure logic, no rendering).

    Attributes:
        source_plant: Optional plant that produced this food
        food_type: Type of food (algae, protein, vitamin, energy, rare, nectar)
        food_properties: Dictionary containing energy and other properties
    """

    # Food type definitions (copied from constants.py for now)
    FOOD_TYPES = {
        'algae': {'energy': 25.0, 'rarity': 0.40, 'sink_multiplier': 1.0, 'stationary': False},
        'protein': {'energy': 45.0, 'rarity': 0.25, 'sink_multiplier': 1.5, 'stationary': False},
        'vitamin': {'energy': 35.0, 'rarity': 0.20, 'sink_multiplier': 0.8, 'stationary': False},
        'energy': {'energy': 60.0, 'rarity': 0.10, 'sink_multiplier': 1.2, 'stationary': False},
        'rare': {'energy': 100.0, 'rarity': 0.05, 'sink_multiplier': 0.5, 'stationary': False},
        'nectar': {'energy': 30.0, 'rarity': 0.0, 'sink_multiplier': 0.0, 'stationary': True},
    }

    def __init__(self, environment: 'Environment', x: float, y: float,
                 source_plant: Optional['Plant'] = None, food_type: Optional[str] = None,
                 allow_stationary_types: bool = True, screen_width: int = 800, screen_height: int = 600) -> None:
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
            food_type = self._select_random_food_type(include_stationary=allow_stationary_types)

        self.food_type = food_type
        self.food_properties = self.FOOD_TYPES[food_type]
        self.is_stationary: bool = self.food_properties.get('stationary', False)

        super().__init__(environment, x, y, 0, screen_width, screen_height)
        self.source_plant: Optional['Plant'] = source_plant

    @staticmethod
    def _select_random_food_type(include_stationary: bool = True) -> str:
        """Select a random food type based on rarity weights."""
        food_types = [
            ft for ft, props in Food.FOOD_TYPES.items()
            if include_stationary or not props.get('stationary', False)
        ]
        weights = [Food.FOOD_TYPES[ft]['rarity'] for ft in food_types]
        return random.choices(food_types, weights=weights)[0]

    def get_energy_value(self) -> float:
        """Get the energy value this food provides."""
        return self.food_properties['energy']

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
        sink_rate = 0.05 * self.food_properties['sink_multiplier']  # FOOD_SINK_ACCELERATION
        self.vel.y += sink_rate

    def get_eaten(self) -> None:
        """Get eaten and notify source plant if applicable."""
        # Notify plant that food was consumed
        if self.source_plant is not None:
            self.source_plant.notify_food_eaten()
