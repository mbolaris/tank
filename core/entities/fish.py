"""Fish entity logic and genetics handling."""

import logging
import random
from typing import TYPE_CHECKING, List, Optional, Tuple

from core.constants import (
    DIRECTION_CHANGE_ENERGY_BASE,
    DIRECTION_CHANGE_SIZE_MULTIPLIER,
    ENERGY_MAX_DEFAULT,
    ENERGY_MODERATE_MULTIPLIER,
    FISH_BASE_HEIGHT,
    FISH_BASE_SPEED,
    FISH_BASE_WIDTH,
    FISH_FOOD_MEMORY_DECAY,
    FISH_LAST_EVENT_INITIAL_AGE,
    FISH_MAX_FOOD_MEMORIES,
    FISH_MEMORY_DECAY_RATE,
    FISH_MEMORY_LEARNING_RATE,
    FISH_MEMORY_MAX_PER_TYPE,
    FISH_TOP_MARGIN,
    FRAME_RATE,
    INITIAL_ENERGY_RATIO,
    LIFE_STAGE_MATURE_MAX,
    PREDATOR_ENCOUNTER_WINDOW,
    TARGET_POPULATION,
)
from core.entities.base import Agent, LifeStage
from core.math_utils import Vector2

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.environment import Environment
    from core.genetics import Genome
    from core.movement_strategy import MovementStrategy

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

    def __init__(
        self,
        environment: "Environment",
        movement_strategy: "MovementStrategy",
        species: str,
        x: float,
        y: float,
        speed: float,
        genome: Optional["Genome"] = None,
        generation: int = 0,
        fish_id: Optional[int] = None,
        ecosystem: Optional["EcosystemManager"] = None,
        screen_width: int = 800,
        screen_height: int = 600,
        initial_energy: Optional[float] = None,
        parent_id: Optional[int] = None,
        skip_birth_recording: bool = False,
    ) -> None:
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
        self.genome: Genome = genome if genome is not None else Genome.random()

        # Ensure poker strategy is initialized (self-healing for older saves/migrations)
        if self.genome.poker_strategy_algorithm is None:
            from core.poker.strategy.implementations import get_random_poker_strategy
            self.genome.poker_strategy_algorithm = get_random_poker_strategy()

        self.generation: int = generation
        self.species: str = species

        # Migration flag - set to True when fish migrates to another tank
        self._migrated: bool = False

        # OPTIMIZATION: Cache dead state to avoid repeated is_dead() checks
        # This is checked ~11x per fish per frame in various places
        self._is_dead_cached: bool = False

        # Life cycle - managed by LifecycleComponent for better code organization
        from core.fish.lifecycle_component import LifecycleComponent

        max_age = int(LIFE_STAGE_MATURE_MAX * self.genome.size_modifier)  # Larger fish live longer
        self._lifecycle_component = LifecycleComponent(max_age, self.genome.size_modifier)

        # Energy & metabolism - managed by EnergyComponent for better code organization
        from core.fish.energy_component import EnergyComponent

        # Max energy is based on fish size - bigger fish can store more energy
        # Use the actual lifecycle size (which includes FISH_BABY_SIZE for newborns)
        # not just genome.size_modifier, to match the dynamic max_energy property
        initial_size = self._lifecycle_component.size
        max_energy = ENERGY_MAX_DEFAULT * initial_size
        if initial_energy is not None and initial_energy > max_energy:
            # Respect explicit initial energy requests by raising capacity when needed
            max_energy = initial_energy
        base_metabolism = ENERGY_MODERATE_MULTIPLIER * self.genome.metabolism_rate
        # Use custom initial energy if provided (for reproduction), otherwise use default ratio
        # Store the original unclamped value for accurate energy tracking
        self._initial_energy_transferred: Optional[float] = initial_energy
        if initial_energy is not None:
            self._energy_component = EnergyComponent(
                max_energy, base_metabolism, initial_energy_ratio=0.0
            )
            # Clamp initial energy to max capacity (prevent baby overflow from large parents)
            self._energy_component.energy = min(max_energy, initial_energy)
        else:
            self._energy_component = EnergyComponent(
                max_energy, base_metabolism, INITIAL_ENERGY_RATIO
            )

        # Backward compatibility: expose energy and max_energy as properties
        # This allows existing code to access fish.energy and fish.max_energy directly

        # Predator tracking (for death attribution)
        self.last_predator_encounter_age: int = FISH_LAST_EVENT_INITIAL_AGE

        # Reproduction - managed by ReproductionComponent for better code organization
        from core.fish.reproduction_component import ReproductionComponent

        self._reproduction_component = ReproductionComponent()

        # Backward compatibility: expose reproduction attributes as properties

        # IMPROVEMENT: Memory and learning system (legacy - kept for compatibility)
        self.food_memory: List[Tuple[Vector2, int]] = (
            []
        )  # (position, age_when_found) for food hotspots
        self.last_food_found_age: int = FISH_LAST_EVENT_INITIAL_AGE
        self.successful_food_finds: int = 0  # Track learning success
        self.MAX_FOOD_MEMORIES = FISH_MAX_FOOD_MEMORIES
        self.FOOD_MEMORY_DECAY = FISH_FOOD_MEMORY_DECAY

        # NEW: Enhanced memory system
        from core.fish_memory import FishMemorySystem

        self.memory_system = FishMemorySystem(
            max_memories_per_type=FISH_MEMORY_MAX_PER_TYPE,
            decay_rate=FISH_MEMORY_DECAY_RATE,
            learning_rate=FISH_MEMORY_LEARNING_RATE,
        )

        # NEW: Behavioral learning system (learn from experience within lifetime)
        from core.behavioral_learning import BehavioralLearningSystem

        self.learning_system = BehavioralLearningSystem(self.genome)

        # ID tracking
        self.ecosystem: Optional[EcosystemManager] = ecosystem
        if fish_id is None and ecosystem is not None:
            self.fish_id: int = ecosystem.get_next_fish_id()
        else:
            self.fish_id: int = fish_id if fish_id is not None else 0

        # Visual attributes (for rendering, but stored in entity)
        # Size is now managed by lifecycle component, but keep reference for rendering
        self.base_width: int = FISH_BASE_WIDTH  # Will be updated by sprite adapter
        self.base_height: int = FISH_BASE_HEIGHT
        self.movement_strategy: MovementStrategy = movement_strategy

        # Apply genetic modifiers to speed
        modified_speed = speed * self.genome.speed_modifier

        # Safety cap: Ensure speed doesn't explode due to legacy bugs
        # Max reasonable speed is base * expected_max_modifier (2.0) * safety_margin (1.2)
        max_allowed_speed = FISH_BASE_SPEED * 2.0 * 1.2
        if modified_speed > max_allowed_speed:
            modified_speed = max_allowed_speed

        super().__init__(environment, x, y, modified_speed, screen_width, screen_height)

        # Store parent ID for delayed registration
        self.parent_id = parent_id

        self.last_direction: Optional[Vector2] = (
            self.vel.normalize() if self.vel.length_squared() > 0 else None
        )

        # Visual effects for poker
        self.poker_effect_state: Optional[Dict[str, Any]] = None
        self.poker_effect_timer: int = 0
        self.poker_cooldown: int = 0  # Cooldown between poker games

        # Visual effects for births
        self.birth_effect_timer: int = 0  # Frames remaining for birth visual effect (hearts + particles)

    def register_birth(self) -> None:
        """Register birth stats with the ecosystem.
        
        Must be called explicitly when the fish is successfully added to the simulation.
        This prevents phantom stats for fish that are created but immediately discarded.
        """
        if self.ecosystem is None:
            return
            
        # Get algorithm ID if fish has a behavior algorithm
        algorithm_id = None
        if self.genome.behavior_algorithm is not None:
            from core.algorithms import get_algorithm_index

            algorithm_id = get_algorithm_index(self.genome.behavior_algorithm)

        # Get color as hex string for phylogenetic tree
        r, g, b = self.genome.get_color_tint()
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        
        # Determine parent lineage
        parent_ids = [self.parent_id] if self.parent_id is not None else None
        
        # Record birth in phylogenetic tree and stats
        self.ecosystem.record_birth(
            self.fish_id,
            self.generation,
            parent_ids=parent_ids,
            algorithm_id=algorithm_id,
            color=color_hex,
        )
        
        # Record energy inflow for soup spawns only
        # - Reproduction births are NOT recorded as inflows because the energy came from
        #   the parent (it's an internal transfer within the fish population, not new energy)
        # - "soup_spawn": spontaneous/system-injected fish (true net inflow of new energy)
        if self.parent_id is None:
            self.ecosystem.record_energy_gain("soup_spawn", self.energy)

    def set_poker_effect(self, status: str, amount: float = 0.0, duration: int = 15, target_id: Optional[int] = None, target_type: Optional[str] = None) -> None:
        """Set a visual effect for poker status.

        Args:
            status: 'playing', 'won', 'lost', 'tie'
            amount: Amount won or lost (for display)
            duration: How long to show the effect in frames
            target_id: ID of the opponent/target entity (for drawing arrows)
            target_type: Type of the opponent/target entity ('fish', 'fractal_plant')
        """
        self.poker_effect_state = {
            "status": status,
            "amount": amount,
            "target_id": target_id,
            "target_type": target_type,
        }
        self.poker_effect_timer = duration

    # Energy properties for backward compatibility
    @property
    def energy(self) -> float:
        """Current energy level (read-only property delegating to EnergyComponent)."""
        return self._energy_component.energy

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level (setter for backward compatibility)."""
        self._energy_component.energy = value
        # OPTIMIZATION: Update dead cache if energy drops to/below zero
        if value <= 0:
            self._is_dead_cached = True

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity based on current size (age + genetics).
        
        A fish's max energy grows as they physically grow from baby to adult.
        Baby fish (size ~0.35-0.5) have less capacity than adults (adult size scales with genetic size_modifier which ranges 0.5-2.0).
        """
        from core.constants import ENERGY_MAX_DEFAULT
        return ENERGY_MAX_DEFAULT * self.size

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
    def mate_genome(self) -> Optional["Genome"]:
        """Mate's genome stored for offspring (delegating to ReproductionComponent)."""
        return self._reproduction_component.mate_genome

    @mate_genome.setter
    def mate_genome(self, value: Optional["Genome"]) -> None:
        """Set mate genome (setter for backward compatibility)."""
        self._reproduction_component.mate_genome = value

    # Lifecycle properties for backward compatibility
    @property
    def age(self) -> int:
        """Current age in frames (read-only property delegating to LifecycleComponent)."""
        return self._lifecycle_component.age

    @property
    def max_age(self) -> int:
        """Maximum age/lifespan (read-only property delegating to LifecycleComponent)."""
        return self._lifecycle_component.max_age

    @property
    def life_stage(self) -> LifeStage:
        """Current life stage (read-only property delegating to LifecycleComponent)."""
        return self._lifecycle_component.life_stage

    @property
    def size(self) -> float:
        """Current size multiplier (read-only property delegating to LifecycleComponent)."""
        return self._lifecycle_component.size

    @property
    def bite_size(self) -> float:
        """Calculate the size of a bite this fish can take.

        Bite size scales with fish size.
        """
        # Base bite size is 20.0 energy units
        # Scales with size (larger fish take bigger bites)
        return 20.0 * self.size

    def update_life_stage(self) -> None:
        """Update life stage based on age (delegates to LifecycleComponent)."""
        self._lifecycle_component.update_life_stage()

    def gain_energy(self, amount: float) -> float:
        """Gain energy from consuming food, routing overflow productively.

        Uses the fish's dynamic max_energy (based on current size) rather than
        the static value in EnergyComponent. Any overflow is used for asexual
        reproduction if eligible, otherwise dropped as food.

        Args:
            amount: Amount of energy to gain.

        Returns:
            float: Actual energy gained by the fish (capped by max_energy)
        """
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if new_energy > self.max_energy:
            # We have overflow - route it productively
            overflow = new_energy - self.max_energy
            self._energy_component.energy = self.max_energy
            self._handle_overflow_energy(overflow)
        else:
            self._energy_component.energy = new_energy

        return self._energy_component.energy - old_energy

    def modify_energy(self, amount: float) -> float:
        """Adjust energy by a specified amount, routing overflow productively.

        Positive amounts are capped at max_energy. Any overflow is first used
        to attempt asexual reproduction, then dropped as food if reproduction
        isn't possible. Negative amounts won't go below zero.

        This provides a simple interface for external systems (like poker) to
        modify energy without embedding their logic in the fish.

        Returns:
            float: The actual energy change applied to the fish
        """
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if amount > 0:
            if new_energy > self.max_energy:
                # We have overflow - try to use it productively
                overflow = new_energy - self.max_energy
                self._energy_component.energy = self.max_energy
                self._handle_overflow_energy(overflow)
            else:
                self._energy_component.energy = new_energy
        else:
            # Negative amount - don't go below zero
            final_energy = max(0.0, new_energy)
            self._energy_component.energy = final_energy
            # OPTIMIZATION: Update dead cache if energy drops to zero
            if final_energy <= 0:
                self._is_dead_cached = True

        return self._energy_component.energy - old_energy

    def _handle_overflow_energy(self, overflow: float) -> None:
        """Route overflow energy into reproduction or food drops.

        When a fish gains more energy than it can hold, this method attempts
        to use that overflow productively:
        1. First, try to trigger asexual reproduction if eligible
        2. If reproduction isn't possible, drop the overflow as food

        Args:
            overflow: Amount of energy exceeding max capacity
        """
        if overflow <= 0:
            return

        # Try asexual reproduction first (requires being adult, not pregnant, etc.)
        if self._reproduction_component.can_asexually_reproduce(
            self.life_stage, self.energy, self.max_energy
        ):
            self._reproduction_component.start_asexual_pregnancy()
            # Track reproduction initiation for stats
            if self.ecosystem is not None:
                self.ecosystem.reproduction_manager.record_reproduction_attempt(success=True)
            return

        # Can't reproduce - drop overflow as food to maintain energy conservation
        self._drop_overflow_as_food(overflow)

    def _drop_overflow_as_food(self, overflow: float) -> None:
        """Convert overflow energy into a food drop near the fish.

        Args:
            overflow: Amount of energy to convert to food
        """
        # Only drop food if we have meaningful overflow
        if overflow < 1.0:
            return

        try:
            from core.entities.resources import Food

            # Create food near the fish
            food = Food(
                environment=self.environment,
                x=self.pos.x + random.uniform(-20, 20),
                y=self.pos.y + random.uniform(-20, 20),
                food_type="energy",  # Use energy type for overflow
                screen_width=self.screen_width,
                screen_height=self.screen_height,
            )
            # Set food energy to match overflow
            food.energy = min(overflow, food.max_energy)
            food.max_energy = food.energy

            # Add to environment if possible
            if hasattr(self.environment, "add_entity"):
                self.environment.add_entity(food)

            # Track as ecosystem outflow (fish overflow → food)
            if self.ecosystem is not None:
                self.ecosystem.record_energy_burn("overflow_food", food.energy)
        except Exception:
            # If food creation fails, the energy is simply lost
            # This is acceptable - it's overflow energy anyway
            pass

    def consume_energy(self, time_modifier: float = 1.0) -> None:
        """Consume energy based on metabolism and activity.

        Delegates to EnergyComponent for cleaner code organization.
        Calculates and reports detailed breakdown of energy sinks to the ecosystem.

        Args:
            time_modifier: Modifier for time-based effects (e.g., day/night)
        """
        energy_breakdown = self._energy_component.consume_energy(
            self.vel, self.speed, self.life_stage, time_modifier, self.size
        )

        # OPTIMIZATION: Update dead cache if energy drops to zero
        if self._energy_component.energy <= 0:
            self._is_dead_cached = True

        if self.ecosystem is not None:
            # Report existence cost (size-based baseline)
            self.ecosystem.record_energy_burn("existence", energy_breakdown["existence"])
            
            # Report movement cost
            self.ecosystem.record_energy_burn("movement", energy_breakdown["movement"])

            # Split metabolism into Base vs Traits
            # The 'metabolism' value from component is (BaseRate * TimeMod * StageMod)
            # Genome.metabolism_rate = 1.0 (Base) + Traits
            # So we can split the cost proportionally
            metabolism_total = energy_breakdown["metabolism"]
            rate = self.genome.metabolism_rate
            
            # Avoid division by zero
            if rate > 0:
                # Calculate what fraction of the rate is due to traits (anything above 1.0)
                trait_fraction = max(0.0, (rate - 1.0) / rate)
                trait_cost = metabolism_total * trait_fraction
                base_cost = metabolism_total - trait_cost
            else:
                trait_cost = 0.0
                base_cost = metabolism_total

            self.ecosystem.record_energy_burn("metabolism", base_cost)
            self.ecosystem.record_energy_burn("trait_maintenance", trait_cost)

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
        # Note: successful_food_finds is incremented in eat() for performance tracking

        # Keep only recent memories (FIFO)
        if len(self.food_memory) > self.MAX_FOOD_MEMORIES:
            self.food_memory.pop(0)

    def can_attempt_migration(self) -> bool:
        """Fish can migrate when hitting horizontal tank boundaries."""

        return True

    def _attempt_migration(self, direction: str) -> bool:
        """Attempt to migrate to a connected tank when hitting a boundary.

        Uses dependency injection pattern - delegates to environment's migration
        handler if available. This keeps core entities decoupled from backend.

        Args:
            direction: "left" or "right" - which boundary was hit

        Returns:
            True if migration successful, False if no migration handler or migration failed
        """
        # Check if environment provides migration handler (dependency injection)
        if not hasattr(self.environment, "migration_handler"):
            logger.debug(f"Fish #{self.fish_id}: No migration_handler in environment")
            return False

        migration_handler = self.environment.migration_handler
        if migration_handler is None:
            return False

        # Check if we have a tank_id
        if not hasattr(self.environment, "tank_id") or self.environment.tank_id is None:
            logger.debug(f"Fish #{self.fish_id}: No tank_id in environment")
            return False

        tank_id = self.environment.tank_id

        # Delegate migration logic to the handler (backend implementation)
        try:
            success = migration_handler.attempt_entity_migration(self, direction, tank_id)

            if success:
                # Mark this fish for removal from source tank
                self._migrated = True
                logger.info(f"Fish #{self.fish_id} successfully migrated {direction}")

            return success

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False

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
            (pos, age) for pos, age in self.food_memory if self.age - age < self.FOOD_MEMORY_DECAY
        ]

    def is_dead(self) -> bool:
        """Check if fish should die or has migrated.

        OPTIMIZATION: Uses cached dead state when possible to avoid repeated checks.
        Cache is updated when energy changes or age increments.
        """
        # OPTIMIZATION: Return cached value if already dead
        if self._is_dead_cached:
            return True
        # Check conditions and update cache if now dead
        dead = self._migrated or self.energy <= 0 or self.age >= self.max_age
        if dead:
            self._is_dead_cached = True
        return dead

    def get_death_cause(self) -> str:
        """Get the cause of death.

        Note: Fish that run out of energy after a recent predator encounter
        (within PREDATOR_ENCOUNTER_WINDOW) count as predation deaths.
        Otherwise, energy depletion counts as starvation.
        """
        if self._migrated:
            return "migration"  # Fish migrated to another tank
        if self.energy <= 0:
            # Check if there was a recent predator encounter
            if self.age - self.last_predator_encounter_age <= PREDATOR_ENCOUNTER_WINDOW:
                return "predation"  # Death after conflict
            else:
                return "starvation"  # Death without recent conflict
        elif self.age >= self.max_age:
            return "old_age"
        return "unknown"

    def mark_predator_encounter(self, escaped: bool = False, damage_taken: float = 0.0) -> None:
        """Mark that this fish has encountered a predator.

        This is used to determine death attribution - if the fish dies from
        energy depletion shortly after this encounter, it counts as predation.

        Args:
            escaped: Whether the fish successfully escaped
            damage_taken: Amount of damage/energy lost
        """
        self.last_predator_encounter_age = self.age

        # NEW: Learn from predator encounter
        from core.behavioral_learning import LearningEvent, LearningType

        predator_event = LearningEvent(
            learning_type=LearningType.PREDATOR_AVOIDANCE,
            success=escaped,
            reward=max(0.0, 1.0 - damage_taken / 10.0),  # Higher reward if less damage
            context={"damage": damage_taken},
        )
        self.learning_system.learn_from_event(predator_event)

    def can_reproduce(self) -> bool:
        """Check if fish can reproduce.

        Delegates to ReproductionComponent.

        Returns:
            bool: True if fish can reproduce
        """
        return self._reproduction_component.can_reproduce(self.life_stage, self.energy, self.max_energy)

    def try_mate(self, other: "Fish") -> bool:
        """Attempt to mate with another fish.

        Delegates to ReproductionComponent for cleaner code organization.

        Args:
            other: Potential mate

        Returns:
            True if mating successful
        """
        # Standard mating is disabled; fish only reproduce sexually after poker games.
        return False

    def update_reproduction(self) -> Optional["Fish"]:
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
            target_population = TARGET_POPULATION  # Desired stable population
            population_ratio = fish_count / target_population if target_population > 0 else 1.0

            # Stress is higher when population is below target (inverse relationship)
            if population_ratio < 1.0:
                population_stress = (
                    1.0 - population_ratio
                ) * 0.8  # 0-80% stress from low population

            # Add stress from recent death rate if available
            if hasattr(self.ecosystem, "recent_death_rate"):
                death_rate_stress = min(0.4, self.ecosystem.recent_death_rate)  # Up to 40% stress
                population_stress = min(1.0, population_stress + death_rate_stress)

        # Capture reproduction type before it's reset in give_birth
        is_asexual = self._reproduction_component._asexual_pregnancy

        # Generate offspring genome using reproduction component
        offspring_genome, _unused_fraction = self._reproduction_component.give_birth(
            self.genome, population_stress
        )

        # Calculate baby's max energy capacity (babies start at FISH_BABY_SIZE)
        # This determines exactly how much energy the parent should transfer
        from core.constants import FISH_BABY_SIZE
        baby_max_energy = ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * offspring_genome.size_modifier
        
        # Parent transfers exactly what baby needs to start at 100% energy
        # But can't transfer more than parent has!
        energy_to_transfer = min(self.energy, baby_max_energy)
        
        # If parent can't afford to give baby 100%, the baby will start with less
        # (This is fine - survival of the fittest)
        self.energy -= energy_to_transfer  # Parent pays the energy cost

        # Record reproduction energy for visibility in stats
        # While it's an internal transfer (parent→baby), showing it helps users
        # understand population dynamics and where energy goes during births.
        if self.ecosystem is not None:
            self.ecosystem.record_reproduction_energy(energy_to_transfer, energy_to_transfer)

        # Create offspring near parent
        offset_x = random.uniform(-30, 30)
        offset_y = random.uniform(-30, 30)
        baby_x = self.pos.x + offset_x
        baby_y = self.pos.y + offset_y

        # Clamp to screen
        baby_x = max(0, min(self.screen_width - 50, baby_x))
        baby_y = max(0, min(self.screen_height - 50, baby_y))

        # Create baby fish with transferred energy
        # Baby gets exactly the energy transferred from parent
        baby = Fish(
            environment=self.environment,
            movement_strategy=self.movement_strategy.__class__(),  # Same strategy type
            species=self.species,  # Same species
            x=baby_x,
            y=baby_y,
            speed=FISH_BASE_SPEED,  # Base speed
            genome=offspring_genome,
            generation=self.generation + 1,
            ecosystem=self.ecosystem,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            initial_energy=energy_to_transfer,  # Baby gets transferred energy
            parent_id=self.fish_id,  # Track lineage for phylogenetic tree
        )

        # Record reproduction stats
        if self.ecosystem is not None and self.genome.behavior_algorithm is not None:
            from core.algorithms import get_algorithm_index

            algorithm_id = get_algorithm_index(self.genome.behavior_algorithm)
            if algorithm_id >= 0:
                self.ecosystem.record_reproduction(algorithm_id, is_asexual=is_asexual)

        # Inherit skill game strategies from parent with mutation
        # If parent has strategies, inherit them; otherwise baby will get default when playing
        from core.fish.skill_game_component import SkillGameComponent
        baby._skill_game_component = SkillGameComponent()
        if hasattr(self, "_skill_game_component") and self._skill_game_component is not None:
            # Parent has strategies - inherit with mutation
            baby._skill_game_component.inherit_from_parent(
                self._skill_game_component,
                mutation_rate=0.1,
            )
        # If parent has no strategies, baby gets empty component and will
        # receive default strategies when first playing (via _ensure_fish_has_strategy)

        # Set visual birth effect timer (60 frames = 2 seconds at 30fps)
        self.birth_effect_timer = 60

        return baby

    def handle_screen_edges(self) -> None:
        """Handle the fish hitting the edge of the screen with top margin for energy bar visibility.

        For connected tanks, attempts migration when hitting left/right boundaries.
        """
        # Horizontal boundaries - check for migration first, then bounce
        if self.pos.x < 0:
            if self._attempt_migration("left"):
                return  # Migration successful, fish removed from this tank
            self.pos.x = 0
            self.vel.x = abs(self.vel.x)  # Bounce right
        elif self.pos.x + self.width > self.screen_width:
            if self._attempt_migration("right"):
                return  # Migration successful, fish removed from this tank
            self.pos.x = self.screen_width - self.width
            self.vel.x = -abs(self.vel.x)  # Bounce left

        # Vertical boundaries with top margin for energy bar visibility
        if self.pos.y < FISH_TOP_MARGIN:
            self.pos.y = FISH_TOP_MARGIN
            self.vel.y = abs(self.vel.y)  # Bounce down
        elif self.pos.y + self.height > self.screen_height:
            self.pos.y = self.screen_height - self.height
            self.vel.y = -abs(self.vel.y)  # Bounce up

    def update(self, elapsed_time: int, time_modifier: float = 1.0) -> Optional["Fish"]:
        """Update the fish state.

        Args:
            elapsed_time: Time elapsed since start
            time_modifier: Time-based modifier (e.g., for day/night)

        Returns:
            Newborn fish if reproduction occurred, None otherwise

        Performance optimizations:
        - Inline simple operations
        - Batch infrequent operations (memory cleanup, learning decay)
        - Cache frequently accessed properties
        """
        super().update(elapsed_time)

        # Age - managed by LifecycleComponent
        self._lifecycle_component.increment_age()
        age = self._lifecycle_component.age  # Cache for use below

        # Performance: Update enhanced memory system less frequently (every 10 frames)
        if age % 10 == 0:
            # Update enhanced memory system less frequently
            self.memory_system.update(age)

            # Apply learning decay less frequently
            self.learning_system.apply_decay()

        # Performance: Clean old food memories less frequently (every 2 seconds instead of 1)
        if age % (FRAME_RATE * 2) == 0:
            self.clean_old_memories()

        # Energy
        self.consume_energy(time_modifier)

        previous_direction = self.last_direction

        # Movement (algorithms handle critical energy internally)
        # Calculate acceleration for diagnostics
        prev_vel = Vector2(self.vel.x, self.vel.y)
        self.movement_strategy.move(self)
        
        # Diagnostic: Record velocity and acceleration
        from core.diagnostics import VelocityTracker
        current_speed = self.vel.length()
        acceleration = (self.vel - prev_vel).length()
        VelocityTracker().record_movement(self.fish_id, self.vel, acceleration)

        self._apply_turn_energy_cost(previous_direction)

        # Reproduction
        newborn = self.update_reproduction()

        # Update poker visual effects
        if self.poker_effect_timer > 0:
            self.poker_effect_timer -= 1
            if self.poker_effect_timer <= 0:
                self.poker_effect_state = None

        # Update birth visual effects
        if self.birth_effect_timer > 0:
            self.birth_effect_timer -= 1

        # Update poker cooldown
        if self.poker_cooldown > 0:
            self.poker_cooldown -= 1

        return newborn

    def eat(self, food: "Food") -> None:
        """Eat food and gain energy.

        Delegates energy gain to EnergyComponent for cleaner code organization.
        Now supports partial consumption (taking bites).

        Args:
            food: The food being eaten

        Performance optimizations:
        - Learning events only created every 5th food eaten
        - Cached algorithm_id lookup
        """
        # Calculate how much room we have for more energy
        available_capacity = self.max_energy - self.energy
        
        # Don't eat if we're already full (prevents wasting food)
        if available_capacity <= 0.1:
            return
        
        # Limit bite size to what we can actually use
        effective_bite_size = min(self.bite_size, available_capacity)
        
        # Take a bite from the food (only what we can hold)
        potential_energy = food.take_bite(effective_bite_size)
        actual_energy = self.gain_energy(potential_energy)

        # IMPROVEMENT: Remember this food location for future reference
        self.remember_food_location(food.pos)

        # Performance: Only create learning events occasionally (every 5 foods eaten)
        # This significantly reduces object allocation overhead
        self.successful_food_finds += 1
        if self.successful_food_finds % 5 == 0:
            from core.behavioral_learning import LearningEvent, LearningType

            food_event = LearningEvent(
                learning_type=LearningType.FOOD_FINDING,
                success=True,
                reward=actual_energy / 10.0,  # Normalize reward based on ACTUAL energy
                context={},
            )
            self.learning_system.learn_from_event(food_event)

        # Record food consumption for algorithm performance tracking
        # Performance: Cache algorithm_id check
        ecosystem = self.ecosystem
        behavior_algorithm = self.genome.behavior_algorithm
        if ecosystem is not None and behavior_algorithm is not None:
            from core.algorithms import get_algorithm_index
            from core.entities.fractal_plant import PlantNectar
            from core.entities.resources import LiveFood

            algorithm_id = get_algorithm_index(behavior_algorithm)
            if algorithm_id >= 0:
                # Determine food type and call appropriate tracking method
                # Use actual_energy to prevent "phantom" stats
                if isinstance(food, PlantNectar):
                    ecosystem.record_nectar_eaten(algorithm_id, actual_energy)
                elif isinstance(food, LiveFood):
                    ecosystem.record_live_food_eaten(
                        algorithm_id, actual_energy, self.genome, self.generation
                    )
                else:
                    ecosystem.record_falling_food_eaten(algorithm_id, actual_energy)

    def _apply_turn_energy_cost(self, previous_direction: Optional[Vector2]) -> None:
        """Apply an energy penalty for direction changes, scaled by turn angle and fish size.

        The energy cost increases with:
        - Sharper turns (more angle change)
        - Larger fish size (bigger fish use more energy to turn)
        """
        if self.vel.length_squared() == 0:
            self.last_direction = None
            return

        new_direction = self.vel.normalize()

        if previous_direction is not None:
            # Calculate dot product (-1 = 180° turn, 0 = 90° turn, 1 = no turn)
            dot_product = previous_direction.dot(new_direction)

            # Convert to turn intensity (0 = no turn, 1 = slight turn, 2 = 180° turn)
            # Formula: (1 - dot_product) gives us 0 to 2 range
            turn_intensity = 1 - dot_product

            # Only apply cost if there's a noticeable direction change
            if turn_intensity > 0.1:  # Threshold to ignore tiny wobbles
                # Base energy cost scaled by turn intensity and fish size
                # Larger fish (size > 1.0) pay more, smaller fish (size < 1.0) pay less
                size_factor = self.size ** DIRECTION_CHANGE_SIZE_MULTIPLIER
                energy_cost = DIRECTION_CHANGE_ENERGY_BASE * turn_intensity * size_factor

                self.energy = max(0, self.energy - energy_cost)

                if self.ecosystem is not None:
                    self.ecosystem.record_energy_burn("turning", energy_cost)

        self.last_direction = new_direction


