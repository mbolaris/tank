"""Plant entity with evolving L-system genetics.

This module implements plants that grow from root spots,
collect energy passively, produce nectar for reproduction, and
can play poker against fish.

This replaces the old 'Plant' and 'FractalPlant' classes with a single unified 'Plant'.
"""

import logging
from typing import TYPE_CHECKING, Optional

from core.entities.base import Agent
from core.entities.resources import Food
from core.entity_ids import PlantId
from core.genetics import PlantGenome
from core.state_machine import EntityState

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.root_spots import RootSpot
    from core.world import World


# Plant lifecycle constants (can be moved to constants.py later)
from core.config.plants import (
    PLANT_BASE_HEIGHT,
    PLANT_BASE_WIDTH,
    PLANT_DAWN_DUSK_MODIFIER,
    PLANT_DAY_MODIFIER,
    PLANT_DEATH_ENERGY,
    PLANT_ENERGY_GAIN_MULTIPLIER,
    PLANT_INITIAL_ENERGY,
    PLANT_MAX_ENERGY,
    PLANT_MAX_SIZE,
    PLANT_MIN_ENERGY_GAIN,
    PLANT_MIN_POKER_ENERGY,
    PLANT_MIN_SIZE,
    PLANT_NECTAR_COOLDOWN,
    PLANT_NECTAR_ENERGY,
    PLANT_NIGHT_MODIFIER,
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

    Attributes:
        plant_id: Unique identifier
        genome: PlantGenome with L-system parameters and traits
        energy: Current energy level (determines size)
        max_energy: Maximum energy capacity
        root_spot: The RootSpot this plant is anchored to
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
        root_spot: "RootSpot",
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
        self.energy = initial_energy
        self.max_energy = PLANT_MAX_ENERGY * genome.growth_efficiency
        self.ecosystem = ecosystem

        # Cooldowns
        self.poker_cooldown = 0
        self.nectar_cooldown = PLANT_NECTAR_COOLDOWN // 2  # Start partially ready

        # Migration timer - check for migration every 300 frames (5 seconds at 60fps)
        # Add random offset to prevent synchronized migrations (use environment RNG)
        self.migration_check_interval = 300
        rng = getattr(environment, "rng", None)
        if rng is None:
            raise RuntimeError("environment.rng is required for deterministic plant initialization")
        self.migration_timer = rng.randint(0, self.migration_check_interval)

        # Statistics
        self.age = 0
        self.nectar_produced = 0
        self.poker_wins = 0
        self.poker_losses = 0

        # Poker state
        self.last_button_position = 2
        self.poker_effect_state: Optional[dict] = None
        self.poker_effect_timer = 0

        # Rendering stability
        self._cached_iterations = 1  # Cache iterations to prevent flickering

        # Type-safe ID wrapper (cached to avoid repeated object creation)
        self._typed_id: Optional[PlantId] = None

        # Update size based on initial energy
        self._update_size()

    def _update_size(self) -> None:
        """Update plant size based on current energy."""
        # Size scales with energy
        energy_ratio = self.energy / self.max_energy
        size_multiplier = PLANT_MIN_SIZE + ((PLANT_MAX_SIZE - PLANT_MIN_SIZE) * energy_ratio)

        self.set_size(
            PLANT_BASE_WIDTH * size_multiplier,
            PLANT_BASE_HEIGHT * size_multiplier,
        )

        # Anchor using root spot semantics (bottom vs center)
        if hasattr(self.root_spot, "get_anchor_topleft"):
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

        # Update cooldowns
        if self.poker_cooldown > 0:
            self.poker_cooldown -= 1
        if self.nectar_cooldown > 0:
            self.nectar_cooldown -= 1

        # Update poker effect timer
        if self.poker_effect_timer > 0:
            self.poker_effect_timer -= 1
            if self.poker_effect_timer <= 0:
                self.poker_effect_state = None

        # Update migration timer and check for migration
        self.migration_timer += 1
        if self.migration_timer >= self.migration_check_interval:
            self.migration_timer = 0
            self._check_migration()

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

    def _collect_energy(self, time_of_day: Optional[float] = None) -> None:
        """Collect passive energy.

        Energy collection rate increases with current energy (compound growth).
        Photosynthesis rate varies with time of day:
        - Day (0.35-0.65): Full rate
        - Dawn/Dusk: 70% rate
        - Night: 30% rate

        Args:
            time_of_day: Normalized time of day (0.0-1.0), None defaults to full power
        """
        # Base rate from genome
        base_rate = self.genome.base_energy_rate

        # Compound growth factor with seedling boost
        # Large plants (>30% energy): standard compound growth 1.0-1.5x
        # Small plants (<30% energy): seedling boost to help recovery (1.5-2.0x)
        # This prevents the "rich get richer" problem where small plants struggle
        energy_ratio = self.energy / self.max_energy

        if energy_ratio < 0.3:
            # Seedling boost: inverse relationship - smaller plants grow faster
            # At 0% energy: 3.0x, at 30% energy: 1.5x (smooth transition to standard)
            # This aggressive boost helps small plants recover quickly after poker losses
            seedling_boost = 3.0 - (energy_ratio / 0.3) * 1.5
            growth_factor = seedling_boost
        else:
            # Standard compound growth for established plants (1.0-1.5x)
            # Uses sqrt to prevent runaway growth
            growth_factor = 1.0 + (energy_ratio**0.5) * 0.5

        # Calculate photosynthesis modifier based on time of day
        # This was previously incorrectly using fish activity modifier (0.5-1.0)
        # Plants need their own photosynthesis logic: Day=1.0, Dawn/Dusk=0.7, Night=0.3
        if time_of_day is None:
            photosynthesis_modifier = PLANT_DAY_MODIFIER
        elif 0.35 <= time_of_day <= 0.65:
            # Full daylight (middle 30% of the day)
            photosynthesis_modifier = PLANT_DAY_MODIFIER
        elif 0.25 <= time_of_day < 0.35 or 0.65 < time_of_day <= 0.75:
            # Dawn (0.25-0.35) or Dusk (0.65-0.75)
            photosynthesis_modifier = PLANT_DAWN_DUSK_MODIFIER
        else:
            # Night (before 0.25 or after 0.75)
            photosynthesis_modifier = PLANT_NIGHT_MODIFIER

        energy_gain = base_rate * growth_factor * photosynthesis_modifier
        energy_gain *= PLANT_ENERGY_GAIN_MULTIPLIER

        # Reduce energy production if neighboring root slots are occupied.
        # If both adjacent slots are full -> -50%, if one is full -> -25%.
        reduction_factor = 1.0
        if self.root_spot is not None and getattr(self.root_spot, "manager", None) is not None:
            manager = self.root_spot.manager
            left_spot = manager.get_spot_by_id(self.root_spot.spot_id - 1)
            right_spot = manager.get_spot_by_id(self.root_spot.spot_id + 1)

            occupied_count = 0
            if left_spot is not None and left_spot.occupied:
                occupied_count += 1
            if right_spot is not None and right_spot.occupied:
                occupied_count += 1

            if occupied_count == 2:
                reduction_factor = 0.5
            elif occupied_count == 1:
                reduction_factor = 0.75

        energy_gain *= reduction_factor

        # Cosmic Fern variants have a small energy collection bonus
        if getattr(self.genome, "type", "lsystem") == "cosmic_fern":
            energy_gain *= 1.1

        # Apply minimum energy gain floor - read from runtime config if available
        min_energy_gain = PLANT_MIN_ENERGY_GAIN  # Default from constants
        config = getattr(self.environment, "simulation_config", None)
        if config is not None:
            plant_config = getattr(config, "plant", None)
            if plant_config is not None:
                min_energy_gain = getattr(
                    plant_config, "plant_energy_input_rate", PLANT_MIN_ENERGY_GAIN
                )

        energy_gain = max(energy_gain, min_energy_gain)

        before = self.energy
        self.energy = min(self.max_energy, self.energy + energy_gain)
        # Energy accounting via ingest_energy_deltas(), no events emitted

    def _try_produce_nectar(self, time_of_day: Optional[float]) -> Optional["PlantNectar"]:
        """Try to produce nectar if conditions are met.

        Args:
            time_of_day: Normalized time of day

        Returns:
            PlantNectar if produced, None otherwise
        """
        # Must be able to afford nectar
        if self.energy < PLANT_NECTAR_ENERGY:
            return None

        # Must be at 90% energy to look "full grown" when producing
        energy_ratio = self.energy / self.max_energy
        if energy_ratio < 0.90:
            return None

        # Check cooldown
        if self.nectar_cooldown > 0:
            return None

        # Produce nectar
        self.nectar_cooldown = PLANT_NECTAR_COOLDOWN
        self.nectar_produced += 1
        self.lose_energy(PLANT_NECTAR_ENERGY, source="nectar")

        # Nectar spawns in the upper portion of the plant visual
        # The visual plant only fills about 50-70% of the bounding box height
        # pos.y is top of bounding box, pos.y + height is bottom/base
        # We need to offset from the visual tree top, not the bounding box

        # Use a fixed offset from the TOP of the bounding box (where branches are)
        # Random position in top 15% of the visual tree (which is upper portion of bbox)
        # Use environment RNG for determinism
        rng = getattr(self.environment, "rng", None)
        if rng is None:
            raise RuntimeError("environment.rng is required for deterministic nectar production")
        top_offset_pct = rng.uniform(0.02, 0.15)  # 2-15% down from top of bbox

        nectar_x = self.pos.x + self.width / 2
        nectar_y = self.pos.y + self.height * top_offset_pct

        # Store as distance from base for update_position compatibility
        base_y = self.pos.y + self.height
        relative_y_offset_pct = (base_y - nectar_y) / self.height

        # Import here to avoid circular imports
        # Note: In the same file in the new structure
        # from core.entities.plant import PlantNectar

        # Determine visuals based on strategy
        floral_visuals = {}
        if self.genome.strategy_type:
            try:
                from core.plants.plant_strategy_types import (
                    PlantStrategyType,
                    get_strategy_visual_config,
                )

                strategy_type = PlantStrategyType(self.genome.strategy_type)
                config = get_strategy_visual_config(strategy_type)

                # Calculate average hue from range for consistent look
                hue = (config.color_hue_range[0] + config.color_hue_range[1]) / 2
                sat = (config.color_saturation_range[0] + config.color_saturation_range[1]) / 2

                floral_visuals = {
                    "floral_type": config.floral_type,
                    "floral_petals": config.floral_petals,
                    "floral_layers": config.floral_layers,
                    "floral_spin": config.floral_spin,
                    "floral_hue": hue,
                    "floral_saturation": sat,
                }
            except Exception:
                pass

        # If no strategy specific visuals (e.g. evolved/legacy plant), use genome colors
        if not floral_visuals:
            floral_visuals = {
                "floral_type": "vortex",  # Default
                "floral_hue": self.genome.color_hue,
                "floral_saturation": self.genome.color_saturation,
                "floral_petals": 5,
                "floral_layers": 3,
                "floral_spin": 1.0,
            }

        return PlantNectar(
            environment=self.environment,
            x=nectar_x,
            y=nectar_y,
            source_plant=self,
            relative_y_offset_pct=relative_y_offset_pct,
            floral_visuals=floral_visuals,
        )

    def can_play_poker(self) -> bool:
        """Check if plant can play poker.

        Returns:
            True if poker game can proceed
        """
        if self.is_dead():
            return False
        if self.energy < PLANT_MIN_POKER_ENERGY:
            return False
        if self.poker_cooldown > 0:
            return False
        return True

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Adjust plant energy by `amount` and return the actual internal-store delta.

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

        before = self.energy

        if amount > 0:
            target = before + amount
            if target > self.max_energy:
                overflow = target - self.max_energy
                self.energy = self.max_energy
                self._route_overflow_energy(overflow)
            else:
                self.energy = target
        else:
            actual_loss = min(before, -amount)
            self.energy = before - actual_loss

        self._update_size()

        delta = self.energy - before

        # Record the delta via the engine recorder (single source of truth)
        # Energy events are no longer emitted to avoid double-counting
        if hasattr(self, "environment") and hasattr(self.environment, "record_energy_delta"):
            self.environment.record_energy_delta(self, delta, source)

        return delta

    def lose_energy(self, amount: float, *, source: str = "poker") -> float:
        """Lose energy (from poker loss or being eaten).

        .. deprecated::
            Use `modify_energy(-amount, source=source)` instead.

        Args:
            amount: Energy to lose

        Returns:
            Actual amount lost
        """
        actual_loss = min(self.energy, amount)
        before = self.energy
        self.energy -= actual_loss
        self._update_size()
        if actual_loss > 0:
            logger.debug(
                f"Plant #{self.plant_id} lost {actual_loss:.1f} energy ({source}): {before:.1f} -> {self.energy:.1f}"
            )
            # Energy events no longer emitted - accounting via ingest_energy_deltas()
        return actual_loss

    def gain_energy(self, amount: float, *, source: str = "poker") -> float:
        """Gain energy (from poker win).

        .. deprecated::
            Use `modify_energy(amount, source=source)` instead.

        Args:
            amount: Energy to gain
            source: Source of the energy gain (for tracking)

        Returns:
            Actual amount gained (including overflow that was routed)
        """
        if amount <= 0:
            return 0.0

        new_energy = self.energy + amount

        if new_energy > self.max_energy:
            overflow = new_energy - self.max_energy
            self.energy = self.max_energy
            self._route_overflow_energy(overflow)
        else:
            self.energy = new_energy
            overflow = 0.0

        self._update_size()
        # Energy events no longer emitted - accounting via ingest_energy_deltas()
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
            # Energy accounting via ingest_energy_deltas(), no events emitted
        except Exception:
            pass  # Energy lost on failure is acceptable

    def is_dead(self) -> bool:
        """Check if plant is dead (energy too low) or has migrated.

        Returns:
            True if plant should be removed
        """
        # Check explicit state first (e.g. migrated)
        if self.state.state in (EntityState.DEAD, EntityState.REMOVED):
            return True

        # Check condition-based death (low energy)
        if self.energy < PLANT_DEATH_ENERGY:
            logger.debug(
                f"Plant #{self.plant_id} died from low energy ({self.energy:.1f} < {PLANT_DEATH_ENERGY})"
            )
            self.state.transition(EntityState.DEAD, reason="low_energy")
            return True

        return False

    def get_size_multiplier(self) -> float:
        """Get current size multiplier for rendering.

        Returns:
            Size multiplier (0.3 to 1.5)
        """
        energy_ratio = self.energy / self.max_energy
        return PLANT_MIN_SIZE + ((PLANT_MAX_SIZE - PLANT_MIN_SIZE) * energy_ratio)

    def get_fractal_iterations(self) -> int:
        """Get number of L-system iterations based on size.

        Larger plants have more detailed fractals.

        Returns:
            Number of iterations (1-3)
        """
        size = self.get_size_multiplier()

        # Use hysteresis to prevent flickering between iteration levels
        # Only upgrade when well past the threshold, downgrade when well below

        target_iterations = 1
        if size >= 1.0:
            target_iterations = 3
        elif size >= 0.6:
            target_iterations = 2

        # Apply hysteresis
        if target_iterations > self._cached_iterations:
            # Upgrade requires being 10% past the threshold to prevent rapid switching
            if (target_iterations == 2 and size > 0.65) or (target_iterations == 3 and size > 1.05):
                self._cached_iterations = target_iterations
        elif target_iterations < self._cached_iterations:
            # Downgrade is immediate to reflect energy loss, but we respect the thresholds
            self._cached_iterations = target_iterations

        return self._cached_iterations

    def get_poker_aggression(self) -> float:
        """Get poker aggression level.

        Returns:
            Aggression value for poker decisions (0.0-1.0)
        """
        return self.genome.aggression

    def get_poker_strategy(self):
        """Get poker strategy for this plant.

        If this plant has a strategy_type set (baseline strategy plant),
        returns the corresponding baseline poker strategy implementation.
        Otherwise falls back to the genome-based adapter.

        Returns:
            PokerStrategyAlgorithm: Either a baseline strategy or PlantPokerStrategyAdapter
        """
        # Check if this is a baseline strategy plant
        if self.genome.strategy_type is not None:
            from core.plants.plant_strategy_types import (
                PlantStrategyType,
                get_poker_strategy_for_type,
            )

            try:
                strategy_type = PlantStrategyType(self.genome.strategy_type)
                # Use environment RNG if available for determinism
                rng = getattr(self.environment, "rng", None)
                return get_poker_strategy_for_type(strategy_type, rng=rng)
            except ValueError:
                pass  # Fall through to genome-based strategy

        # Fall back to genome-based strategy (legacy behavior)
        from core.plant_poker_strategy import PlantPokerStrategyAdapter

        return PlantPokerStrategyAdapter(self.genome)

    def get_poker_id(self) -> int:
        """Get stable ID for poker tracking.

        Returns:
            plant_id offset by 100000 to avoid collision with fish IDs
        """
        return self.plant_id + 100000

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
        self.poker_effect_state = {
            "status": status,
            "amount": amount,
            "target_id": target_id,
            "target_type": target_type,
        }
        self.poker_effect_timer = duration

    def die(self) -> None:
        """Handle plant death - release root spot."""
        if self.root_spot is not None:
            # Only release if we actually own the spot; protects against
            # duplicate plants under concurrency/migration races.
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

    def _check_migration(self) -> None:
        """Check if plant should attempt migration based on root spot position."""
        if self.root_spot is None:
            return

        # Determine if this plant is in an edge position
        # Edge positions are the first 2 or last 2 spots out of 25
        total_spots = (
            len(self.root_spot.manager.spots) if hasattr(self.root_spot, "manager") else 25
        )
        edge_threshold = 2  # Consider first 2 and last 2 spots as "edge"

        spot_id = self.root_spot.spot_id
        direction = None

        if spot_id < edge_threshold:
            # Leftmost positions - can migrate left
            direction = "left"
        elif spot_id >= total_spots - edge_threshold:
            # Rightmost positions - can migrate right
            direction = "right"

        if direction is not None:
            # Attempt migration with a probability (20% per check)
            # This makes migration less aggressive than guaranteed (use environment RNG)
            rng = getattr(self.environment, "rng", None)
            if rng is None:
                raise RuntimeError("environment.rng is required for deterministic migration")
            if rng.random() < 0.20:
                self._attempt_migration(direction)

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

        tank_id = getattr(self.environment, "tank_id", None)
        if tank_id is None:
            return False

        # Delegate migration logic to the handler (backend implementation)
        try:
            success = migration_handler.attempt_entity_migration(self, direction, tank_id)

            if success:
                # Mark this plant for removal from source tank
                self.state.transition(EntityState.REMOVED, reason="migration")
                logger.debug(f"Plant #{self.plant_id} successfully migrated {direction}")

            return success

        except Exception as e:
            logger.error(f"Plant migration failed: {e}", exc_info=True)
            return False

    def to_state_dict(self) -> dict:
        """Serialize plant state for frontend rendering.

        Returns:
            Dictionary with plant state
        """
        # NOTE: returning type="plant" to maintain compatibility with frontend renderer
        return {
            "type": "plant",
            "id": self.plant_id,
            "x": self.pos.x,
            "y": self.pos.y,
            "width": self.width,
            "height": self.height,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "size_multiplier": self.get_size_multiplier(),
            "iterations": self.get_fractal_iterations(),
            "genome": self.genome.to_dict(),
            "age": self.age,
            "nectar_ready": self.nectar_cooldown == 0
            and self.energy >= PLANT_NECTAR_ENERGY
            and self.energy / self.max_energy >= 0.90,
            "poker_effect_state": self.poker_effect_state,
        }


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
            # But we need to ensure the consumer knows this is special nectar
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
