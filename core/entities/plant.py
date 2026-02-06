"""Plant entity with evolving L-system genetics.

This module implements plants that grow from root spots,
collect energy passively, produce nectar for reproduction, and
can play poker against fish.

This replaces the old 'Plant' and 'FractalPlant' classes with a single unified 'Plant'.
The Plant class now delegates to specialized components for better modularity:
- PlantEnergyComponent: Energy collection and management
- PlantNectarComponent: Nectar production for reproduction
- PlantPokerComponent: Poker gameplay functionality
- PlantMigrationComponent: Migration between tanks
- PlantVisualComponent: Size and rendering calculations
"""

import logging
from typing import TYPE_CHECKING, Optional

from core.entities.base import Agent, EntityUpdateResult
from core.entities.resources import Food
from core.entity_ids import PlantId
from core.genetics import PlantGenome
from core.plant.energy_component import PlantEnergyComponent
from core.plant.migration_component import PlantMigrationComponent
from core.plant.nectar_component import PlantNectarComponent
from core.plant.poker_component import PlantPokerComponent
from core.plant.visual_component import PlantVisualComponent
from core.state_machine import EntityState

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.root_spots import RootSpot
    from core.world import World

from core.config.plants import (
    PLANT_DEATH_ENERGY,
    PLANT_INITIAL_ENERGY,
    PLANT_MAX_ENERGY,
    PLANT_NECTAR_ENERGY,
)

logger = logging.getLogger(__name__)


