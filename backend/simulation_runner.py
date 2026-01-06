"""Background simulation runner thread."""

import asyncio
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from core.worlds.petri.dish import PetriDish

import orjson

from backend.runner import CommandHandlerMixin
from backend.runner.state_builders import (
    build_base_stats,
    build_energy_stats,
    build_meta_stats,
    build_physical_stats,
    collect_poker_stats_payload,
)
from backend.runner.world_hooks import get_hooks_for_world
from backend.state_payloads import (
    AutoEvaluateStatsPayload,
    DeltaStatePayload,
    EntitySnapshot,
    FullStatePayload,
    PokerEventPayload,
    PokerLeaderboardEntryPayload,
    PokerStatsPayload,
    StatsPayload,
)
from backend.world_registry import create_world, get_world_metadata
from core import entities
from core.config.display import (
    FRAME_RATE,
)
from core.entities import Fish
from core.entities.plant import Plant
from core.worlds.interfaces import FAST_STEP_ACTION

logger = logging.getLogger(__name__)


class SimulationRunner(CommandHandlerMixin):
    """Runs the simulation in a background thread and provides state updates.

    Inherits command handling from CommandHandlerMixin to reduce class size.
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        world_id: Optional[str] = None,
        world_name: Optional[str] = None,
        world_type: str = "tank",
    ):
        """Initialize the simulation runner.

        Args:
            seed: Optional random seed for deterministic behavior
            world_id: Optional unique identifier for the world
            world_name: Optional human-readable name for the world
            world_type: Type of world to create (default "tank")
        """
        # Create world via registry (world-agnostic)
        self.world, self._entity_snapshot_builder = create_world(world_type, seed=seed)

        # Store world metadata for payloads
        metadata = get_world_metadata(world_type)
        self.mode_id = metadata.mode_id if metadata else world_type
        self.world_type = metadata.world_type if metadata else world_type
        self.view_mode = metadata.view_mode if metadata else "side"

        # Create world-specific hooks for feature extensions
        self.world_hooks = get_hooks_for_world(world_type)

        # Worlds start unpaused by default - they run as soon as the server starts
        self.world.paused = False

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Performance instrumentation
        self._enable_perf_logging = True
        self._perf_stats = {
            "update": {"count": 0, "total_ms": 0.0, "max_ms": 0.0},
            "snapshot": {"count": 0, "total_ms": 0.0, "max_ms": 0.0},
            "stats": {"count": 0, "total_ms": 0.0, "max_ms": 0.0},
            "serialize": {"count": 0, "total_ms": 0.0, "max_ms": 0.0},
        }

        # World identity (used for persistence, migration context, and UI attribution)
        self.world_id = world_id or str(uuid.uuid4())
        self.world_name = world_name or f"World {self.world_id[:8]}"

        self.evolution_benchmark_tracker = None

        # Target frame rate
        self.fps = FRAME_RATE
        self.frame_time = 1.0 / self.fps
        self.fast_forward = False

        # FPS Tracking
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        self.current_actual_fps = 0.0

        # Performance: Throttle WebSocket updates to reduce serialization overhead
        # Cache state and only rebuild every N frames (reduces from 30 FPS to 15 FPS)
        self.websocket_update_interval = 2  # Send every 2 frames
        self.frames_since_websocket_update = 0
        self._cached_state: Optional[Union[FullStatePayload, DeltaStatePayload]] = None
        self._cached_state_frame: Optional[int] = None
        self.delta_sync_interval = 90  # Full sync every 3 seconds (was 1 second)
        self._last_full_frame: Optional[int] = None
        self._last_entities: Dict[int, EntitySnapshot] = {}
        self._cached_gene_distributions: Dict[str, Any] = {}
        self._last_distribution_time = 0.0
        raw_distribution_interval = os.getenv("BROADCAST_DISTRIBUTIONS_INTERVAL_SECONDS", "10")
        try:
            self._distribution_interval_seconds = float(raw_distribution_interval)
        except ValueError:
            self._distribution_interval_seconds = 10.0
        if self._distribution_interval_seconds < 0:
            self._distribution_interval_seconds = 0.0

        # Initialize world-specific hooks and features
        self.world_hooks.warmup(self)

        # Migration support
        self.connection_manager = None  # Set after initialization
        self.world_manager = None  # Set after initialization
        self._migration_handler = None  # Created when dependencies are available
        self._migration_handler_deps = (None, None)  # (connection_manager, world_manager)
        self.migration_lock = threading.Lock()

        # Note: _entity_snapshot_builder is created by create_world() above

        # Inject migration support into environment for fish to access
        self._update_environment_migration_context()

    def _require_hook_attr(self, attr: str) -> None:
        """Raise AttributeError if the world hooks don't support the attribute."""
        if not hasattr(self.world_hooks, attr):
            raise AttributeError(f"{attr} not supported for world_type={self.world_type}")

    @property
    def human_poker_game(self):
        self._require_hook_attr("human_poker_game")
        return self.world_hooks.human_poker_game

    @human_poker_game.setter
    def human_poker_game(self, value):
        self._require_hook_attr("human_poker_game")
        self.world_hooks.human_poker_game = value

    @property
    def standard_poker_series(self):
        self._require_hook_attr("standard_poker_series")
        return self.world_hooks.standard_poker_series

    @standard_poker_series.setter
    def standard_poker_series(self, value):
        self._require_hook_attr("standard_poker_series")
        self.world_hooks.standard_poker_series = value

    def _get_evolution_benchmark_export_path(self) -> Path:
        """Get the benchmark export path scoped to this world."""
        world_id = getattr(self, "world_id", None) or "default"
        # Write to shared benchmarks directory to avoid creating orphan world directories
        return Path("data") / "benchmarks" / f"poker_evolution_{world_id[:8]}.json"

    def set_world_identity(self, world_id: str, world_name: Optional[str] = None) -> None:
        """Update world identity for restored/renamed worlds.

        This keeps runner-level persistence paths and migration context consistent
        with the SimulationManager's world metadata.
        """
        self.world_id = world_id
        if world_name is not None:
            self.world_name = world_name

        # Update hooks with new world identity
        if hasattr(self.world_hooks, "update_benchmark_tracker_path"):
            self.world_hooks.update_benchmark_tracker_path(self)

        self._update_environment_migration_context()

    def switch_world_type(self, new_world_type: str) -> None:
        """Switch to a different world type while preserving entities.

        This method hot-swaps between tank and petri modes without resetting
        the simulation. Both modes share the same underlying engine, so we
        just need to swap the adapter and update metadata.

        Args:
            new_world_type: Target world type ("tank" or "petri")

        Raises:
            ValueError: If switching between incompatible world types
        """
        if new_world_type == self.world_type:
            return

        # Only tank <-> petri switching is supported (they share the same engine)
        if {self.world_type, new_world_type} != {"tank", "petri"}:
            raise ValueError(
                f"Cannot hot-swap between {self.world_type} and {new_world_type}. "
                f"Only tank <-> petri switching is supported."
            )

        logger.info(
            "Hot-swapping world type from %s to %s (preserving entities)",
            self.world_type,
            new_world_type,
        )

        # Get the underlying TankWorldBackendAdapter
        if hasattr(self.world, "_tank_backend"):
            # Currently petri - extract the tank backend
            tank_backend = self.world._tank_backend
        else:
            # Currently tank
            tank_backend = self.world

        # Create the new adapter wrapping the existing tank backend
        if new_world_type == "petri":
            from core.worlds.petri.backend import PetriWorldBackendAdapter

            # Create petri adapter wrapping the existing tank backend
            new_world = PetriWorldBackendAdapter.__new__(PetriWorldBackendAdapter)
            new_world._tank_backend = tank_backend
            new_world.supports_fast_step = True
            new_world._last_step_result = None
        else:
            # Switching to tank - just use the tank backend directly
            new_world = tank_backend

        # Update runner state
        self.world = new_world
        self.world_type = new_world_type

        # Update metadata from registry
        metadata = get_world_metadata(new_world_type)
        self.mode_id = metadata.mode_id if metadata else new_world_type
        self.view_mode = metadata.view_mode if metadata else "side"

        # Update snapshot builder for the new world type
        from backend.world_registry import _SNAPSHOT_BUILDERS

        builder_factory = _SNAPSHOT_BUILDERS.get(new_world_type)
        if builder_factory:
            self._entity_snapshot_builder = builder_factory()

        # Clear cached state to force full rebuild on next get_state()
        self._invalidate_state_cache()

        # Apply or remove circular dish physics
        if new_world_type == "petri":
            self._apply_petri_physics()
        else:
            self._remove_petri_physics()

        logger.info(
            "World type switch complete: now %s (mode_id=%s, view_mode=%s)",
            new_world_type,
            self.mode_id,
            self.view_mode,
        )

    def _apply_petri_physics(self) -> None:
        """Apply circular dish physics and clamp all entities inside.

        Called when switching to Petri mode. Creates dish geometry, injects
        it into the environment, and repositions any entities outside the dish.
        """
        from core.config.display import SCREEN_HEIGHT, SCREEN_WIDTH
        from core.worlds.petri.dish import PetriDish

        # Create dish geometry matching PetriPack defaults
        rim_margin = 2.0
        radius = (min(SCREEN_WIDTH, SCREEN_HEIGHT) / 2) - rim_margin
        dish = PetriDish(
            cx=SCREEN_WIDTH / 2,
            cy=SCREEN_HEIGHT / 2,
            r=radius,
        )

        # Inject dish into environment for circular physics
        env = self.engine.environment
        if env is not None:
            env.dish = dish
            logger.info(
                "Petri physics applied: dish(cx=%.0f, cy=%.0f, r=%.0f)",
                dish.cx,
                dish.cy,
                dish.r,
            )

        # Clamp all entities inside the dish
        self._clamp_entities_to_dish(dish)

        # Swap RootSpotManager to CircularRootSpotManager
        if self.engine.plant_manager:
            from core.worlds.petri.root_spots import CircularRootSpotManager

            # Create new manager
            new_manager = CircularRootSpotManager(dish, rng=self.engine.rng)
            self.engine.plant_manager.root_spot_manager = new_manager
            logger.info("Swapped to CircularRootSpotManager")

            # Relocate existing plants to new perimeter spots
            self._relocate_plants_to_spots(new_manager)

    def _remove_petri_physics(self) -> None:
        """Remove circular dish physics when switching back to tank mode."""
        env = self.engine.environment
        if env is not None:
            env.dish = None
            logger.info("Petri physics removed: rectangular bounds restored")

        # Swap RootSpotManager back to standard (rectangular)
        if self.engine.plant_manager:
            from core.root_spots import RootSpotManager

            # Create new manager
            # Use screen dimensions from environment or defaults
            width = 800
            height = 600
            if self.engine.environment:
                width = self.engine.environment.width
                height = self.engine.environment.height

            new_manager = RootSpotManager(
                width,
                height,
                rng=self.engine.rng,
            )
            self.engine.plant_manager.root_spot_manager = new_manager
            logger.info("Swapped to standard RootSpotManager")

            # Relocate existing plants to new grid spots
            self._relocate_plants_to_spots(new_manager)

    def _relocate_plants_to_spots(self, manager: "RootSpotManager") -> None:
        """Relocate all existing plants to valid spots in the new manager.

        Args:
            manager: The new RootSpotManager instance
        """
        from core.math_utils import Vector2

        # Get all plants
        if self.engine.environment and self.engine.environment.agents:
            plants = [e for e in self.engine.environment.agents if isinstance(e, Plant)]
        else:
            plants = []
        if not plants:
            return

        # Clear old spots
        for plant in plants:
            if plant.root_spot:
                # Clear occupant reference on the old spot to be safe,
                # though the old manager is being discarded.
                plant.root_spot.occupant = None
                plant.root_spot = None

        # Assign new spots
        count = 0
        for plant in plants:
            spot = manager.get_random_empty_spot()
            if spot:
                plant.root_spot = spot
                spot.claim(plant)
                # Physically move plant to the spot
                plant.pos = Vector2(spot.x, spot.y)
                plant.rect.x = spot.x
                plant.rect.y = spot.y
                count += 1
            else:
                # No spots left (e.g. shrinking population cap)
                # Leave unrooted - reconcile_plants will likely cull it
                pass

        logger.info("Relocated %d/%d plants to new root spots", count, len(plants))

    def _clamp_entities_to_dish(self, dish: "PetriDish") -> None:
        """Reposition all agents to be inside the circular dish.

        Called after switching to Petri mode to ensure no entities are
        positioned outside the circular boundary.

        Args:
            dish: The PetriDish geometry to clamp entities within
        """
        clamped_count = 0
        for entity in self.engine.entities_list:
            if not hasattr(entity, "pos") or not hasattr(entity, "vel"):
                continue

            # Calculate agent center and radius
            agent_r = max(entity.width, getattr(entity, "height", entity.width)) / 2
            agent_cx = entity.pos.x + entity.width / 2
            agent_cy = entity.pos.y + getattr(entity, "height", entity.width) / 2

            # Clamp inside dish
            new_cx, new_cy, new_vx, new_vy, collided = dish.clamp_and_reflect(
                agent_cx,
                agent_cy,
                entity.vel.x,
                entity.vel.y,
                agent_r,
            )

            if collided:
                entity.pos.x = new_cx - entity.width / 2
                entity.pos.y = new_cy - getattr(entity, "height", entity.width) / 2
                entity.vel.x = new_vx
                entity.vel.y = new_vy
                if hasattr(entity, "rect"):
                    entity.rect.x = entity.pos.x
                    entity.rect.y = entity.pos.y
                clamped_count += 1

        if clamped_count > 0:
            logger.info("Clamped %d entities inside petri dish boundary", clamped_count)

    def _update_environment_migration_context(self) -> None:
        """Update the environment with current migration context."""
        if hasattr(self.world, "engine") and hasattr(self.world.engine, "environment"):
            env = self.world.engine.environment
            if env:
                env.connection_manager = self.connection_manager
                env.world_manager = self.world_manager
                env.world_id = self.world_id
                env.world_name = self.world_name

                # Create (or clear) a migration handler based on available dependencies.
                # Core entities depend only on the MigrationHandler protocol, while the backend
                # provides the concrete implementation.
                if self.connection_manager is not None and self.world_manager is not None:
                    deps = (self.connection_manager, self.world_manager)
                    if self._migration_handler is None or self._migration_handler_deps != deps:
                        from backend.migration_handler import MigrationHandler

                        self._migration_handler = MigrationHandler(
                            connection_manager=self.connection_manager,
                            world_manager=self.world_manager,
                        )
                        self._migration_handler_deps = deps
                    env.migration_handler = self._migration_handler
                else:
                    self._migration_handler = None
                    self._migration_handler_deps = (None, None)
                    env.migration_handler = None

                logger.info(
                    f"Migration context updated for world {self.world_id[:8] if self.world_id else 'None'}: "
                    f"conn_mgr={'SET' if self.connection_manager else 'NULL'}, "
                    f"manager={'SET' if self.world_manager else 'NULL'}"
                )
            else:
                logger.warning("Cannot update migration context: environment is None")
        else:
            logger.warning(
                "Cannot update migration context: world.engine or world.engine.environment not found"
            )

    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create a standardized error response.

        Args:
            error_msg: The error message to return

        Returns:
            Dictionary with success=False and error message
        """
        return {"success": False, "error": error_msg}

    def _invalidate_state_cache(self) -> None:
        """Clear cached state so the next request rebuilds fresh data."""

        self._cached_state = None
        self._cached_state_frame = None
        self.frames_since_websocket_update = 0
        self._last_full_frame = None
        self._last_entities.clear()
        self._cached_gene_distributions = {}
        self._last_distribution_time = 0.0

    def invalidate_state_cache(self) -> None:
        """Public wrapper to invalidate cached websocket state.

        Other backend modules (migrations/transfers) should call this instead of
        reaching into private cache implementation details.
        """

        self._invalidate_state_cache()

    @property
    def engine(self):
        """Expose the underlying simulation engine for testing."""
        return self.world.engine

    @property
    def frame_count(self) -> int:
        """Current frame count from the simulation."""
        return self.world.frame_count

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused."""
        return self.world.paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the simulation paused state."""
        self.world.paused = value

    def get_entities_snapshot(self) -> List[EntitySnapshot]:
        """Get entity snapshots for rendering (public API for RunnerProtocol).

        Returns:
            List of EntitySnapshot DTOs for all entities
        """
        return self._collect_entities()

    def get_stats(self) -> Dict[str, Any]:
        """Get current simulation statistics (public API for RunnerProtocol).

        Returns:
            Dictionary of simulation statistics
        """
        frame = self.world.frame_count
        stats_payload = self._collect_stats(frame, include_distributions=False)
        return {
            "fish_count": stats_payload.fish_count,
            "plant_count": stats_payload.plant_count,
            "food_count": stats_payload.food_count,
            "total_energy": stats_payload.total_energy,
            "fish_energy": stats_payload.fish_energy,
            "plant_energy": stats_payload.plant_energy,
            "generation": stats_payload.generation,
            "max_generation": stats_payload.max_generation,
            "fps": stats_payload.fps,
            "frame": stats_payload.frame,
            "fast_forward": stats_payload.fast_forward,
            "poker_score": stats_payload.poker_score,
            "poker_elo": stats_payload.poker_elo,
            "poker_elo_history": stats_payload.poker_elo_history,
        }

    def get_world_info(self) -> Dict[str, str]:
        """Get world metadata for frontend (public API for RunnerProtocol).

        Returns:
            Dictionary with mode_id, world_type, and view_mode
        """
        return {
            "mode_id": self.mode_id,
            "world_type": self.world_type,
            "view_mode": self.view_mode,
        }

    def _create_fish_player_data(
        self, fish: Fish, include_aggression: bool = False
    ) -> Dict[str, Any]:
        """Create fish player data dictionary.

        Args:
            fish: The fish entity
            include_aggression: If True, include aggression field for human poker games

        Returns:
            Dictionary with fish player data
        """
        from core.serializers import FishSerializer

        return FishSerializer.to_player_data(fish, include_aggression)

    def start(self, start_paused: bool = False):
        """Start the simulation in a background thread.

        Args:
            start_paused: Whether to keep the simulation paused after starting.
                Defaults to False to allow immediate frame progression in tests
                and headless runs. The backend can override to start paused
                until WebSocket broadcasting is ready.
        """

        if not self.running:
            # Override the initial paused state based on caller preference
            self.world.paused = start_paused

            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop the simulation."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> None:
        """Advance the simulation by one step."""
        with self.lock:
            # Apply agent actions if provided
            # (Tank/Petri world currently handles actions internally or via step args)
            # For now, we assume simple stepping is enough for verification tasks.

            if getattr(self.world, "supports_fast_step", False):
                self.world.step({FAST_STEP_ACTION: True})
            else:
                self.world.step()

            self._start_auto_evaluation_if_needed()
            self.fps_frame_count += 1
            self._invalidate_state_cache()

    def reset(
        self,
        seed: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Reset the world to initial state."""
        with self.lock:
            if seed is not None:
                self.seed = seed

            # create_world expects tank_type/world_type as first arg, but we call function create_world
            # self.create_world() in code refers to backend.world_registry.create_world?
            # No, self.world, self._entity_snapshot_builder = create_world(self.world_type, seed=seed)
            # We import create_world at top level

            self.world, self._entity_snapshot_builder = create_world(
                self.world_type, seed=self.seed
            )
            self.frame_count = 0
            self._invalidate_state_cache()

    def _run_loop(self):
        """Main simulation loop."""
        logger.info("Simulation loop: Starting")
        loop_iteration_count = 0

        # Drift correction: Track when the next frame *should* start
        next_frame_start_time = time.time()
        was_fast_forward = self.fast_forward

        try:
            while self.running:
                try:
                    # Advance target time by one frame duration
                    next_frame_start_time += self.frame_time
                    loop_iteration_count += 1

                    with self.lock:
                        try:
                            start_time = time.perf_counter()
                            if getattr(self.world, "supports_fast_step", False):
                                self.world.step({FAST_STEP_ACTION: True})
                            else:
                                self.world.step()
                            duration_ms = (time.perf_counter() - start_time) * 1000
                            if self._enable_perf_logging:
                                mst = self._perf_stats["update"]
                                mst["count"] += 1
                                mst["total_ms"] += duration_ms
                                if duration_ms > mst["max_ms"]:
                                    mst["max_ms"] = duration_ms
                        except Exception as e:
                            logger.error(
                                f"Simulation loop: Error updating world at frame {loop_iteration_count}: {e}",
                                exc_info=True,
                            )
                            # Continue running even if update fails

                    self._start_auto_evaluation_if_needed()

                    # Yield to keep the main server thread/event loop responsive
                    # (important for Ctrl+C handling under heavy simulation load).
                    time.sleep(0)

                    # FPS Calculation
                    self.fps_frame_count += 1
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 5.0:
                        self.current_actual_fps = self.fps_frame_count / (
                            current_time - self.last_fps_time
                        )
                        self.fps_frame_count = 0
                        self.last_fps_time = current_time
                        # Log stats periodically
                        stats = self.world.get_stats(include_distributions=False)

                        # Format perf stats if enabled
                        perf_log = ""
                        if self._enable_perf_logging:
                            parts = []
                            for key, mst in self._perf_stats.items():
                                if mst["count"] > 0:
                                    avg_ms = mst["total_ms"] / mst["count"]
                                    parts.append(f"{key}={avg_ms:.1f}ms(max {mst['max_ms']:.1f})")
                                    # Reset
                                    mst["count"] = 0
                                    mst["total_ms"] = 0.0
                                    mst["max_ms"] = 0.0
                            if parts:
                                perf_log = " | " + " ".join(parts)

                        world_label = self.world_name or self.world_id or "Unknown World"

                        # Get migration counts since last report
                        from backend.transfer_history import get_and_reset_migration_counts

                        migrations_in, migrations_out = get_and_reset_migration_counts(
                            self.world_id
                        )
                        migration_str = ""
                        if migrations_in > 0 or migrations_out > 0:
                            migration_str = f", Migrations=+{migrations_in}/-{migrations_out}"

                        # Get poker skill snapshot; show Elo + vs-expert bb/100 to avoid saturated 99% confidence
                        poker_str = ""
                        if self.evolution_benchmark_tracker is not None:
                            latest = self.evolution_benchmark_tracker.get_latest_snapshot()
                            if latest is not None:
                                mean_elo = getattr(latest, "pop_mean_elo", None)
                                best_elo = getattr(latest, "best_elo", None)
                                vs_expert_bb = getattr(latest, "pop_bb_vs_expert", None)

                                if mean_elo is not None and best_elo is not None:
                                    poker_str = f", Poker(Elo)={mean_elo:.0f}/{best_elo:.0f}"
                                if vs_expert_bb is not None:
                                    poker_str += f", vsExp={vs_expert_bb:.1f}bb/100"

                        logger.info(
                            f"{world_label} Simulation Status "
                            f"FPS={self.current_actual_fps:.1f}, "
                            f"Fish={stats.get('fish_count', 0)}, "
                            f"Plants={stats.get('plant_count', 0)}, "
                            f"Gen={stats.get('max_generation', 0)}, "
                            f"Energy={stats.get('total_energy', 0.0):.0f}"
                            f"{migration_str}{poker_str}{perf_log}"
                        )

                    # Check for mode switch that happened during step() or async
                    # If we switched from Fast Forward -> Normal, we must reset the clock
                    # to "now" to avoid sleeping for the accumulated drift.
                    if was_fast_forward and not self.fast_forward:
                        logger.info("Simulation loop: Fast forward disabled, resetting clock sync")
                        next_frame_start_time = time.time()

                    was_fast_forward = self.fast_forward

                    # Maintain frame rate with drift correction
                    if not self.fast_forward:
                        now = time.time()
                        sleep_time = next_frame_start_time - now

                        if sleep_time > 0:
                            time.sleep(sleep_time)
                        elif sleep_time < -0.1:  # Lagging by > 100ms
                            # We are falling too far behind, reset target to avoid "spiral of death"
                            # where we try to execute 0-delay frames forever to catch up
                            next_frame_start_time = now
                    else:
                        # Even in fast-forward mode, yield occasionally so signals/shutdown remain responsive.
                        time.sleep(0)

                except Exception as e:
                    logger.error(
                        f"Simulation loop: Unexpected error at frame {loop_iteration_count}: {e}",
                        exc_info=True,
                    )
                    # Use simple sleep on error to prevent tight loops
                    time.sleep(self.frame_time)
                    # Reset timing target after error recovery
                    next_frame_start_time = time.time()

        except Exception as e:
            logger.error(f"Simulation loop: Fatal error, loop exiting: {e}", exc_info=True)
        finally:
            logger.info(f"Simulation loop: Ended after {loop_iteration_count} frames")

    def _start_auto_evaluation_if_needed(self) -> None:
        """Periodically benchmark top fish against the static evaluator."""
        # AutoEvalService removed. Now using EvolutionBenchmarkTracker only.

        # Run evolution benchmark tracker (runs in background thread when due)
        self._run_evolution_benchmark_if_needed()

    def _run_evolution_benchmark_if_needed(self) -> None:
        """Run evolution benchmark if interval has passed.

        The benchmark runs in a background thread to avoid blocking the main loop.
        Results are used to track poker skill evolution over generations.
        """
        tracker = getattr(self, "evolution_benchmark_tracker", None)
        if tracker is None:
            return
        current_frame = self.world.frame_count

        paused_only = os.getenv("TANK_EVOLUTION_BENCHMARK_PAUSED_ONLY", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if paused_only and not getattr(self.world, "paused", False):
            return

        interval_seconds = float(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_SECONDS", "900"))
        now = time.time()
        last_completed = float(
            getattr(self, "_evolution_benchmark_last_completed_time", 0.0) or 0.0
        )
        if now - last_completed < interval_seconds:
            return

        guard = getattr(self, "_evolution_benchmark_guard", None)
        if guard is None:
            return

        if guard.acquire(blocking=False):
            # Run benchmark in background thread to avoid blocking
            import threading

            def run_benchmark():
                try:
                    with self.lock:
                        fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]

                    def apply_reward(fish: "Fish", amount: float) -> None:
                        with self.lock:
                            # Ensure fish is still valid/alive in the simulation
                            if fish in self.world.entities_list:
                                actual_gain = fish.modify_energy(amount)
                                if actual_gain > 0 and fish.ecosystem is not None:
                                    # We reuse the auto_eval metric for tracking
                                    fish.ecosystem.record_auto_eval_energy_gain(actual_gain)
                                logger.info(
                                    f"Benchmark Reward: Fish #{fish.fish_id} ({getattr(fish, 'generation', 0)}) gained {actual_gain:.1f} energy"
                                )

                    tracker.run_and_record(
                        fish_population=fish_list,
                        current_frame=current_frame,
                        force=True,
                        reward_callback=apply_reward,
                    )
                except Exception as e:
                    logger.error(f"Evolution benchmark failed: {e}", exc_info=True)
                finally:
                    self._evolution_benchmark_last_completed_time = time.time()
                    try:
                        guard.release()
                    except Exception:
                        pass

            thread = threading.Thread(
                target=run_benchmark,
                name="evolution_benchmark_thread",
                daemon=True,
            )
            thread.start()

    # Original _run_auto_evaluation and _reward_auto_eval_winners are removed
    # as they are now handled by the AutoEvalService.

    def get_state(self, force_full: bool = False, allow_delta: bool = True):
        """Get current simulation state for WebSocket broadcast.

        This method now supports delta compression to avoid sending the entire
        world on every frame. A full state is sent every ``delta_sync_interval``
        frames (or when ``force_full`` is True); intermediate frames only carry
        position/velocity updates plus any added/removed entities.
        """

        current_frame = self.world.frame_count
        # Try to get precise elapsed time, falling back to frame count approximation
        elapsed_time = self.world.frame_count * 33

        # Check if we can access the engine's elapsed_time directly or via adapter
        if hasattr(self.world, "engine") and hasattr(self.world.engine, "elapsed_time"):
            elapsed_time = self.world.engine.elapsed_time
        elif (
            hasattr(self.world, "world")
            and hasattr(self.world.world, "engine")
            and hasattr(self.world.world.engine, "elapsed_time")
        ):
            # Handle TankWorldBackendAdapter
            elapsed_time = self.world.world.engine.elapsed_time

        # Fast path: identical frame reuse
        if self._cached_state is not None and current_frame == self._cached_state_frame:
            return self._cached_state

        self.frames_since_websocket_update += 1
        should_rebuild = self.frames_since_websocket_update >= self.websocket_update_interval
        if not self.running:
            should_rebuild = True

        if not should_rebuild and self._cached_state is not None:
            return self._cached_state

        self.frames_since_websocket_update = 0

        # PERF: Use non-blocking lock acquisition to avoid waiting for simulation.
        # If we have cached state, return it immediately if lock is busy.
        # This eliminates the lock contention that was causing 100-1000ms delays.
        if self._cached_state is not None:
            lock_acquired = self.lock.acquire(blocking=False)
        else:
            # First frame: must wait to get initial state
            lock_acquired = self.lock.acquire(timeout=5.0)

        if not lock_acquired:
            # Lock is busy (simulation running), return cached state immediately
            if self._cached_state is not None:
                return self._cached_state
            # No cached state, create minimal emergency state
            return DeltaStatePayload(
                frame=current_frame,
                elapsed_time=elapsed_time,
                updates=[],
                added=[],
                removed=[],
                poker_events=[],
                stats=None,
            )

        try:
            # Helper to get recent poker events
            poker_events = self._collect_poker_events()

            # Calculate derived stats properly
            # Calculate derived stats properly
            # For delta frames, skip expensive genetic distribution calculations
            include_distributions = send_full = (
                force_full
                or not allow_delta
                or self._last_full_frame is None
                or (current_frame - self._last_full_frame) >= self.delta_sync_interval
            )

            start_stats = time.perf_counter()
            stats = self._collect_stats(current_frame, include_distributions=include_distributions)
            if self._enable_perf_logging:
                duration_ms = (time.perf_counter() - start_stats) * 1000
                mst = self._perf_stats["stats"]
                mst["count"] += 1
                mst["total_ms"] += duration_ms
                if duration_ms > mst["max_ms"]:
                    mst["max_ms"] = duration_ms

            # Collect entities once
            start_snap = time.perf_counter()
            entity_snapshots = self._collect_entities()
            if self._enable_perf_logging:
                duration_ms = (time.perf_counter() - start_snap) * 1000
                mst = self._perf_stats["snapshot"]
                mst["count"] += 1
                mst["total_ms"] += duration_ms
                if duration_ms > mst["max_ms"]:
                    mst["max_ms"] = duration_ms

            send_full = (
                force_full
                or not allow_delta
                or self._last_full_frame is None
                or (current_frame - self._last_full_frame) >= self.delta_sync_interval
            )

            if send_full:
                # Full state update
                self._last_full_frame = current_frame
                self._last_entities = {e.id: e for e in entity_snapshots}

                state = FullStatePayload(
                    frame=current_frame,  # Using current_frame as self.world.step_count
                    elapsed_time=elapsed_time,  # Using elapsed_time as self.world.time
                    entities=entity_snapshots,
                    stats=stats,
                    poker_events=poker_events,  # Include events in full update
                    auto_evaluation=self._collect_auto_eval(),  # Re-using existing _collect_auto_eval
                    world_id=self.world_id,
                    poker_leaderboard=self._collect_poker_leaderboard(),  # Re-using existing _collect_poker_leaderboard
                    mode_id=self.mode_id,
                    world_type=self.world_type,
                    view_mode=self.view_mode,
                )
            else:
                # Delta update
                # optimization: only send poker events if changed?
                # For now, we only send them on full updates (every 30 frames ~ 1 sec)
                # AND if explicitly requested or if we detect a change (TODO).
                # Current decision: Exclude from delta to save massive bandwidth/memory.
                # Frontend will persist the last known list.

                current_entities = {entity.id: entity for entity in entity_snapshots}
                added = [
                    entity.to_full_dict()
                    for eid, entity in current_entities.items()
                    if eid not in self._last_entities
                ]
                removed = [eid for eid in self._last_entities if eid not in current_entities]
                updates = [entity.to_delta_dict() for entity in entity_snapshots]

                state = DeltaStatePayload(
                    frame=current_frame,  # Using current_frame as self.world.step_count
                    elapsed_time=elapsed_time,  # Using elapsed_time as self.world.time
                    updates=updates,
                    added=added,
                    removed=removed,
                    stats=stats,
                    # poker_events=poker_events, # REMOVED from delta to prevent leak/bloat
                    world_id=self.world_id,
                    mode_id=self.mode_id,
                    world_type=self.world_type,
                    view_mode=self.view_mode,
                )
                self._last_entities = current_entities

            self._cached_state = state
            self._cached_state_frame = current_frame
            return state
        finally:
            self.lock.release()

    async def get_state_async(self, force_full: bool = False, allow_delta: bool = True):
        """Async wrapper to fetch simulation state without blocking the event loop."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_state, force_full, allow_delta)

    def serialize_state(self, state: Union[FullStatePayload, DeltaStatePayload]) -> bytes:
        """Serialize a state payload with fast JSON and log slow frames."""

        start = time.perf_counter()
        payload = state.to_dict() if hasattr(state, "to_dict") else state
        serialized = orjson.dumps(payload)
        duration_ms = (time.perf_counter() - start) * 1000

        if self._enable_perf_logging:
            mst = self._perf_stats["serialize"]
            mst["count"] += 1
            mst["total_ms"] += duration_ms
            if duration_ms > mst["max_ms"]:
                mst["max_ms"] = duration_ms

        # Only log if serialization itself is slow (> 50ms), not just large payloads
        if duration_ms > 50:
            logger.warning(
                "serialize_state: Frame %s slow serialization: %.2f ms, Size: %d bytes",
                getattr(state, "frame", "unknown"),
                duration_ms,
                len(serialized),
            )

        return serialized

    def _build_full_state(self, frame: int, elapsed_time: int) -> FullStatePayload:
        entities = self._collect_entities()
        stats = self._collect_stats(frame)

        # Build universal state
        state_dict = {
            "frame": frame,
            "elapsed_time": elapsed_time,
            "entities": entities,
            "stats": stats,
            "mode_id": self.mode_id,
            "world_type": self.world_type,
            "view_mode": self.view_mode,
        }

        # Add world-specific extras (poker, leaderboard, etc.) from hooks
        try:
            extras = self.world_hooks.build_world_extras(self)
            state_dict.update(extras)
        except Exception as e:
            logger.warning(f"Error building world extras from hooks: {e}")
            # Provide defaults
            state_dict["poker_events"] = []
            state_dict["poker_leaderboard"] = []
            state_dict["auto_evaluation"] = None

        return FullStatePayload(**state_dict)

    def _collect_entities(self) -> List[EntitySnapshot]:
        get_step_result = getattr(self.world, "get_last_step_result", None)
        if callable(get_step_result):
            step_result = get_step_result()
            if step_result is not None:
                return self._entity_snapshot_builder.build(step_result, self.world)

        if hasattr(self.world, "get_entities_for_snapshot"):
            live_entities = self.world.get_entities_for_snapshot()
        else:
            live_entities = getattr(self.world, "entities_list", [])

        return self._entity_snapshot_builder.collect(live_entities)

    def _collect_poker_stats_payload(self, stats: Dict[str, Any]) -> PokerStatsPayload:
        """Delegate to state_builders module."""
        return collect_poker_stats_payload(stats)

    def _collect_stats(self, frame: int, include_distributions: bool = True) -> StatsPayload:
        """Collect and organize simulation statistics."""
        # Use getattr/call to handle potential interface mismatches if world hasn't been updated
        get_stats = self.world.get_stats
        compute_distributions = include_distributions
        if include_distributions and self._distribution_interval_seconds > 0:
            now = time.perf_counter()
            if (now - self._last_distribution_time) < self._distribution_interval_seconds:
                compute_distributions = False
        else:
            now = time.perf_counter()
        try:
            stats = get_stats(include_distributions=compute_distributions)
        except TypeError:
            # Fallback for worlds that don't support include_distributions yet
            stats = get_stats()
            compute_distributions = True

        if compute_distributions:
            self._cached_gene_distributions = stats.get("gene_distributions", {})
            self._last_distribution_time = now
        elif self._cached_gene_distributions:
            stats["gene_distributions"] = self._cached_gene_distributions

        # Get Poker Score from evolution benchmark tracker
        poker_score = None
        poker_score_history: List[float] = []
        if self.evolution_benchmark_tracker is not None:
            latest = self.evolution_benchmark_tracker.get_latest_snapshot()
            if latest is not None and latest.confidence_vs_strong is not None:
                poker_score = latest.confidence_vs_strong
            history = self.evolution_benchmark_tracker.get_history()
            if history:
                valid_scores = [
                    s.confidence_vs_strong for s in history if s.confidence_vs_strong is not None
                ]
                poker_score_history = valid_scores[-20:]

        # Get Poker Elo from evolution benchmark tracker
        poker_elo = None
        poker_elo_history: List[float] = []
        if self.evolution_benchmark_tracker is not None:
            latest = self.evolution_benchmark_tracker.get_latest_snapshot()
            if latest is not None and latest.pop_mean_elo is not None:
                poker_elo = latest.pop_mean_elo
            history = self.evolution_benchmark_tracker.get_history()
            if history:
                valid_elos = [s.pop_mean_elo for s in history if s.pop_mean_elo is not None]
                poker_elo_history = valid_elos[-20:]

        # Build stat components using helper functions
        base_stats = build_base_stats(stats, frame, self.current_actual_fps, self.fast_forward)
        energy_stats = build_energy_stats(
            stats,
            poker_score,
            poker_score_history,
            poker_elo,
            poker_elo_history,
        )
        physical_stats = build_physical_stats(stats)
        meta_stats = build_meta_stats(stats)
        poker_stats = collect_poker_stats_payload(stats)

        return StatsPayload(
            **base_stats,
            **energy_stats,
            **physical_stats,
            poker_stats=poker_stats,
            meta_stats=meta_stats,
        )

    def _collect_poker_events(self) -> List[PokerEventPayload]:
        poker_events: List[PokerEventPayload] = []
        recent_events = self.world.engine.poker_events
        for event in recent_events:
            if "Standard Algorithm" in event["message"] or "Auto-eval" in event["message"]:
                continue

            poker_events.append(
                PokerEventPayload(
                    frame=event["frame"],
                    winner_id=event["winner_id"],
                    loser_id=event["loser_id"],
                    winner_hand=event["winner_hand"],
                    loser_hand=event["loser_hand"],
                    energy_transferred=event["energy_transferred"],
                    message=event["message"],
                    is_plant=event.get("is_plant", False),
                    plant_id=event.get("plant_id", None),
                )
            )

        return poker_events

    def _collect_poker_leaderboard(self) -> List[PokerLeaderboardEntryPayload]:
        # Guard: Only fish-based worlds have ecosystem with poker leaderboard
        if not hasattr(self.world, "ecosystem") or not hasattr(
            self.world.ecosystem, "get_poker_leaderboard"
        ):
            return []

        fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]
        leaderboard_data = self.world.ecosystem.get_poker_leaderboard(
            fish_list=fish_list, limit=10, sort_by="net_energy"
        )
        return [PokerLeaderboardEntryPayload(**entry) for entry in leaderboard_data]

    def get_full_evaluation_history(self) -> List[Dict[str, Any]]:
        """Return the full auto-evaluation history."""
        return []

    def get_evolution_benchmark_data(self) -> Dict[str, Any]:
        """Return the evolution benchmark tracking data.

        Returns:
            Dictionary with benchmark history, improvement metrics, and latest snapshot.
            Returns empty dict with status if tracker not available.
        """
        tracker = getattr(self, "evolution_benchmark_tracker", None)
        if tracker is None:
            return {"status": "not_available", "history": [], "improvement": {}, "latest": None}

        return tracker.get_api_data()

    def _collect_auto_eval(self) -> Optional[AutoEvaluateStatsPayload]:
        return None

    def _entity_to_data(self, entity: entities.Agent) -> Optional[EntitySnapshot]:
        """Convert an entity to a lightweight snapshot for serialization.

        Kept for compatibility/greppability; delegates to `EntitySnapshotBuilder`.
        """

        return self._entity_snapshot_builder.to_snapshot(entity)

    def handle_command(self, command: str, data: Optional[Dict[str, Any]] = None):
        """Handle a command from the client.

        Commands can be:
        1. Universal: pause, resume, reset, fast_forward (supported by all worlds)
        2. World-specific: poker, human poker, etc. (delegated to hooks)
        3. Tank-specific: add_food, spawn_fish, set_plant_energy_input

        Args:
            command: Command type
            data: Optional command data
        """
        data = data or {}

        # Try world-specific hooks first
        with self.lock:
            # Check if hooks handle this command
            if self.world_hooks.supports_command(command):
                try:
                    result = self.world_hooks.handle_command(self, command, data)
                    if result is not None:
                        return result
                except Exception as e:
                    logger.error(f"Error handling command {command} via hooks: {e}")
                    return self._create_error_response(f"Error handling {command}: {e}")

            # Map universal and tank commands to handler methods
            universal_handlers = {
                "pause": self._cmd_pause,
                "resume": self._cmd_resume,
                "reset": self._cmd_reset,
                "fast_forward": self._cmd_fast_forward,
            }

            tank_handlers = {
                "add_food": self._cmd_add_food,
                "spawn_fish": self._cmd_spawn_fish,
                "start_poker": self._cmd_start_poker,
                "poker_action": self._cmd_poker_action,
                "poker_process_ai_turn": self._cmd_poker_process_ai_turn,
                "poker_new_round": self._cmd_poker_new_round,
                "poker_autopilot_action": self._cmd_poker_autopilot_action,
                "standard_poker_series": self._cmd_standard_poker_series,
                "set_plant_energy_input": self._cmd_set_plant_energy_input,
            }

            # Try universal handlers first
            handler = universal_handlers.get(command)
            if handler:
                return handler(data)

            # Try fish-world handlers (tank, petri - any world with fish/poker)
            if command in tank_handlers:
                # Check if world supports fish-based commands
                metadata = get_world_metadata(self.world_type)
                has_fish = metadata.has_fish if metadata else (self.world_type == "tank")
                if not has_fish:
                    return self._create_error_response(
                        f"Command '{command}' not supported for world_type={self.world_type}"
                    )
                handler = tank_handlers[command]
                return handler(data)

            # Log unknown command
            logger.warning(f"Unknown command received: {command}")
            return self._create_error_response(f"Unknown command: {command}")

    async def handle_command_async(self, command: str, data: Optional[Dict[str, Any]] = None):
        """Async wrapper to route commands off the event loop thread."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.handle_command, command, data)
