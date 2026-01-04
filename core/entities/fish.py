import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from core.config.fish import (
    DIRECTION_CHANGE_ENERGY_BASE,
    DIRECTION_CHANGE_SIZE_MULTIPLIER,
    ENERGY_MAX_DEFAULT,
    ENERGY_MODERATE_MULTIPLIER,
    FISH_BASE_HEIGHT,
    FISH_BASE_SPEED,
    FISH_BASE_WIDTH,
    FISH_LAST_EVENT_INITIAL_AGE,
    FISH_MEMORY_DECAY_RATE,
    FISH_MEMORY_LEARNING_RATE,
    FISH_MEMORY_MAX_PER_TYPE,
    FISH_TOP_MARGIN,
    INITIAL_ENERGY_RATIO,
    LIFE_STAGE_MATURE_MAX,
    PREDATOR_ENCOUNTER_WINDOW,
)
from core.entities.base import Agent, EntityState, LifeStage
from core.entities.visual_state import FishVisualState
from core.entity_ids import FishId
from core.math_utils import Vector2
from core.constants import (
    BURN_REASON_EXISTENCE,
    BURN_REASON_METABOLISM,
    BURN_REASON_MOVEMENT,
    BURN_REASON_OVERFLOW_FOOD,
    BURN_REASON_TRAIT_MAINTENANCE,
    DEATH_REASON_MIGRATION,
    DEATH_REASON_OLD_AGE,
    DEATH_REASON_STARVATION,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.movement_strategy import MovementStrategy
    from core.world import World

# Runtime imports (moved from local scopes)

from core.config.fish import OVERFLOW_ENERGY_BANK_MULTIPLIER
from core.fish.energy_component import EnergyComponent
from core.fish.energy_state import EnergyState
from core.fish.lifecycle_component import LifecycleComponent
from core.fish.reproduction_component import ReproductionComponent
from core.fish.skill_game_component import SkillGameComponent
from core.fish_memory import FishMemorySystem, MemoryType
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from core.sim.energy_ledger import EnergyDelta
from core.sim.events import AteFood, EnergyBurned
from core.skills.base import SkillGameResult, SkillGameType, SkillStrategy
from core.telemetry.events import (
    BirthEvent,
    EnergyBurnEvent,
    FoodEatenEvent,
    ReproductionEvent,
)


class Fish(Agent):
    """A fish entity with genetics, energy, and life cycle (pure logic, no rendering).

    Attributes:
        genome: Genetic traits
        energy: Current energy level (EnergyHolder protocol)
        max_energy: Maximum energy capacity (EnergyHolder protocol)
        generation: Generation number
        fish_id: Unique identifier
        species: Fish species identifier
    """

    def __init__(
        self,
        environment: "World",
        movement_strategy: "MovementStrategy",
        species: str,
        x: float,
        y: float,
        speed: float,
        genome: Optional["Genome"] = None,
        generation: int = 0,
        fish_id: Optional[int] = None,
        ecosystem: Optional["EcosystemManager"] = None,
        initial_energy: Optional[float] = None,
        parent_id: Optional[int] = None,
        skip_birth_recording: bool = False,
    ) -> None:
        """Initialize a fish with genetics and life systems.

        Args:
            environment: The world the fish lives in
            movement_strategy: Movement behavior strategy
            species: Species identifier (e.g., 'fish1.png')
            x: Initial x position
            y: Initial y position
            speed: Base speed
            genome: Genetic traits (random if None)
            generation: Generation number
            fish_id: Unique ID (assigned by ecosystem if None)
            ecosystem: Ecosystem manager for tracking
            initial_energy: Override initial energy (for reproduction energy transfer)
        """
        from core.util.rng import require_rng

        if genome is not None:
            self.genome = genome
        else:
            # Use require_rng for deterministic genome creation (fails loudly if unavailable)
            rng = require_rng(environment, "Fish.__init__.genome")
            self.genome = Genome.random(rng=rng)

        # Ensure poker strategy is initialized (self-healing for older saves/migrations)
        if (
            self.genome.behavioral.poker_strategy is None
            or self.genome.behavioral.poker_strategy.value is None
        ):
            from core.poker.strategy.implementations import get_random_poker_strategy

            rng = require_rng(environment, "Fish.__init__.poker_strategy")
            strategy = get_random_poker_strategy(rng=rng)

            if self.genome.behavioral.poker_strategy is None:
                self.genome.behavioral.poker_strategy = GeneticTrait(strategy)
            else:
                self.genome.behavioral.poker_strategy.value = strategy

        self.generation: int = generation
        self.species: str = species

        # OPTIMIZATION: Cache for is_dead() result to avoid repeated checks
        # This is checked ~11x per fish per frame in various places
        self._cached_is_dead: bool = False

        # OPTIMIZATION: Cache bounds to avoid fetching from environment every frame
        self._cached_bounds: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None

        # Life cycle - managed by LifecycleComponent for better code organization

        # Calculate max_age using size_modifier and lifespan_modifier.
        # This decouples size from age, allowing small but long-lived fish.
        lifespan_mult = 1.0
        if hasattr(self.genome.physical, "lifespan_modifier"):
            lifespan_mult = self.genome.physical.lifespan_modifier.value

        size_modifier = self.genome.physical.size_modifier.value
        max_age = int(LIFE_STAGE_MATURE_MAX * size_modifier * lifespan_mult)
        self._lifecycle_component = LifecycleComponent(max_age, size_modifier)

        # Energy & metabolism - managed by EnergyComponent for better code organization

        # Max energy is based on fish size - bigger fish can store more energy
        # Use the actual lifecycle size (which includes FISH_BABY_SIZE for newborns)
        # not just genome.physical.size_modifier, to match the dynamic max_energy property
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

        # Predator tracking (for death attribution)
        self.last_predator_encounter_age: int = FISH_LAST_EVENT_INITIAL_AGE

        # Reproduction - managed by ReproductionComponent for better code organization

        self._reproduction_component = ReproductionComponent()

        # NEW: Enhanced memory system

        self.memory_system = FishMemorySystem(
            max_memories_per_type=FISH_MEMORY_MAX_PER_TYPE,
            decay_rate=FISH_MEMORY_DECAY_RATE,
            learning_rate=FISH_MEMORY_LEARNING_RATE,
        )

        # NEW: Skill game component (manages strategies and stats for skill games)
        self._skill_game_component = SkillGameComponent()

        # ID tracking
        self.ecosystem: Optional[EcosystemManager] = ecosystem
        if fish_id is None and ecosystem is not None:
            self.fish_id: int = ecosystem.generate_new_fish_id()
        else:
            self.fish_id: int = fish_id if fish_id is not None else 0

        # Type-safe ID wrapper (cached to avoid repeated object creation)
        self._typed_id: Optional[FishId] = None

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

        super().__init__(environment, x, y, modified_speed)

        # Store parent ID for delayed registration
        self.parent_id = parent_id

        self.last_direction: Optional[Vector2] = (
            self.vel.normalize() if self.vel.length_squared() > 0 else None
        )

        # Rendering-only state is stored separately to keep domain logic lean.
        self.visual_state = FishVisualState()
        self.poker_cooldown: int = 0  # Cooldown between poker games

        # Optional: Override movement policy (if set, used instead of genome behavior)
        self._movement_policy: Optional[Any] = None

    @property
    def movement_policy(self) -> Optional[Any]:
        """Get the override movement policy, if any."""
        return self._movement_policy

    @movement_policy.setter
    def movement_policy(self, policy: Optional[Any]) -> None:
        """Set an override movement policy.

        If set, this policy will be used instead of the genome-based behavior.
        Set to None to return to default genome behavior.
        """
        self._movement_policy = policy

    @property
    def typed_id(self) -> FishId:
        """Get the type-safe fish ID.

        This wraps the raw fish_id in a FishId type for type safety.
        The wrapper is cached to avoid repeated object creation.

        Returns:
            FishId wrapper around fish_id
        """
        if self._typed_id is None or self._typed_id.value != self.fish_id:
            self._typed_id = FishId(self.fish_id)
        return self._typed_id

    def get_energy_state(self) -> EnergyState:
        """Get immutable snapshot of current energy state."""
        return EnergyState(
            current_energy=self.energy,
            max_energy=self._energy_component.max_energy,
        )

    # =========================================================================
    # PokerPlayer Protocol Implementation
    # =========================================================================

    def get_poker_aggression(self) -> float:
        """Get poker aggression level (implements PokerPlayer protocol).

        Returns:
            Aggression value for poker decisions (0.0-1.0)
        """
        if hasattr(self.genome.behavioral, "aggression"):
            return self.genome.behavioral.aggression.value
        return 0.5

    def get_poker_strategy(self):
        """Get poker strategy for this fish (implements PokerPlayer protocol).

        Returns:
            PokerStrategyAlgorithm from genome, or None for aggression-based play
        """
        trait = getattr(self.genome.behavioral, "poker_strategy", None)
        return trait.value if trait else None

    def get_poker_id(self) -> int:
        """Get stable ID for poker tracking (implements PokerPlayer protocol).

        Returns:
            fish_id for consistent identification
        """
        return self.fish_id

    # =========================================================================
    # SkillfulAgent Protocol Implementation
    # =========================================================================

    def get_strategy(self, game_type: SkillGameType) -> Optional[SkillStrategy]:
        """Get the fish's strategy for a specific skill game (implements SkillfulAgent Protocol).

        Args:
            game_type: The type of skill game

        Returns:
            The fish's strategy for that game, or None if not initialized
        """
        return self._skill_game_component.get_strategy(game_type)

    def set_strategy(self, game_type: SkillGameType, strategy: SkillStrategy) -> None:
        """Set the fish's strategy for a specific skill game (implements SkillfulAgent Protocol).

        Args:
            game_type: The type of skill game
            strategy: The strategy to use for that game
        """
        self._skill_game_component.set_strategy(game_type, strategy)

    def learn_from_game(self, game_type: SkillGameType, result: SkillGameResult) -> None:
        """Update strategy based on game outcome (implements SkillfulAgent Protocol).

        This is how fish learn within their lifetime. The strategy is updated
        based on the result (win/loss/tie) and optimality of play.

        Args:
            game_type: The type of skill game that was played
            result: The outcome of the game
        """
        self._skill_game_component.record_game_result(game_type, result)

    @property
    def can_play_skill_games(self) -> bool:
        """Whether this fish is currently able to play skill games (implements SkillfulAgent Protocol).

        Returns:
            True if fish is adult, has sufficient energy, and isn't on cooldown
        """
        if self._lifecycle_component.life_stage not in (LifeStage.ADULT, LifeStage.ELDER):
            return False

        from core.poker_interaction import MIN_ENERGY_TO_PLAY

        return self.energy >= MIN_ENERGY_TO_PLAY and self.poker_cooldown <= 0 and not self.is_dead()

    # =========================================================================
    # EnergyHolder Protocol Implementation
    # =========================================================================

    @property
    def energy(self) -> float:
        """Current energy level (read-only property delegating to EnergyComponent)."""
        return self._energy_component.energy

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level."""
        self._energy_component.energy = value
        # OPTIMIZATION: Update dead cache if energy drops to/below zero
        if value <= 0:
            if self.state.state == EntityState.ACTIVE:
                self.state.transition(EntityState.DEAD, reason=DEATH_REASON_STARVATION)
            self._cached_is_dead = True

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity based on current size (age + genetics).

        A fish's max energy grows as they physically grow from baby to adult.
        Baby fish (size ~0.35-0.5) have less capacity than adults.
        """
        return ENERGY_MAX_DEFAULT * self._lifecycle_component.size

    @property
    def bite_size(self) -> float:
        """Calculate the size of a bite this fish can take.

        Bite size scales with fish size.
        """
        return 20.0 * self._lifecycle_component.size

    def apply_energy_delta(self, delta: EnergyDelta) -> None:
        """Apply an energy delta from the EnergyLedger."""
        if delta.reason == "ate_food":
            # Delegate to internal logic which handles overflow banking
            self._apply_energy_gain_internal(delta.delta)
        elif delta.reason in (
            "movement",
            "metabolism",
            "existence",
            "trait_maintenance",
            "poker_game",
        ):
            # Direct modification for consumption/loss
            self.modify_energy(delta.delta)
        else:
            # Fallback
            self.modify_energy(delta.delta)

    def gain_energy(self, amount: float) -> float:
        """Gain energy from consuming food.

        Emits AteFood event. Energy is applied later via apply_energy_delta.
        Returns the amount requested to satisfy legacy callers (like Food)
        that need to know how much was taken.
        """
        # Emit domain event for Ledger
        # Note: We need food info for the event.
        # But this method signature only has `amount`.
        # The caller usually knows the context.
        # Ideally caller emits the event.
        # But for "Mission: Pick 2-3 high-value energy paths", we are putting it here.
        # We'll use a generic "unknown" food type if locally missing,
        # but AteFood requires food_type.
        # We might need to guess or change method signature.
        # Existing callers: Food.be_eaten_by calls this.

        # We will assume generic food for now or use a default.
        # Ideally, we refactor `Food.be_eaten_by` to emit the event, but that's outside "Fish" scope.
        # Let's emit a specific event if we can't context.
        # Actually, let's keep it simple:
        # We emit AteFood with essential info.

        behavior_id = None
        if self.genome.behavioral.behavior and self.genome.behavioral.behavior.value:
            behavior_id = hash(self.genome.behavioral.behavior.value.behavior_id) % 1000

        self._emit_event(
            AteFood(
                entity_id=self.fish_id,
                food_id=0,  # Unknown here
                food_type="unknown",
                energy_gained=amount,
                algorithm_id=behavior_id,
            )
        )

        # Return amount so Food dies immediately (preserving game logic)
        return amount

    def _apply_energy_gain_internal(self, amount: float) -> float:
        """Internal logic to apply energy gain and route overflow."""
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if new_energy > self.max_energy:
            overflow = new_energy - self.max_energy
            self._energy_component.energy = self.max_energy
            self._route_overflow_energy(overflow)
        else:
            self._energy_component.energy = new_energy

        # Ensure fish is marked alive if it has energy and state is active
        if self._energy_component.energy > 0 and self.state.state == EntityState.ACTIVE:
            self._cached_is_dead = False

        return self._energy_component.energy - old_energy

    def modify_energy(self, amount: float) -> float:
        """Adjust energy by a specified amount, routing overflow productively.

        Positive amounts are capped at max_energy with overflow handling.
        Negative amounts won't go below zero.

        Returns:
            float: The actual energy change applied to the fish
        """
        old_energy = self._energy_component.energy
        new_energy = old_energy + amount

        if amount > 0:
            if new_energy > self.max_energy:
                overflow = new_energy - self.max_energy
                self._energy_component.energy = self.max_energy
                self._route_overflow_energy(overflow)
            else:
                self._energy_component.energy = new_energy
        else:
            final_energy = max(0.0, new_energy)
            self._energy_component.energy = final_energy
            if final_energy <= 0:
                if self.state.state == EntityState.ACTIVE:
                    self.state.transition(EntityState.DEAD, reason=DEATH_REASON_STARVATION)
                self._cached_is_dead = True
            elif self.state.state == EntityState.ACTIVE:
                self._cached_is_dead = False

        return self._energy_component.energy - old_energy

    def _route_overflow_energy(self, overflow: float) -> None:
        """Route overflow energy into reproduction bank.

        When a fish gains more energy than it can hold, this method banks
        the overflow for future reproduction. If the bank is full, excess
        is dropped as food.

        Args:
            overflow: Amount of energy exceeding max capacity
        """
        if overflow <= 0:
            return

        max_bank = self.max_energy * OVERFLOW_ENERGY_BANK_MULTIPLIER
        banked = self._reproduction_component.bank_overflow_energy(overflow, max_bank=max_bank)
        remainder = overflow - banked

        if remainder > 0:
            self._spawn_overflow_food(remainder)

    def _spawn_overflow_food(self, overflow: float) -> None:
        """Convert overflow energy into a food drop near the fish.

        Args:
            overflow: Amount of energy to convert to food
        """
        if overflow < 1.0:
            return

        try:
            from core.entities.resources import Food
            from core.util.mutations import request_spawn_in
            from core.util.rng import require_rng

            rng = require_rng(self.environment, "Fish._spawn_overflow_food")
            food = Food(
                environment=self.environment,
                x=self.pos.x + rng.uniform(-20, 20),
                y=self.pos.y + rng.uniform(-20, 20),
                food_type="energy",
            )
            food.energy = min(overflow, food.max_energy)
            food.max_energy = food.energy

            if not request_spawn_in(self.environment, food, reason="overflow_food"):
                logger.warning("spawn requester unavailable, overflow food lost")

            self._emit_event(
                EnergyBurned(
                    entity_id=self.fish_id, amount=food.energy, reason=BURN_REASON_OVERFLOW_FOOD
                )
            )
        except Exception:
            pass  # Energy lost on failure is acceptable

    def consume_energy(self, time_modifier: float = 1.0) -> None:
        """Consume energy based on metabolism and activity.

        Calculates burn and emits events. Energy is reduced later via apply_energy_delta.
        """
        energy_breakdown = self._energy_component.consume_energy(
            self.vel,
            self.speed,
            self._lifecycle_component.life_stage,
            time_modifier,
            self._lifecycle_component.size,
        )

        # Emit new Ledger events
        self._emit_event(
            EnergyBurned(
                entity_id=self.fish_id,
                amount=energy_breakdown["existence"],
                reason=BURN_REASON_EXISTENCE,
            )
        )

        self._emit_event(
            EnergyBurned(
                entity_id=self.fish_id,
                amount=energy_breakdown["movement"],
                reason=BURN_REASON_MOVEMENT,
            )
        )

        # Calculate trait cost for telemetry/ledger
        metabolism_total = energy_breakdown["metabolism"]
        rate = self.genome.metabolism_rate
        if rate > 0:
            trait_fraction = max(0.0, (rate - 1.0) / rate)
            trait_cost = metabolism_total * trait_fraction
            base_cost = metabolism_total - trait_cost
        else:
            trait_cost = 0.0
            base_cost = metabolism_total

        self._emit_event(
            EnergyBurned(entity_id=self.fish_id, amount=base_cost, reason=BURN_REASON_METABOLISM)
        )

        self._emit_event(
            EnergyBurned(
                entity_id=self.fish_id, amount=trait_cost, reason=BURN_REASON_TRAIT_MAINTENANCE
            )
        )

    def is_starving(self) -> bool:
        return self._energy_component.is_starving()

    def is_critical_energy(self) -> bool:
        return self._energy_component.is_critical_energy()

    def is_low_energy(self) -> bool:
        return self._energy_component.is_low_energy()

    def is_safe_energy(self) -> bool:
        return self._energy_component.is_safe_energy()

    def get_energy_ratio(self) -> float:
        """Get energy as a ratio of max energy (0.0-1.0)."""
        max_e = self.max_energy
        return self.energy / max_e if max_e > 0 else 0.0

    def register_birth(self) -> None:
        """Register birth stats with the ecosystem.

        Must be called explicitly when the fish is successfully added to the simulation.
        This prevents phantom stats for fish that are created but immediately discarded.
        """
        if self.ecosystem is None:
            return

        # Get behavior ID from behavior for tracking
        algorithm_id = None
        algorithm_name = None
        behavior = self.genome.behavioral.behavior
        if behavior is not None and behavior.value is not None:
            # Use a hash of the behavior_id for backwards compatibility with integer tracking
            # The ecosystem stats system expects an integer algorithm_id
            behavior_id = behavior.value.behavior_id
            algorithm_id = hash(behavior_id) % 1000  # Keep it in a reasonable range
            # Extract algorithm name from behavior_id for lineage display
            # behavior_id format is typically "ComposableBehavior(algo1, algo2, ...)"
            # We want a clean display name
            algorithm_name = self._extract_algorithm_name(behavior_id)

        # Get color as hex string for phylogenetic tree
        r, g, b = self.genome.get_color_tint()
        color_hex = f"#{r:02x}{g:02x}{b:02x}"

        # Determine parent lineage
        parent_ids = [self.parent_id] if self.parent_id is not None else None

        # Get tank name from environment if available
        tank_name = getattr(self.environment, "tank_name", None)

        # Emit birth telemetry (includes soup spawn energy for true inflow).
        self._emit_event(
            BirthEvent(
                fish_id=self.fish_id,
                generation=self.generation,
                parent_ids=parent_ids,
                algorithm_id=algorithm_id,
                color_hex=color_hex,
                energy=self.energy,
                is_soup_spawn=self.parent_id is None,
                algorithm_name=algorithm_name,
                tank_name=tank_name,
            )
        )

    def _extract_algorithm_name(self, behavior_id: str) -> str:
        """Extract a short, readable algorithm name from a behavior_id string.

        Args:
            behavior_id: The behavior ID string, e.g. "flee-seek-schooling-opportunistic"

        Returns:
            Short display name, e.g. "Flee/Seek"
        """
        if not behavior_id:
            return "Unknown"

        # Handle hyphen-separated format: "flee-seek-schooling-opportunistic"
        if "-" in behavior_id:
            parts = behavior_id.split("-")
            # Take first 2 components, capitalize them
            short_parts = [p.capitalize() for p in parts[:2]]
            return "/".join(short_parts)

        # Handle ComposableBehavior format: "ComposableBehavior(AlgoName, ...)"
        if "ComposableBehavior(" in behavior_id:
            start = behavior_id.find("(")
            end = behavior_id.rfind(")")
            if start != -1 and end != -1 and end > start:
                inner = behavior_id[start + 1 : end]
                parts = inner.split(",")
                if parts:
                    return parts[0].strip()[:15]  # Max 15 chars

        # Handle simple class names
        if "." in behavior_id:
            return behavior_id.split(".")[-1][:15]  # Max 15 chars

        # Return truncated if too long
        return behavior_id[:15] if len(behavior_id) > 15 else behavior_id

    def set_poker_effect(
        self,
        status: str,
        amount: float = 0.0,
        duration: int = 15,
        target_id: Optional[int] = None,
        target_type: Optional[str] = None,
    ) -> None:
        """Set a visual effect for poker status.

        Args:
            status: 'playing', 'won', 'lost', 'tie'
            amount: Amount won or lost (for display)
            duration: How long to show the effect in frames
            target_id: ID of the opponent/target entity (for drawing arrows)
            target_type: Type of the opponent/target entity ('fish', 'plant')
        """
        self.visual_state.set_poker_effect(status, amount, duration, target_id, target_type)

    def set_death_effect(self, cause: str, duration: int = 45) -> None:
        """Set a visual effect for death cause.

        Args:
            cause: 'starvation', 'old_age', 'predation', 'migration', 'unknown'
            duration: How long to show the effect in frames (default 1.5s at 30fps)
        """
        self.visual_state.set_death_effect(cause, duration)

    def can_attempt_migration(self) -> bool:
        """Fish can migrate when hitting horizontal tank boundaries."""

        return True

    def _attempt_migration(self, direction: str) -> bool:
        """Attempt to migrate to a connected tank when hitting a boundary.

        Uses the MigrationCapable protocol to check if migration is supported.
        This keeps core entities decoupled from backend implementation.

        Args:
            direction: "left" or "right" - which boundary was hit

        Returns:
            True if migration successful, False if not supported or failed
        """
        from core.interfaces import MigrationCapable

        # Check if environment supports migration using Protocol
        if not isinstance(self.environment, MigrationCapable):
            return False

        migration_handler = self.environment.migration_handler
        if migration_handler is None:
            return False

        tank_id = self.environment.tank_id
        if tank_id is None:
            return False

        # Delegate migration logic to the handler (backend implementation)
        try:
            success = migration_handler.attempt_entity_migration(self, direction, tank_id)

            if success:
                # Mark this fish for removal from source tank
                self.state.transition(EntityState.REMOVED, reason=DEATH_REASON_MIGRATION)
                logger.debug(f"Fish #{self.fish_id} successfully migrated {direction}")

            return success

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False

    def get_remembered_food_locations(self) -> List[Vector2]:
        """Get list of remembered food locations (excluding expired memories).

        Returns:
            List of Vector2 positions where food was previously found
        """
        memories = self.memory_system.get_all_memories(MemoryType.FOOD_LOCATION, min_strength=0.1)
        return [m.location for m in memories]

    def is_dead(self) -> bool:
        """Check if fish should die or has migrated.

        OPTIMIZATION: Uses cached dead state when possible to avoid repeated checks.
        Cache is updated when energy changes or age increments.
        """
        # OPTIMIZATION: Return cached value if already dead
        if self._cached_is_dead:
            return True

        # Check active state first (checks underlying state machine)
        if self.state.state in (EntityState.DEAD, EntityState.REMOVED):
            self._cached_is_dead = True
            return True

        # Check conditions and update state if now dead
        # 1. Energy depletion
        if self.energy <= 0:
            self.state.transition(EntityState.DEAD, reason=DEATH_REASON_STARVATION)
            self._cached_is_dead = True
            return True

        # 2. Old age
        if self._lifecycle_component.age >= self._lifecycle_component.max_age:
            self.state.transition(EntityState.DEAD, reason=DEATH_REASON_OLD_AGE)
            self._cached_is_dead = True
            return True

        return False

    def get_death_cause(self) -> str:
        """Determine the cause of death.

        Checks state history first for explicit causes recorded during transition.
        If history is unavailable/unclear, infers cause from current state.

        Returns:
            str: Cause of death ('starvation', 'old_age', 'predation', 'migration')
        """
        # Check explicit history first
        history = self.state.history
        if history:
            last_transition = history[-1]
            if last_transition.to_state in (EntityState.DEAD, EntityState.REMOVED):
                # Reason is stored in transition (e.g. "starvation", "old_age", "migration")
                # Normalize reason to match expected strings
                reason = last_transition.reason
                if "migration" in reason:
                    return "migration"
                if "starvation" in reason:
                    # Check for predation overlap even if recorded as starvation
                    if (
                        self._lifecycle_component.age - self.last_predator_encounter_age
                        <= PREDATOR_ENCOUNTER_WINDOW
                    ):
                        return "predation"
                    return "starvation"
                if "old_age" in reason:
                    return "old_age"
                if "predation" in reason:
                    return "predation"

        # Fallback to inference if history unavailable/unclear
        if self.state.state == EntityState.REMOVED:
            return "migration"  # Assume removal implies migration if not death

        # Logic for determining death cause based on state
        if self.energy <= 0:
            # Check if there was a recent predator encounter
            if (
                self._lifecycle_component.age - self.last_predator_encounter_age
                <= PREDATOR_ENCOUNTER_WINDOW
            ):
                return "predation"  # Death after conflict
            else:
                return "starvation"  # Death without recent conflict
        elif self._lifecycle_component.age >= self._lifecycle_component.max_age:
            return "old_age"

        # Debugging "Unknown" causes
        # Capture state to identify why we reached here
        parts = []
        if self.state.state == EntityState.ACTIVE:
            parts.append("active")
        if self.state.state == EntityState.DEAD:
            parts.append("dead")
        if self.energy > 0:
            parts.append("pos_energy")
        if not history:
            parts.append("no_hist")
        else:
            parts.append(f"last_rsn_{history[-1].reason}")

        return f"unknown_{'_'.join(parts)}"

    def mark_predator_encounter(self, escaped: bool = False, damage_taken: float = 0.0) -> None:
        """Mark that this fish has encountered a predator.

        This is used to determine death attribution - if the fish dies from
        energy depletion shortly after this encounter, it counts as predation.

        Args:
            escaped: Whether the fish successfully escaped
            damage_taken: Amount of damage/energy lost
        """
        self.last_predator_encounter_age = self._lifecycle_component.age

    def can_reproduce(self) -> bool:
        """Check if fish can reproduce.

        Delegates to ReproductionComponent.

        Returns:
            bool: True if fish can reproduce
        """
        return self._reproduction_component.can_reproduce(
            self._lifecycle_component.life_stage,
            self.energy,
            self.max_energy,
        )

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
        """Update reproduction state and potentially create offspring.

        Updates cooldown timer and checks if conditions are met for instant
        asexual reproduction (overflow energy banked + eligible).

        Returns:
            Newborn fish if reproduction occurred, None otherwise
        """
        from core.reproduction_service import ReproductionService

        self._reproduction_component.update_cooldown()
        return ReproductionService.maybe_create_banked_offspring(self)

    def _create_asexual_offspring(self) -> Optional["Fish"]:
        """Create an offspring through asexual reproduction.

        This is called when conditions are met for instant asexual reproduction.
        The baby is created immediately (no pregnancy/gestation period).

        Returns:
            The newly created baby fish, or None if creation failed
        """
        # Obtain RNG for determinism - fail loudly if unavailable
        from core.util.rng import require_rng

        rng = require_rng(self.environment, "Fish._create_asexual_offspring")

        # Get available policies for mutation
        available_policies = None
        if hasattr(self.environment, "code_pool"):
            # Get only valid movement policies
            components = self.environment.code_pool.list_components()
            available_policies = [
                comp.component_id for comp in components if comp.kind == "movement_policy"
            ]

        # Generate offspring genome (also sets cooldown)
        offspring_genome, _unused_fraction = (
            self._reproduction_component.trigger_asexual_reproduction(
                self.genome, rng=rng, available_policies=available_policies
            )
        )

        # Calculate baby's max energy capacity (babies start at FISH_BABY_SIZE)
        from core.config.fish import FISH_BABY_SIZE

        baby_max_energy = (
            ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * offspring_genome.physical.size_modifier.value
        )

        # Use banked overflow energy first, then draw from parent
        bank_used = self._reproduction_component.consume_overflow_energy_bank(baby_max_energy)
        remaining_needed = baby_max_energy - bank_used
        parent_transfer = min(self.energy, remaining_needed)

        # Transfer energy from parent to baby
        self.energy -= parent_transfer
        baby_initial_energy = bank_used + parent_transfer

        # Get boundaries from environment (World protocol)
        bounds = self.environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds

        # Create offspring near parent
        offset_x = rng.uniform(-30, 30)
        offset_y = rng.uniform(-30, 30)
        baby_x = self.pos.x + offset_x
        baby_y = self.pos.y + offset_y

        # Clamp to screen
        baby_x = max(min_x, min(max_x - 50, baby_x))
        baby_y = max(min_y, min(max_y - 50, baby_y))

        # Create baby fish with transferred energy
        baby = Fish(
            environment=self.environment,
            movement_strategy=self.movement_strategy.__class__(),
            species=self.species,
            x=baby_x,
            y=baby_y,
            speed=FISH_BASE_SPEED,
            genome=offspring_genome,
            generation=self.generation + 1,
            ecosystem=self.ecosystem,
            initial_energy=baby_initial_energy,
            parent_id=self.fish_id,
        )

        # Record reproduction stats using composable behavior ID
        composable = self.genome.behavioral.behavior
        if composable is not None and composable.value is not None:
            behavior_id = composable.value.behavior_id
            algorithm_id = hash(behavior_id) % 1000
            self._emit_event(ReproductionEvent(algorithm_id, is_asexual=True))

        # Inherit skill game strategies from parent with mutation
        baby._skill_game_component.inherit_from_parent(
            self._skill_game_component,
            mutation_rate=0.1,
            rng=rng,
        )

        # Set visual birth effect timer (60 frames = 2 seconds at 30fps)
        self.visual_state.set_birth_effect(60)

        return baby

    def _get_visual_bounds_offsets(self) -> Tuple[float, float, float, float]:
        """Return visual bounds offsets from self.pos for edge clamping.

        Accounts for lifecycle scaling and parametric template geometry so the
        rendered fish stays inside the tank bounds.
        """
        base_size = max(self.width, self.height)
        lifecycle = getattr(self, "_lifecycle_component", None)
        size = lifecycle.size if lifecycle is not None and hasattr(lifecycle, "size") else 1.0
        scaled_base = base_size * size

        genome = getattr(self, "genome", None)
        physical = getattr(genome, "physical", None) if genome is not None else None
        if physical is None:
            return (0.0, scaled_base, 0.0, scaled_base)

        fin_trait = getattr(physical, "fin_size", None)
        tail_trait = getattr(physical, "tail_size", None)
        body_trait = getattr(physical, "body_aspect", None)
        template_trait = getattr(physical, "template_id", None)

        fin_size = fin_trait.value if fin_trait is not None and fin_trait.value is not None else 1.0
        tail_size = (
            tail_trait.value if tail_trait is not None and tail_trait.value is not None else 1.0
        )
        body_aspect = (
            body_trait.value if body_trait is not None and body_trait.value is not None else 1.0
        )
        template_id = (
            int(template_trait.value)
            if template_trait is not None and template_trait.value is not None
            else 0
        )
        template_id = max(0, min(5, template_id))

        width_scale = body_aspect
        height_scale = 1.0

        if template_id == 5:
            width_scale = body_aspect * 1.3
            height_scale = 0.7
            min_x_ratio = min(0.05, 0.3 - 0.08 * fin_size, 0.1 - 0.15 * tail_size)
            max_x_ratio = 0.98
            min_y_ratio = min(0.25, 0.35 - 0.12 * fin_size)
            max_y_ratio = 0.75
        elif template_id == 4:
            min_x_ratio = min(0.2, 0.4 - 0.2 * fin_size, 0.25 - 0.18 * tail_size)
            max_x_ratio = 0.92
            min_y_ratio = 0.15 - 0.15 * fin_size
            max_y_ratio = 0.85
        elif template_id == 3:
            min_x_ratio = 0.3 - 0.25 * tail_size
            max_x_ratio = 0.9
            min_y_ratio = min(0.2, 0.22 - 0.3 * fin_size)
            max_y_ratio = 0.78 + 0.3 * fin_size
        elif template_id == 2:
            min_x_ratio = min(0.2, 0.25 - 0.3 * tail_size)
            max_x_ratio = 0.95
            min_y_ratio = 0.2 - 0.25 * fin_size
            max_y_ratio = 0.8 + 0.25 * fin_size
        elif template_id == 1:
            min_x_ratio = min(0.1, 0.4 - 0.1 * fin_size, 0.15 - 0.2 * tail_size)
            max_x_ratio = 0.95
            min_y_ratio = min(0.2, 0.3 - 0.15 * fin_size)
            max_y_ratio = 0.8
        else:
            min_x_ratio = min(0.1, 0.35 - 0.15 * fin_size, 0.2 - 0.25 * tail_size)
            max_x_ratio = 0.95
            min_y_ratio = min(0.1, 0.15 - 0.2 * fin_size)
            max_y_ratio = 0.9

        width = scaled_base * width_scale
        height = scaled_base * height_scale
        min_x = min_x_ratio * width
        max_x = max_x_ratio * width
        min_y = min_y_ratio * height
        max_y = max_y_ratio * height

        flipped_min_x = scaled_base - max_x
        flipped_max_x = scaled_base - min_x

        effective_min_x = min(0.0, min_x, flipped_min_x)
        effective_max_x = max(scaled_base, max_x, flipped_max_x)
        effective_min_y = min(0.0, min_y)
        effective_max_y = max(scaled_base, max_y)

        return (effective_min_x, effective_max_x, effective_min_y, effective_max_y)

    def constrain_to_screen(self) -> None:
        """Override to use cached bounds."""
        if self._cached_bounds is None:
            self._cached_bounds = self.environment.get_bounds()

        (min_x, min_y), (max_x, max_y) = self._cached_bounds

        # Clamp horizontally
        if self.pos.x < min_x:
            self.pos.x = min_x
        elif self.pos.x + self.width > max_x:
            self.pos.x = max_x - self.width

        # Clamp vertically
        if self.pos.y < min_y:
            self.pos.y = min_y
        elif self.pos.y + self.height > max_y:
            self.pos.y = max_y - self.height

        # Keep rect in sync with position
        self.rect.topleft = self.pos

    def handle_screen_edges(self) -> None:
        """Handle the fish hitting the edge of the screen with top margin for energy bar visibility.

        For connected tanks, attempts migration when hitting left/right boundaries.
        """

        # Get boundaries from environment (World protocol)
        if self._cached_bounds is None:
            self._cached_bounds = self.environment.get_bounds()

        (env_min_x, env_min_y), (env_max_x, env_max_y) = self._cached_bounds

        min_x_offset, max_x_offset, min_y_offset, max_y_offset = self._get_visual_bounds_offsets()

        # Adjusted top boundary for energy bar visibility
        adjusted_min_y = max(env_min_y, FISH_TOP_MARGIN)

        # Horizontal boundaries - check for migration first, then bounce
        if self.pos.x + min_x_offset < env_min_x:
            if self._attempt_migration("left"):
                return  # Migration successful, fish removed from this tank
            self.pos.x = env_min_x - min_x_offset
            self.vel.x = abs(self.vel.x)  # Bounce right
        elif self.pos.x + max_x_offset > env_max_x:
            if self._attempt_migration("right"):
                return  # Migration successful, fish removed from this tank
            self.pos.x = env_max_x - max_x_offset
            self.vel.x = -abs(self.vel.x)  # Bounce left

        # Vertical boundaries with top margin for energy bar visibility
        if self.pos.y + min_y_offset < adjusted_min_y:
            self.pos.y = adjusted_min_y - min_y_offset
            self.vel.y = abs(self.vel.y)  # Bounce down
        elif self.pos.y + max_y_offset > env_max_y:
            self.pos.y = env_max_y - max_y_offset
            self.vel.y = -abs(self.vel.y)  # Bounce up

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ) -> "EntityUpdateResult":
        """Update the fish state.

        Args:
            frame_count: Time elapsed since start
            time_modifier: Time-based modifier (e.g., for day/night)
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            EntityUpdateResult containing newborn fish if reproduction occurred
        """
        from core.entities.base import EntityUpdateResult

        super().update(frame_count, time_modifier, time_of_day)

        # Performance: Cache bounds once per frame
        self._cached_bounds = self.environment.get_bounds()

        # Age - managed by LifecycleComponent
        self._lifecycle_component.increment_age()
        age = self._lifecycle_component.age  # Cache for use below

        # Performance: Update enhanced memory system less frequently (every 10 frames)
        if age % 10 == 0:
            # Update enhanced memory system less frequently
            self.memory_system.update(age)

        # Energy consumption
        self.consume_energy(time_modifier)

        # Update visual effects (delegated to visual state)
        self.visual_state.update()

        # Handle death
        if self.is_dead():
            # Stop movement for dying fish so they don't drift while showing death icon
            self.vel.x = 0
            self.vel.y = 0

            # Create update result with death event if desired, or just empty
            # For now, SimulationEngine handles death by checking is_dead() separately
            # but we could move that here.
            # Keeping strictly to refactoring return type for now.
            return EntityUpdateResult()

        previous_direction = self.last_direction

        # Movement (algorithms handle critical energy internally)
        self.movement_strategy.move(self)

        self._apply_turn_energy_cost(previous_direction)

        # Update poker cooldown
        if self.poker_cooldown > 0:
            self.poker_cooldown -= 1

        result = EntityUpdateResult()
        return result

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
        if self.get_energy_state().is_saturated:
            return

        # Limit bite size to what we can actually use
        effective_bite_size = min(self.bite_size, available_capacity)

        # Take a bite from the food (only what we can hold)
        potential_energy = food.take_bite(effective_bite_size)
        # Apply energy immediately (modify_energy handles overflow banking)
        actual_energy = self.modify_energy(potential_energy)

        # Record food location in memory
        from core.fish_memory import MemoryType

        self.memory_system.add_memory(MemoryType.FOOD_LOCATION, food.pos)

        # Record food consumption for behavior performance tracking
        from core.entities.plant import PlantNectar
        from core.entities.resources import LiveFood

        # Get algorithm ID for tracking (0 if no composable behavior)
        composable = self.genome.behavioral.behavior
        if composable is not None and composable.value is not None:
            behavior_id = composable.value.behavior_id
            algorithm_id = hash(behavior_id) % 1000
        else:
            algorithm_id = 0  # Default algorithm for fish without composable behavior

        # Determine food type and emit telemetry
        # Use actual_energy to prevent "phantom" stats
        if isinstance(food, PlantNectar):
            self._emit_event(FoodEatenEvent("nectar", algorithm_id, actual_energy))
        elif isinstance(food, LiveFood):
            self._emit_event(
                FoodEatenEvent(
                    "live_food",
                    algorithm_id,
                    actual_energy,
                    genome=self.genome,
                    generation=self.generation,
                )
            )
        else:
            self._emit_event(FoodEatenEvent("falling_food", algorithm_id, actual_energy))

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
                size_factor = self._lifecycle_component.size**DIRECTION_CHANGE_SIZE_MULTIPLIER
                energy_cost = DIRECTION_CHANGE_ENERGY_BASE * turn_intensity * size_factor

                self.energy = max(0, self.energy - energy_cost)

                self._emit_event(EnergyBurnEvent("turning", energy_cost))

        self.last_direction = new_direction