class Plant(Agent):
    """A plant entity with evolving L-system genetics.

    Plants:
    - Grow from fixed root spots at the tank bottom
    - Collect energy passively (more energy = bigger = more collection)
    - Produce nectar when large enough (triggers reproduction)
    - Can play poker against fish (fish can eat the plant's energy)
    - Have genetically inherited fractal shapes that evolve

    This class delegates to specialized components:
    - _energy_comp: Energy collection and management
    - _nectar_comp: Nectar production
    - _poker_comp: Poker gameplay
    - _migration_comp: Tank migration
    - _visual_comp: Size and rendering

    Attributes:
        plant_id: Unique identifier
        genome: PlantGenome with L-system parameters and traits
        energy: Current energy level (determines size)
        max_energy: Maximum energy capacity
        root_spot: The RootSpot this plant is anchored to (Optional)
        poker_cooldown: Frames until can play poker again
        nectar_cooldown: Frames until can produce nectar again
        age: Frames since sprouting
        nectar_produced: Count of nectar produced
        poker_wins: Count of poker games won
        poker_losses: Count of poker games lost
    """

    def __init__(
        self,
        environment: "World",
        genome: PlantGenome,
        root_spot: Optional["RootSpot"],
        initial_energy: float = PLANT_INITIAL_ENERGY,
        ecosystem: Optional["EcosystemManager"] = None,
        *,
        plant_id: int,
    ) -> None:
        """Initialize a plant.

        Args:
            environment: The world the plant lives in
            genome: The plant's genetic information
            root_spot: The root spot this plant grows from
            initial_energy: Starting energy level
            plant_id: Unique identifier (required, assigned by PlantManager)
        """
        if root_spot is None:
            raise ValueError("root_spot is required to initialize a Plant")

        # Initialize at the root spot position
        super().__init__(
            environment,
            root_spot.x,
            root_spot.y,
            0,  # Plants don't move
        )

        # Assign unique ID (no fallback - must be provided by PlantManager)
        self.plant_id = plant_id

        # Core attributes
        self.genome = genome
        self.root_spot = root_spot
        self.max_energy = PLANT_MAX_ENERGY * genome.growth_efficiency
        self.ecosystem = ecosystem

        # Statistics
        self.age = 0

        # Type-safe ID wrapper (cached to avoid repeated object creation)
        self._typed_id: Optional[PlantId] = None

        # Get RNG for components
        rng = getattr(environment, "rng", None)
        if rng is None:
            raise RuntimeError("environment.rng is required for deterministic plant initialization")

        # Initialize components with callbacks
        self._energy_comp = PlantEnergyComponent(
            genome=genome,
            initial_energy=initial_energy,
            max_energy=self.max_energy,
            get_root_spot=lambda: self.root_spot,
            get_environment=lambda: self.environment,
        )

        self._nectar_comp = PlantNectarComponent(
            get_energy_ratio=self._energy_comp.get_energy_ratio,
            get_energy=lambda: self._energy_comp.energy,
            get_genome=lambda: self.genome,
            get_environment=lambda: self.environment,
            get_plant_pos=lambda: (self.pos.x, self.pos.y),
            get_plant_size=lambda: (self.width, self.height),
            lose_energy=self.lose_energy,
        )

        self._poker_comp = PlantPokerComponent(
            plant_id=plant_id,
            get_energy=lambda: self._energy_comp.energy,
            get_genome=lambda: self.genome,
            get_environment=lambda: self.environment,
            is_dead=self.is_dead,
        )

        self._migration_comp = PlantMigrationComponent(
            plant_id=plant_id,
            get_root_spot=lambda: self.root_spot,
            get_environment=lambda: self.environment,
            transition_state=self._transition_state,
            rng=rng,
        )

        self._visual_comp = PlantVisualComponent(
            get_energy=lambda: self._energy_comp.energy,
            get_max_energy=lambda: self.max_energy,
            get_genome=lambda: self.genome,
            get_nectar_cooldown=lambda: self._nectar_comp.nectar_cooldown,
        )

        # Update size based on initial energy
        self._update_size()

    # =========================================================================
    # Property accessors for component state (backwards compatibility)
    # =========================================================================

    @property
    def energy(self) -> float:
        """Current energy level."""
        return self._energy_comp.energy

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level."""
        self._energy_comp.energy = value

    @property
    def poker_cooldown(self) -> int:
        """Frames until can play poker again."""
        return self._poker_comp.poker_cooldown

    @poker_cooldown.setter
    def poker_cooldown(self, value: int) -> None:
        """Set poker cooldown."""
        self._poker_comp.poker_cooldown = value

    @property
    def nectar_cooldown(self) -> int:
        """Frames until can produce nectar again."""
        return self._nectar_comp.nectar_cooldown

    @nectar_cooldown.setter
    def nectar_cooldown(self, value: int) -> None:
        """Set nectar cooldown."""
        self._nectar_comp.nectar_cooldown = value

    @property
    def nectar_produced(self) -> int:
        """Count of nectar produced."""
        return self._nectar_comp.nectar_produced

    @nectar_produced.setter
    def nectar_produced(self, value: int) -> None:
        """Set nectar produced count."""
        self._nectar_comp.nectar_produced = value

    @property
    def poker_wins(self) -> int:
        """Count of poker games won."""
        return self._poker_comp.poker_wins

    @poker_wins.setter
    def poker_wins(self, value: int) -> None:
        """Set poker wins count."""
        self._poker_comp.poker_wins = value

    @property
    def poker_losses(self) -> int:
        """Count of poker games lost."""
        return self._poker_comp.poker_losses

    @poker_losses.setter
    def poker_losses(self, value: int) -> None:
        """Set poker losses count."""
        self._poker_comp.poker_losses = value

    @property
    def last_button_position(self) -> int:
        """Last dealer button position."""
        return self._poker_comp.last_button_position

    @last_button_position.setter
    def last_button_position(self, value: int) -> None:
        """Set last button position."""
        self._poker_comp.last_button_position = value

    @property
    def poker_effect_state(self) -> Optional[dict]:
        """Current poker effect state."""
        return self._poker_comp.poker_effect_state

    @poker_effect_state.setter
    def poker_effect_state(self, value: Optional[dict]) -> None:
        """Set poker effect state."""
        self._poker_comp.poker_effect_state = value

    @property
    def poker_effect_timer(self) -> int:
        """Remaining frames for poker effect display."""
        return self._poker_comp.poker_effect_timer

    @poker_effect_timer.setter
    def poker_effect_timer(self, value: int) -> None:
        """Set poker effect timer."""
        self._poker_comp.poker_effect_timer = value

    @property
    def migration_timer(self) -> int:
        """Frames until next migration check."""
        return self._migration_comp.migration_timer

    @migration_timer.setter
    def migration_timer(self, value: int) -> None:
        """Set migration timer."""
        self._migration_comp.migration_timer = value

    @property
    def migration_check_interval(self) -> int:
        """Frames between migration checks."""
        return self._migration_comp.migration_check_interval

    @migration_check_interval.setter
    def migration_check_interval(self, value: int) -> None:
        """Set migration check interval."""
        self._migration_comp.migration_check_interval = value

    # =========================================================================
    # Core methods
    # =========================================================================

    def _update_size(self) -> None:
        """Update plant size based on current energy."""
        width, height = self._visual_comp.calculate_size()
        self.set_size(width, height)

        # Anchor using root spot semantics (bottom vs center)
        if self.root_spot is None:
            # Stationary fallback if root spot is lost
            self.rect.topleft = self.pos
        elif hasattr(self.root_spot, "get_anchor_topleft"):
            self.pos.x, self.pos.y = self.root_spot.get_anchor_topleft(self.width, self.height)
            self.rect.topleft = self.pos
        else:
            # Fallback for legacy/mock root spots
            self.pos.y = self.root_spot.y - self.height
            self.rect.y = self.pos.y

    @property
    def typed_id(self) -> PlantId:
        """Get the type-safe plant ID.

        This wraps the raw plant_id in a PlantId type for type safety.
        The wrapper is cached to avoid repeated object creation.

        Returns:
            PlantId wrapper around plant_id
        """
        if self._typed_id is None or self._typed_id.value != self.plant_id:
            self._typed_id = PlantId(self.plant_id)
        return self._typed_id

    def get_entity_id(self) -> Optional[int]:
        """Get the unique identifier for this plant (Identifiable protocol).

        Returns:
            Unique plant ID
        """
        return self.plant_id

    @property
    def snapshot_type(self) -> str:
        """Return entity type for snapshot serialization.

        Used by identity providers to determine type-specific ID offsets
        without requiring isinstance checks.
        """
        return "plant"

    def update_position(self) -> None:
        """Plants are stationary - don't update position."""
        pass

    def update(
        self,
        frame_count: int,
        time_modifier: float = 1.0,
        time_of_day: Optional[float] = None,
    ) -> "EntityUpdateResult":
        """Update the plant state.

        Args:
            frame_count: Time elapsed since start
            time_modifier: Time-based modifier (day/night effects)
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            EntityUpdateResult containing nectar if produced
        """
        from core.entities.base import EntityUpdateResult

        super().update(frame_count, time_modifier, time_of_day)

        self.age += 1

        # Update component timers
        self._poker_comp.update()
        self._nectar_comp.update()

        # Update migration timer
        self._migration_comp.update()

        # Passive energy collection (compound growth)
        self._collect_energy(time_of_day)

        # Update size based on new energy
        self._update_size()

        # Check if can produce nectar
        nectar = self._try_produce_nectar(time_of_day)

        result = EntityUpdateResult()
        if nectar:
            result.spawned_entities.append(nectar)

        return result

    def _collect_energy(self, time_of_day: Optional[float] = None) -> float:
        """Collect passive energy through photosynthesis.

        This method delegates to the energy component but is kept for
        backwards compatibility with tests and external code.

        Args:
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            Amount of energy collected
        """
        return self._energy_comp.collect_energy(time_of_day)

    def _try_produce_nectar(self, time_of_day: Optional[float]) -> Optional["PlantNectar"]:
        """Try to produce nectar if conditions are met.

        Args:
            time_of_day: Normalized time of day

        Returns:
            PlantNectar if produced, None otherwise
        """
        if not self._nectar_comp.can_produce_nectar():
            return None

        # Get nectar creation data from component
        nectar_data = self._nectar_comp.try_produce_nectar(time_of_day)
        if nectar_data is None:
            return None

        # Create actual nectar with reference to self
        return PlantNectar(
            environment=self.environment,
            x=nectar_data.x,
            y=nectar_data.y,
            source_plant=self,
            relative_y_offset_pct=nectar_data.relative_y_offset_pct,
            floral_visuals=nectar_data.floral_visuals,
        )

    def _check_migration(self) -> None:
        """Check if plant should attempt migration based on root spot position."""
        # Handled by migration component's update() method
        pass

    def _attempt_migration(self, direction: str) -> bool:
        """Attempt to migrate to a connected tank.

        Uses dependency injection pattern - delegates to environment's migration
        handler if available. This keeps core entities decoupled from backend.

        Args:
            direction: "left" or "right" - which edge this plant is on

        Returns:
            True if migration successful, False otherwise
        """
        migration_handler = getattr(self.environment, "migration_handler", None)
        if migration_handler is None:
            return False

        world_id = getattr(self.environment, "world_id", None)
        if world_id is None:
            return False

        try:
            success = bool(migration_handler.attempt_entity_migration(self, direction, world_id))

            if success:
                # Mark this plant for removal from source tank
                self.state.transition(EntityState.REMOVED, reason="migration")
                logger.debug(f"Plant #{self.plant_id} successfully migrated {direction}")

            return success

        except Exception as e:
            logger.error(f"Plant migration failed: {e}", exc_info=True)
            return False

    # =========================================================================
    # Energy methods (delegating to component)
    # =========================================================================

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Adjust plant energy and return the actual delta.

        Positive amounts clamp to max_energy; overflow is routed (food drop).
        Negative amounts clamp at 0.

        Args:
            amount: Energy to add (positive) or remove (negative)
            source: Source of the energy change (for tracking)

        Returns:
            The actual delta applied to the plant's internal energy store.
        """
        if amount == 0:
            return 0.0

        before = self._energy_comp.energy

        if amount > 0:
            target = before + amount
            if target > self.max_energy:
                overflow = target - self.max_energy
                self._energy_comp.energy = self.max_energy
                self._route_overflow_energy(overflow)
            else:
                self._energy_comp.energy = target
        else:
            actual_loss = min(before, -amount)
            self._energy_comp.energy = before - actual_loss

        self._update_size()

        delta = self._energy_comp.energy - before

        # Record the delta via the engine recorder (single source of truth)
        if hasattr(self, "environment") and hasattr(self.environment, "record_energy_delta"):
            self.environment.record_energy_delta(self, delta, source)

        return delta

    def _transition_state(self, state: EntityState, reason: str) -> None:
        self.state.transition(state, reason=reason)

    def lose_energy(self, amount: float, source: str = "poker") -> float:
        """Lose energy (from poker loss or being eaten).

        Args:
            amount: Energy to lose
            source: Source of energy loss

        Returns:
            Actual amount lost
        """
        before = self._energy_comp.energy
        actual_loss = self._energy_comp.lose_energy(amount)
        self._update_size()
        if actual_loss > 0:
            logger.debug(
                f"Plant #{self.plant_id} lost {actual_loss:.1f} energy ({source}): "
                f"{before:.1f} -> {self._energy_comp.energy:.1f}"
            )
        return actual_loss

    def gain_energy(self, amount: float, *, source: str = "poker") -> float:
        """Gain energy (from poker win).

        Args:
            amount: Energy to gain
            source: Source of the energy gain (for tracking)

        Returns:
            Actual amount gained (including overflow that was routed)
        """
        if amount <= 0:
            return 0.0

        gained, overflow = self._energy_comp.gain_energy(amount)
        if overflow > 0:
            self._route_overflow_energy(overflow)
        self._update_size()
        return amount  # Return full amount since overflow was routed

    def _route_overflow_energy(self, overflow: float) -> None:
        """Route overflow energy into a food drop near the plant.

        When a plant gains more energy than it can hold (e.g., from poker
        winnings), this method converts the excess into food that drops
        near the plant base, conserving energy in the ecosystem.

        Args:
            overflow: Amount of energy exceeding max capacity
        """
        if overflow < 1.0:
            return

        try:
            from core.util.mutations import request_spawn_in

            rng = getattr(self.environment, "rng", None)
            if rng is None:
                raise RuntimeError("environment.rng is required for deterministic food spawning")
            food = Food(
                environment=self.environment,
                x=self.pos.x + self.width / 2 + rng.uniform(-20, 20),
                y=self.pos.y + self.height - 10,  # Near the base of the plant
                food_type="energy",
            )
            food.energy = min(overflow, food.max_energy)
            food.max_energy = food.energy

            if not request_spawn_in(self.environment, food, reason="plant_overflow_food"):
                logger.warning("spawn requester unavailable, plant overflow food lost")
        except Exception:
            logger.debug(
                "Plant overflow energy spawn failed; energy lost on failure is acceptable",
                exc_info=True,
            )

    # =========================================================================
    # Poker methods (delegating to component)
    # =========================================================================

    def can_play_poker(self) -> bool:
        """Check if plant can play poker.

        Returns:
            True if poker game can proceed
        """
        return self._poker_comp.can_play_poker()

    def get_poker_aggression(self) -> float:
        """Get poker aggression level.

        Returns:
            Aggression value for poker decisions (0.0-1.0)
        """
        return self._poker_comp.get_poker_aggression()

    def get_poker_strategy(self):
        """Get poker strategy for this plant.

        If this plant has a strategy_type set (baseline strategy plant),
        returns the corresponding baseline poker strategy implementation.
        Otherwise falls back to the genome-based adapter.

        Returns:
            PokerStrategyAlgorithm: Either a baseline strategy or PlantPokerStrategyAdapter
        """
        return self._poker_comp.get_poker_strategy()

    def get_poker_id(self) -> int:
        """Get stable ID for poker tracking.

        Returns:
            plant_id offset by 100000 to avoid collision with fish IDs
        """
        return self._poker_comp.get_poker_id()

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
        self._poker_comp.set_poker_effect(status, amount, duration, target_id, target_type)

    # =========================================================================
    # Visual methods (delegating to component)
    # =========================================================================

    def get_size_multiplier(self) -> float:
        """Get current size multiplier for rendering.

        Returns:
            Size multiplier (0.3 to 1.5)
        """
        return self._visual_comp.get_size_multiplier()

    def get_fractal_iterations(self) -> int:
        """Get number of L-system iterations based on size.

        Larger plants have more detailed fractals.

        Returns:
            Number of iterations (1-3)
        """
        return self._visual_comp.get_fractal_iterations()

    # =========================================================================
    # Lifecycle methods
    # =========================================================================

    def is_dead(self) -> bool:
        """Check if plant is dead (energy too low) or has migrated.

        Returns:
            True if plant should be removed
        """
        # Check explicit state first (e.g. migrated)
        if self.state.state in (EntityState.DEAD, EntityState.REMOVED):
            return True

        # Check condition-based death (low energy)
        if self._energy_comp.energy < PLANT_DEATH_ENERGY:
            logger.debug(
                f"Plant #{self.plant_id} died from low energy "
                f"({self._energy_comp.energy:.1f} < {PLANT_DEATH_ENERGY})"
            )
            self.state.transition(EntityState.DEAD, reason="low_energy")
            return True

        return False

    def die(self) -> None:
        """Handle plant death - release root spot."""
        if self.root_spot is not None:
            # Only release if we actually own the spot
            release_if_occupant = getattr(self.root_spot, "release_if_occupant", None)
            if callable(release_if_occupant):
                release_if_occupant(self)
            else:
                self.root_spot.release()

    def notify_food_eaten(self) -> None:
        """Notify plant that one of its food items was eaten.

        For Plant, this is a no-op as nectar production is controlled
        by cooldowns and energy thresholds, not a concurrent count limit.
        """
        pass

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_state_dict(self) -> dict:
        """Serialize plant state for frontend rendering.

        Returns:
            Dictionary with plant state
        """
        return self._visual_comp.to_state_dict(
            plant_id=self.plant_id,
            pos_x=self.pos.x,
            pos_y=self.pos.y,
            width=self.width,
            height=self.height,
            age=self.age,
            poker_effect_state=self._poker_comp.poker_effect_state,
        )


class PlantNectar(Food):
    """Nectar produced by plants.

    When consumed by fish, triggers plant reproduction at a nearby root spot.

    Attributes:
        source_plant: The plant that produced this nectar
        parent_genome: Copy of parent plant's genome for inheritance
        energy: Energy value when consumed
    """

    NECTAR_ENERGY = PLANT_NECTAR_ENERGY
    NECTAR_SIZE = 15

    def __init__(
        self,
        environment: "World",
        x: float,
        y: float,
        source_plant: Plant,
        relative_y_offset_pct: float = 0.20,
        floral_visuals: Optional[dict] = None,
    ) -> None:
        """Initialize plant nectar.

        Args:
            environment: The environment
            x: X position
            y: Y position
            source_plant: The plant that produced this
            relative_y_offset_pct: Vertical offset from top as percentage of height (0.0-1.0)
            floral_visuals: Dictionary of visual properties (hue, saturation, type, etc.)
        """
        super().__init__(
            environment,
            x,
            y,
            source_plant=source_plant,
            food_type="nectar",
            allow_stationary_types=True,
        )

        self.source_plant = source_plant
        self.relative_y_offset_pct = relative_y_offset_pct
        self.floral_visuals = floral_visuals or {}
        self.parent_genome = source_plant.genome  # Reference to parent genome
        # Override energy from Food init (which uses default 90.0 from constants)
        self.energy = self.NECTAR_ENERGY
        self.max_energy = self.NECTAR_ENERGY

        self.set_size(self.NECTAR_SIZE, self.NECTAR_SIZE)

    @property
    def snapshot_type(self) -> str:
        """Return entity type for snapshot serialization.

        Used by identity providers to determine type-specific ID offsets
        without requiring isinstance checks.
        """
        return "plant_nectar"

    def update_position(self) -> None:
        """Nectar stays attached to its source plant in the upper portion."""
        if self.source_plant is not None and not self.source_plant.is_dead():
            # relative_y_offset_pct is how far UP from base (0.65-0.95 = upper portion)
            # Calculate position from base going up
            base_y = self.source_plant.pos.y + self.source_plant.height
            self.pos.x = self.source_plant.pos.x + self.source_plant.width / 2 - self.width / 2
            self.pos.y = (
                base_y - self.source_plant.height * self.relative_y_offset_pct - self.height / 2
            )

    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: Optional[float] = None
    ) -> "EntityUpdateResult":
        """Update nectar state."""
        from core.entities.base import EntityUpdateResult

        super().update(frame_count, time_modifier, time_of_day)
        self.update_position()
        if self.environment:
            self.environment.update_agent_position(self)
        return EntityUpdateResult()

    def get_energy_value(self) -> float:
        """Get energy provided when consumed.

        Returns:
            Energy value
        """
        return self.energy

    def is_consumed(self) -> bool:
        """Check if nectar has been consumed.

        Returns:
            True if fully consumed
        """
        return self.energy <= 0

    def take_bite(self, bite_size: float) -> float:
        """Take a bite from the nectar.

        Overrides Food.take_bite to trigger reproduction logic when fully consumed.
        """
        consumed = super().take_bite(bite_size)

        # If fully consumed (or close enough), trigger reproduction logic
        if self.energy <= 0.1:
            self.energy = 0
            # Logic for reproduction is handled by the consumer (Fish)
            pass

        return consumed

    def consume(self) -> "PlantGenome":
        """Consume this nectar.

        Returns:
            The parent genome for reproduction
        """
        self.energy = 0
        return self.parent_genome

    def to_state_dict(self) -> dict:
        """Serialize for frontend.

        Returns:
            State dictionary
        """
        result = {
            "type": "plant_nectar",
            "x": self.pos.x,
            "y": self.pos.y,
            "width": self.width,
            "height": self.height,
            "energy": self.energy,
            "source_plant_id": self.source_plant.plant_id if self.source_plant else None,
        }

        # Add visual properties
        if self.floral_visuals:
            result.update(self.floral_visuals)

        # Add source plant position for sway synchronization
        if self.source_plant:
            result["source_plant_x"] = self.source_plant.pos.x + self.source_plant.width / 2
            result["source_plant_y"] = self.source_plant.pos.y + self.source_plant.height
        return result
