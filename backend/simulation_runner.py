"""Background simulation runner thread."""

import asyncio
import os
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import orjson

from backend.runner import CommandHandlerMixin
from backend.runner.state_builders import (
    build_base_stats,
    build_energy_stats,
    build_meta_stats,
    build_physical_stats,
    collect_poker_stats_payload,
)

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
from backend.entity_snapshot_builder import EntitySnapshotBuilder
from backend.world_registry import create_world, get_world_metadata
from core import entities, movement_strategy
from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.config.display import (
    FILES,
    FRAME_RATE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.config.ecosystem import SPAWN_MARGIN_PIXELS
from core.entities import Fish
from core.entities.plant import Plant
from core.genetics import Genome
from core.human_poker_game import HumanPokerGame
from core.plant_poker_strategy import PlantPokerStrategyAdapter

logger = logging.getLogger(__name__)


class SimulationRunner(CommandHandlerMixin):
    """Runs the simulation in a background thread and provides state updates.

    Inherits command handling from CommandHandlerMixin to reduce class size.
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        tank_id: Optional[str] = None,
        tank_name: Optional[str] = None,
        world_type: str = "tank",
    ):
        """Initialize the simulation runner.

        Args:
            seed: Optional random seed for deterministic behavior
            tank_id: Optional unique identifier for the tank
            tank_name: Optional human-readable name for the tank
            world_type: Type of world to create (default "tank")
        """
        # Create world via registry (world-agnostic)
        self.world, self._entity_snapshot_builder = create_world(world_type, seed=seed)

        # Store world metadata for payloads
        metadata = get_world_metadata(world_type)
        self.world_type = world_type
        self.view_mode = metadata.view_mode if metadata else "side"

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

        # Tank identity (used for persistence, migration context, and UI attribution)
        self.tank_id = tank_id or str(uuid.uuid4())
        self.tank_name = tank_name or f"Tank {self.tank_id[:8]}"

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

        # Human poker game management
        self.human_poker_game: Optional[HumanPokerGame] = None

        # Static benchmark poker series management
        self.standard_poker_series: Optional[AutoEvaluatePokerGame] = None

        # Evolution benchmark tracker for longitudinal skill measurement
        # Enabled by default (can cause FPS drops during benchmark); set TANK_EVOLUTION_BENCHMARK_ENABLED=0 to disable.
        self.evolution_benchmark_tracker = None
        if os.getenv("TANK_EVOLUTION_BENCHMARK_ENABLED", "1").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        ):
            from core.poker.evaluation.evolution_benchmark_tracker import (
                EvolutionBenchmarkTracker,
            )
            self.evolution_benchmark_tracker = EvolutionBenchmarkTracker(
                eval_interval_frames=int(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_FRAMES", "27000")),
                export_path=self._get_evolution_benchmark_export_path(),
                use_quick_benchmark=True,
            )
            self._evolution_benchmark_guard = threading.Lock()
            # Initialize to (now - interval + 60 seconds) so first benchmark runs after ~60 seconds of startup
            # This gives the simulation time to populate fish before the first evaluation
            initial_delay = 60.0
            interval = float(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_SECONDS", "900"))
            self._evolution_benchmark_last_completed_time = time.time() - interval + initial_delay
        else:
            self._evolution_benchmark_guard = None
            self._evolution_benchmark_last_completed_time = 0.0

        # Migration support
        self.connection_manager = None  # Set after initialization
        self.tank_registry = None  # Set after initialization
        self._migration_handler = None  # Created when dependencies are available
        self._migration_handler_deps = (None, None)  # (connection_manager, tank_registry)
        self.migration_lock = threading.Lock()

        # Note: _entity_snapshot_builder is created by create_world() above

        # Inject migration support into environment for fish to access
        self._update_environment_migration_context()

    def _get_evolution_benchmark_export_path(self) -> Path:
        """Get the benchmark export path scoped to this tank."""
        tank_id = getattr(self, "tank_id", None) or "default"
        return Path("data") / "tanks" / tank_id / "poker_evolution_benchmark.json"

    def set_tank_identity(self, tank_id: str, tank_name: Optional[str] = None) -> None:
        """Update tank identity for restored/renamed tanks.

        This keeps runner-level persistence paths and migration context consistent
        with the SimulationManager's tank metadata.
        """
        self.tank_id = tank_id
        if tank_name is not None:
            self.tank_name = tank_name

        tracker = getattr(self, "evolution_benchmark_tracker", None)
        if tracker is not None:
            tracker.export_path = self._get_evolution_benchmark_export_path()

        self._update_environment_migration_context()

    def _update_environment_migration_context(self) -> None:
        """Update the environment with current migration context."""
        if hasattr(self.world, 'engine') and hasattr(self.world.engine, 'environment'):
            env = self.world.engine.environment
            if env:
                env.connection_manager = self.connection_manager
                env.tank_registry = self.tank_registry
                env.tank_id = self.tank_id
                env.tank_name = self.tank_name

                # Create (or clear) a migration handler based on available dependencies.
                # Core entities depend only on the MigrationHandler protocol, while the backend
                # provides the concrete implementation.
                if self.connection_manager is not None and self.tank_registry is not None:
                    deps = (self.connection_manager, self.tank_registry)
                    if self._migration_handler is None or self._migration_handler_deps != deps:
                        from backend.migration_handler import MigrationHandler

                        self._migration_handler = MigrationHandler(
                            connection_manager=self.connection_manager,
                            tank_registry=self.tank_registry,
                        )
                        self._migration_handler_deps = deps
                    env.migration_handler = self._migration_handler
                else:
                    self._migration_handler = None
                    self._migration_handler_deps = (None, None)
                    env.migration_handler = None

                logger.info(
                    f"Migration context updated for tank {self.tank_id[:8] if self.tank_id else 'None'}: "
                    f"conn_mgr={'SET' if self.connection_manager else 'NULL'}, "
                    f"registry={'SET' if self.tank_registry else 'NULL'}"
                )
            else:
                logger.warning("Cannot update migration context: environment is None")
        else:
            logger.warning("Cannot update migration context: world.engine or world.engine.environment not found")

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
        """Expose the underlying simulation engine for compatibility/testing."""

        return self.world.engine

    def _create_fish_player_data(self, fish: Fish, include_aggression: bool = False) -> Dict[str, Any]:
        """Create fish player data dictionary.

        Args:
            fish: The fish entity
            include_aggression: If True, include aggression field for human poker games

        Returns:
            Dictionary with fish player data
        """
        from core.serializers import FishSerializer
        return FishSerializer.to_player_data(fish, include_aggression)

    def _create_plant_player_data(self, plant: Plant) -> Dict[str, Any]:
        """Create benchmark player metadata for a plant."""
        from core.serializers import PlantSerializer
        return PlantSerializer.to_player_data(plant)

    def _get_fish_genome_data(self, fish: Fish) -> Optional[Dict[str, Any]]:
        """Extract visual genome data for a fish to mirror tank rendering."""
        from core.serializers import FishSerializer
        return FishSerializer.to_genome_data(fish)

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
                            self.world.update()
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
                        self.current_actual_fps = self.fps_frame_count / (current_time - self.last_fps_time)
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
                                
                        tank_label = self.tank_name or self.tank_id or "Unknown Tank"

                        
                        # Get migration counts since last report
                        from backend.transfer_history import get_and_reset_migration_counts
                        migrations_in, migrations_out = get_and_reset_migration_counts(self.tank_id)
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
                            f"{tank_label} Simulation Status "
                            f"FPS={self.current_actual_fps:.1f}, "
                            f"Fish={stats.get('fish_count', 0)}, "
                            f"Plants={stats.get('plant_count', 0)}, "
                            f"Gen={stats.get('max_generation', 0)}, "
                            f"Energy={stats.get('total_energy', 0.0):.0f}"
                            f"{migration_str}{poker_str}{perf_log}"
                        )

                    # Check for mode switch that happened during update() or async
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
                    logger.error(f"Simulation loop: Unexpected error at frame {loop_iteration_count}: {e}", exc_info=True)
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
        # AutoEvalService removed (legacy). Now using EvolutionBenchmarkTracker only.

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
        last_completed = float(getattr(self, "_evolution_benchmark_last_completed_time", 0.0) or 0.0)
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
                                logger.info(f"Benchmark Reward: Fish #{fish.fish_id} ({getattr(fish, 'generation', 0)}) gained {actual_gain:.1f} energy")

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
        elif hasattr(self.world, "world") and hasattr(self.world.world, "engine") and hasattr(self.world.world.engine, "elapsed_time"):
            # Handle TankWorldBackendAdapter
            elapsed_time = self.world.world.engine.elapsed_time

        # Fast path: identical frame reuse
        if self._cached_state is not None and current_frame == self._cached_state_frame:
            return self._cached_state

        self.frames_since_websocket_update += 1
        should_rebuild = self.frames_since_websocket_update >= self.websocket_update_interval

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
            stats = self._collect_stats(
                current_frame, include_distributions=include_distributions
            )
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
                    frame=current_frame, # Using current_frame as self.world.step_count
                    elapsed_time=elapsed_time, # Using elapsed_time as self.world.time
                    entities=entity_snapshots,
                    stats=stats,
                    poker_events=poker_events, # Include events in full update
                    auto_evaluation=self._collect_auto_eval(), # Re-using existing _collect_auto_eval
                    tank_id=self.tank_id,
                    poker_leaderboard=self._collect_poker_leaderboard(), # Re-using existing _collect_poker_leaderboard
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
                added = [entity.to_full_dict() for eid, entity in current_entities.items() if eid not in self._last_entities]
                removed = [eid for eid in self._last_entities if eid not in current_entities]
                updates = [entity.to_delta_dict() for entity in entity_snapshots]
                
                state = DeltaStatePayload(
                    frame=current_frame, # Using current_frame as self.world.step_count
                    elapsed_time=elapsed_time, # Using elapsed_time as self.world.time
                    updates=updates,
                    added=added,
                    removed=removed,
                    stats=stats,
                    # poker_events=poker_events, # REMOVED from delta to prevent leak/bloat
                    tank_id=self.tank_id,
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
        return await loop.run_in_executor(
            None, self.get_state, force_full, allow_delta
        )

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
        poker_events = self._collect_poker_events()
        poker_leaderboard = self._collect_poker_leaderboard()
        auto_eval = self._collect_auto_eval()

        return FullStatePayload(
            frame=frame,
            elapsed_time=elapsed_time,
            entities=entities,
            stats=stats,
            poker_events=poker_events,
            poker_leaderboard=poker_leaderboard,
            auto_evaluation=auto_eval,
            world_type=self.world_type,
            view_mode=self.view_mode,
        )

    def _collect_entities(self) -> List[EntitySnapshot]:
        return self._entity_snapshot_builder.collect(self.world.entities_list)

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
                valid_scores = [s.confidence_vs_strong for s in history if s.confidence_vs_strong is not None]
                poker_score_history = valid_scores[-20:]

        # Build stat components using helper functions
        base_stats = build_base_stats(stats, frame, self.current_actual_fps, self.fast_forward)
        energy_stats = build_energy_stats(stats, poker_score, poker_score_history)
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
        if not hasattr(self.world.ecosystem, "get_poker_leaderboard"):
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

        Args:
            command: Command type ('add_food', 'spawn_fish', 'pause', 'resume', 'reset')
            data: Optional command data
        """
        # Map commands to handler methods
        handlers = {
            "add_food": self._cmd_add_food,
            "spawn_fish": self._cmd_spawn_fish,
            "pause": self._cmd_pause,
            "resume": self._cmd_resume,
            "reset": self._cmd_reset,
            "fast_forward": self._cmd_fast_forward,
            "start_poker": self._cmd_start_poker,
            "poker_action": self._cmd_poker_action,
            "poker_process_ai_turn": self._cmd_poker_process_ai_turn,
            "poker_new_round": self._cmd_poker_new_round,
            "poker_autopilot_action": self._cmd_poker_autopilot_action,
            "standard_poker_series": self._cmd_standard_poker_series,
        }

        with self.lock:
            handler = handlers.get(command)
            if handler:
                return handler(data or {})
            
            # Log unknown command
            logger.warning(f"Unknown command received: {command}")
            return self._create_error_response(f"Unknown command: {command}")

    async def handle_command_async(
        self, command: str, data: Optional[Dict[str, Any]] = None
    ):
        """Async wrapper to route commands off the event loop thread."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.handle_command, command, data)
