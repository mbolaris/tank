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
from core import entities, movement_strategy
from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.constants import FILES, FRAME_RATE, SCREEN_HEIGHT, SCREEN_WIDTH, SPAWN_MARGIN_PIXELS
from core.entities import Fish
from core.entities.fractal_plant import FractalPlant
from core.genetics import Genome
from core.human_poker_game import HumanPokerGame
from core.plant_poker_strategy import PlantPokerStrategyAdapter

# Use absolute imports assuming tank/ is in PYTHONPATH
from core.tank_world import TankWorld, TankWorldConfig

logger = logging.getLogger(__name__)


class SimulationRunner:
    """Runs the simulation in a background thread and provides state updates."""

    def __init__(
        self,
        seed: Optional[int] = None,
        tank_id: Optional[str] = None,
        tank_name: Optional[str] = None,
    ):
        """Initialize the simulation runner.

        Args:
            seed: Optional random seed for deterministic behavior
            tank_id: Optional unique identifier for the tank
            tank_name: Optional human-readable name for the tank
        """
        # Create TankWorld configuration
        config = TankWorldConfig(headless=True)

        # Create TankWorld instance
        self.world = TankWorld(config=config, seed=seed)
        self.world.setup()

        # Start paused to prevent initial fish from aging before frontend sees them
        # This ensures all fish (initial and spawned) appear at baby size when first created
        self.world.paused = True

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

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
        self.delta_sync_interval = 30
        self._last_full_frame: Optional[int] = None
        self._last_entities: Dict[int, EntitySnapshot] = {}

        # Human poker game management
        self.human_poker_game: Optional[HumanPokerGame] = None

        # Static benchmark poker series management
        self.standard_poker_series: Optional[AutoEvaluatePokerGame] = None

        # Ongoing auto-evaluation against static baseline
        from backend.services.auto_eval_service import AutoEvalService
        self.auto_eval_service = AutoEvalService(self.world, world_lock=self.lock)
        self.auto_eval_running = False
        self._last_auto_eval_stats_version = self.auto_eval_service.get_stats_version()
        self.auto_eval_interval_seconds = 15.0  # Kept for compatibility if needed
        self.last_auto_eval_time = 0.0          # Kept for compatibility if needed
        self.auto_eval_lock = self.auto_eval_service.lock  # Alias lock if needed, or just rely on service

        # Evolution benchmark tracker for longitudinal skill measurement
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
                eval_interval_frames=int(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_FRAMES", "1800")),
                export_path=self._get_evolution_benchmark_export_path(),
                use_quick_benchmark=True,
            )
            self._evolution_benchmark_guard = threading.Lock()
            self._evolution_benchmark_last_completed_time = 0.0
        else:
            self._evolution_benchmark_guard = None
            self._evolution_benchmark_last_completed_time = 0.0

        # Migration support
        self.connection_manager = None  # Set after initialization
        self.tank_registry = None  # Set after initialization
        self._migration_handler = None  # Created when dependencies are available
        self._migration_handler_deps = (None, None)  # (connection_manager, tank_registry)
        self.migration_lock = threading.Lock()

        # Entity snapshot conversion (stable IDs, DTO mapping, z-order sort)
        self._entity_snapshot_builder = EntitySnapshotBuilder()

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

                # Create (or clear) a migration handler based on available dependencies.
                # Core entities depend only on the MigrationHandler protocol, while the backend
                # provides the concrete implementation.
                if self.connection_manager is not None and self.tank_registry is not None:
                    deps = (self.connection_manager, self.tank_registry)
                    if self._migration_handler is None or self._migration_handler_deps != deps:
                        from backend.migration_handler import BackendMigrationHandler

                        self._migration_handler = BackendMigrationHandler(
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

    def _create_plant_player_data(self, plant: FractalPlant) -> Dict[str, Any]:
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
        frame_count = 0
        
        # Drift correction: Track when the next frame *should* start
        next_frame_target = time.time()
        
        try:
            while self.running:
                try:
                    # Advance target time by one frame duration
                    next_frame_target += self.frame_time
                    frame_count += 1

                    with self.lock:
                        try:
                            self.world.update()
                        except Exception as e:
                            logger.error(
                                f"Simulation loop: Error updating world at frame {frame_count}: {e}",
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
                        stats = self.world.get_stats()
                        tank_label = self.tank_name or self.tank_id or "Unknown Tank"
                        logger.info(
                            f"{tank_label} Simulation Status "
                            f"FPS={self.current_actual_fps:.1f}, "
                            f"Fish={stats.get('fish_count', 0)}, "
                            f"Plants={stats.get('plant_count', 0)}, "
                            f"Energy={stats.get('total_energy', 0.0):.1f}"
                        )

                    # Maintain frame rate with drift correction
                    if not self.fast_forward:
                        now = time.time()
                        sleep_time = next_frame_target - now
                        
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                        elif sleep_time < -0.1:  # Lagging by > 100ms
                            # We are falling too far behind, reset target to avoid "spiral of death"
                            # where we try to execute 0-delay frames forever to catch up
                            next_frame_target = now
                    else:
                        # Even in fast-forward mode, yield occasionally so signals/shutdown remain responsive.
                        time.sleep(0)

                except Exception as e:
                    logger.error(f"Simulation loop: Unexpected error at frame {frame_count}: {e}", exc_info=True)
                    # Use simple sleep on error to prevent tight loops
                    time.sleep(self.frame_time)
                    # Reset timing target after error recovery
                    next_frame_target = time.time()

        except Exception as e:
            logger.error(f"Simulation loop: Fatal error, loop exiting: {e}", exc_info=True)
        finally:
            logger.info(f"Simulation loop: Ended after {frame_count} frames")

    def _start_auto_evaluation_if_needed(self) -> None:
        """Periodically benchmark top fish against the static evaluator."""
        if hasattr(self, "auto_eval_service"):
            self.auto_eval_service.update()
            current_version = self.auto_eval_service.get_stats_version()
            if current_version != self._last_auto_eval_stats_version:
                self._last_auto_eval_stats_version = current_version
                self._invalidate_state_cache()
            if self.auto_eval_service.running != self.auto_eval_running:
                # Sync running state if needed, or just rely on invalidating cache when done
                if not self.auto_eval_service.running and self.auto_eval_running:
                    self._invalidate_state_cache()
                self.auto_eval_running = self.auto_eval_service.running

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

        interval_seconds = float(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_SECONDS", "60"))
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
                    tracker.run_and_record(
                        fish_population=fish_list,
                        current_frame=current_frame,
                        force=True,
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


    def _reward_auto_eval_winners(self, benchmark_players: List[Dict[str, Any]], final_stats) -> None:
        """Reward Fish/Plants that won energy in auto-evaluation by adding it to their actual energy.

        Args:
            benchmark_players: List of players that participated in the evaluation
            final_stats: Final statistics from the auto-evaluation game
        """
        with self.lock:
            for player_stats in final_stats.players:
                # Skip the standard algorithm player
                if player_stats.get("is_standard", False):
                    continue

                net_energy = player_stats.get("net_energy", 0.0)
                if net_energy <= 0:
                    continue  # Only reward winners

                # Find the actual entity
                fish_id = player_stats.get("fish_id")
                plant_id = player_stats.get("plant_id")

                if fish_id is not None:
                    fish = next((e for e in self.world.entities_list
                               if isinstance(e, Fish) and e.fish_id == fish_id), None)
                    if fish and net_energy > 0:
                        # Use modify_energy to properly cap at max and route overflow to reproduction/food
                        actual_gain = fish.modify_energy(net_energy)
                        if actual_gain > 0 and fish.ecosystem is not None:
                            fish.ecosystem.record_auto_eval_energy_gain(actual_gain)
                        logger.info(f"Auto-eval reward: Fish #{fish_id} gained {actual_gain:.1f} energy")

                elif plant_id is not None:
                    plant = next((e for e in self.world.entities_list
                                if isinstance(e, FractalPlant) and e.plant_id == plant_id), None)
                    if plant:
                        reward = min(net_energy, plant.max_energy - plant.energy)
                        if reward > 0:
                            actual_gain = plant.gain_energy(reward, source="auto_eval")
                            logger.info(
                                f"Auto-eval reward: Plant #{plant_id} gained {actual_gain:.1f} energy"
                            )

    def get_state(self, force_full: bool = False, allow_delta: bool = True):
        """Get current simulation state for WebSocket broadcast.

        This method now supports delta compression to avoid sending the entire
        world on every frame. A full state is sent every ``delta_sync_interval``
        frames (or when ``force_full`` is True); intermediate frames only carry
        position/velocity updates plus any added/removed entities.
        """

        current_frame = self.world.frame_count
        elapsed_time = (
            self.world.engine.elapsed_time
            if hasattr(self.world.engine, "elapsed_time")
            else self.world.frame_count * 33
        )

        # Fast path: identical frame reuse
        if self._cached_state is not None and current_frame == self._cached_state_frame:
            return self._cached_state

        self.frames_since_websocket_update += 1
        should_rebuild = self.frames_since_websocket_update >= self.websocket_update_interval

        if not should_rebuild and self._cached_state is not None:
            return self._cached_state

        self.frames_since_websocket_update = 0

        # Try to acquire lock with timeout to prevent blocking indefinitely.
        # If we don't have any cached state yet (fresh server start / first client),
        # wait longer so the frontend can render an initial snapshot even if the
        # simulation update is slow.
        lock_timeout = 5.0 if self._cached_state is None else 0.5
        lock_acquired = self.lock.acquire(timeout=lock_timeout)
        if not lock_acquired:
            # If we can't get the lock, return cached state to avoid blocking
            logger.debug("get_state: Lock acquisition timed out, returning cached state")
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
            send_full = (
                force_full
                or not allow_delta
                or self._last_full_frame is None
                or (current_frame - self._last_full_frame) >= self.delta_sync_interval
            )

            if send_full:
                state = self._build_full_state(current_frame, elapsed_time)
                self._last_full_frame = current_frame
                self._last_entities = {entity.id: entity for entity in state.entities}
            else:
                entities = self._collect_entities()
                current_entities = {entity.id: entity for entity in entities}

                added = [entity.to_full_dict() for eid, entity in current_entities.items() if eid not in self._last_entities]
                removed = [eid for eid in self._last_entities if eid not in current_entities]
                updates = [entity.to_delta_dict() for entity in entities]

                poker_events = self._collect_poker_events()
                state = DeltaStatePayload(
                    frame=current_frame,
                    elapsed_time=elapsed_time,
                    updates=updates,
                    added=added,
                    removed=removed,
                    poker_events=poker_events,
                    stats=None,
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

        if duration_ms > 10:
            logger.warning(
                "serialize_state: Slow serialization %.2f ms for frame %s",
                duration_ms,
                getattr(state, "frame", "unknown"),
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
        )

    def _collect_entities(self) -> List[EntitySnapshot]:
        return self._entity_snapshot_builder.collect(self.world.entities_list)

    def _collect_poker_stats_payload(self, stats: Dict[str, Any]) -> PokerStatsPayload:
        """Create PokerStatsPayload from stats dictionary."""
        poker_stats_dict = stats.get("poker_stats", {})
        return PokerStatsPayload(
            total_games=poker_stats_dict.get("total_games", 0),
            total_fish_games=poker_stats_dict.get("total_fish_games", 0),
            total_plant_games=poker_stats_dict.get("total_plant_games", 0),
            total_plant_energy_transferred=poker_stats_dict.get("total_plant_energy_transferred", 0.0),
            total_wins=poker_stats_dict.get("total_wins", 0),
            total_losses=poker_stats_dict.get("total_losses", 0),
            total_ties=poker_stats_dict.get("total_ties", 0),
            total_energy_won=poker_stats_dict.get("total_energy_won", 0.0),
            total_energy_lost=poker_stats_dict.get("total_energy_lost", 0.0),
            net_energy=poker_stats_dict.get("net_energy", 0.0),
            best_hand_rank=poker_stats_dict.get("best_hand_rank", 0),
            best_hand_name=poker_stats_dict.get("best_hand_name", "None"),
            win_rate=poker_stats_dict.get("win_rate", 0.0),
            win_rate_pct=poker_stats_dict.get("win_rate_pct", "0.0%"),
            roi=poker_stats_dict.get("roi", 0.0),
            vpip=poker_stats_dict.get("vpip", 0.0),
            vpip_pct=poker_stats_dict.get("vpip_pct", "0.0%"),
            bluff_success_rate=poker_stats_dict.get("bluff_success_rate", 0.0),
            bluff_success_pct=poker_stats_dict.get("bluff_success_pct", "0.0%"),
            button_win_rate=poker_stats_dict.get("button_win_rate", 0.0),
            button_win_rate_pct=poker_stats_dict.get("button_win_rate_pct", "0.0%"),
            off_button_win_rate=poker_stats_dict.get("off_button_win_rate", 0.0),
            off_button_win_rate_pct=poker_stats_dict.get("off_button_win_rate_pct", "0.0%"),
            positional_advantage=poker_stats_dict.get("positional_advantage", 0.0),
            positional_advantage_pct=poker_stats_dict.get("positional_advantage_pct", "0.0%"),
            aggression_factor=poker_stats_dict.get("aggression_factor", 0.0),
            avg_hand_rank=poker_stats_dict.get("avg_hand_rank", 0.0),
            total_folds=poker_stats_dict.get("total_folds", 0),
            preflop_folds=poker_stats_dict.get("preflop_folds", 0),
            postflop_folds=poker_stats_dict.get("postflop_folds", 0),
            showdown_win_rate=poker_stats_dict.get("showdown_win_rate", "0.0%"),
            avg_fold_rate=poker_stats_dict.get("avg_fold_rate", "0.0%"),
        )

    def _collect_stats(self, frame: int) -> StatsPayload:
        """Collect and organize simulation statistics."""
        stats = self.world.get_stats()
        
        # Organize stats into logical groups
        poker_stats = self._collect_poker_stats_payload(stats)
        
        # Extract individual stat groups to reduce cognitive load in the main constructor call
        # while preserving the flat structure required by the existing StatsPayload definition
        
        # Base simulation metrics
        base_stats = {
            "frame": frame,
            "population": stats.get("total_population", 0),
            "generation": stats.get("current_generation", 0),
            "max_generation": stats.get("max_generation", stats.get("current_generation", 0)),
            "births": stats.get("total_births", 0),
            "deaths": stats.get("total_deaths", 0),
            "capacity": stats.get("capacity_usage", "0%"),
            "time": stats.get("time_string", "Day"),
            "death_causes": stats.get("death_causes", {}),
            "fish_count": stats.get("fish_count", 0),
            "food_count": stats.get("food_count", 0),
            "plant_count": stats.get("plant_count", 0),
            "fps": round(self.current_actual_fps, 1),
            "fast_forward": self.fast_forward,
            "total_sexual_births": stats.get("reproduction_stats", {}).get("total_sexual_reproductions", 0),
            "total_asexual_births": stats.get("reproduction_stats", {}).get("total_asexual_reproductions", 0),
        }
        
        # Energy metrics
        energy_stats = {
            "total_energy": stats.get("total_energy", 0.0),
            "food_energy": stats.get("food_energy", 0.0),
            "live_food_count": stats.get("live_food_count", 0),
            "live_food_energy": stats.get("live_food_energy", 0.0),
            "fish_energy": stats.get("fish_energy", 0.0),
            "plant_energy": stats.get("plant_energy", 0.0),
            "energy_sources": stats.get("energy_sources", {}),
            "energy_sources_recent": stats.get("energy_sources_recent", {}),
            "energy_from_nectar": stats.get("energy_from_nectar", 0.0),
            "energy_from_live_food": stats.get("energy_from_live_food", 0.0),
            "energy_from_falling_food": stats.get("energy_from_falling_food", 0.0),
            "energy_from_poker": stats.get("energy_from_poker", 0.0),
            "energy_from_poker_plant": stats.get("energy_from_poker_plant", 0.0),
            "energy_from_auto_eval": stats.get("energy_from_auto_eval", 0.0),
            "energy_burn_recent": stats.get("energy_burn_recent", {}),
            "energy_burn_total": stats.get("energy_burn_total", 0.0),
            "energy_gains_recent_total": stats.get("energy_gains_recent_total", 0.0),
            "energy_net_recent": stats.get("energy_net_recent", 0.0),
            "energy_accounting_discrepancy": stats.get("energy_accounting_discrepancy", 0.0),
            "plant_energy_sources": stats.get("plant_energy_sources", {}),
            "plant_energy_sources_recent": stats.get("plant_energy_sources_recent", {}),
            "plant_energy_from_photosynthesis": stats.get("plant_energy_from_photosynthesis", 0.0),
            "plant_energy_burn_recent": stats.get("plant_energy_burn_recent", {}),
            "plant_energy_burn_total": stats.get("plant_energy_burn_total", 0.0),
            "energy_delta": stats.get("energy_delta", {}),
            "avg_fish_energy": stats.get("avg_fish_energy", 0.0),
            "min_fish_energy": stats.get("min_fish_energy", 0.0),
            "max_fish_energy": stats.get("max_fish_energy", 0.0),
            "min_max_energy_capacity": stats.get("min_max_energy_capacity", 0.0),
            "max_max_energy_capacity": stats.get("max_max_energy_capacity", 0.0),
            "median_max_energy_capacity": stats.get("median_max_energy_capacity", 0.0),
            "fish_health_critical": stats.get("fish_health_critical", 0),
            "fish_health_low": stats.get("fish_health_low", 0),
            "fish_health_healthy": stats.get("fish_health_healthy", 0),
            "fish_health_full": stats.get("fish_health_full", 0),
        }
        
        # Physical stats
        physical_stats = {
            # Adult size
            "adult_size_min": stats.get("adult_size_min", 0.0),
            "adult_size_max": stats.get("adult_size_max", 0.0),
            "adult_size_median": stats.get("adult_size_median", 0.0),
            "adult_size_range": stats.get("adult_size_range", ""),
            "allowed_adult_size_min": stats.get("allowed_adult_size_min", 0.0),
            "allowed_adult_size_max": stats.get("allowed_adult_size_max", 0.0),
            "adult_size_bins": stats.get("adult_size_bins", []),
            "adult_size_bin_edges": stats.get("adult_size_bin_edges", []),
            
            # Eye size
            "eye_size_min": stats.get("eye_size_min", 0.0),
            "eye_size_max": stats.get("eye_size_max", 0.0),
            "eye_size_median": stats.get("eye_size_median", 0.0),
            "eye_size_bins": stats.get("eye_size_bins", []),
            "eye_size_bin_edges": stats.get("eye_size_bin_edges", []),
            "allowed_eye_size_min": stats.get("allowed_eye_size_min", 0.5),
            "allowed_eye_size_max": stats.get("allowed_eye_size_max", 2.0),
            
            # Fin size
            "fin_size_min": stats.get("fin_size_min", 0.0),
            "fin_size_max": stats.get("fin_size_max", 0.0),
            "fin_size_median": stats.get("fin_size_median", 0.0),
            "fin_size_bins": stats.get("fin_size_bins", []),
            "fin_size_bin_edges": stats.get("fin_size_bin_edges", []),
            "allowed_fin_size_min": stats.get("allowed_fin_size_min", 0.5),
            "allowed_fin_size_max": stats.get("allowed_fin_size_max", 2.0),
            
            # Tail size
            "tail_size_min": stats.get("tail_size_min", 0.0),
            "tail_size_max": stats.get("tail_size_max", 0.0),
            "tail_size_median": stats.get("tail_size_median", 0.0),
            "tail_size_bins": stats.get("tail_size_bins", []),
            "tail_size_bin_edges": stats.get("tail_size_bin_edges", []),
            "allowed_tail_size_min": stats.get("allowed_tail_size_min", 0.5),
            "allowed_tail_size_max": stats.get("allowed_tail_size_max", 2.0),
            
            # Body aspect
            "body_aspect_min": stats.get("body_aspect_min", 0.0),
            "body_aspect_max": stats.get("body_aspect_max", 0.0),
            "body_aspect_median": stats.get("body_aspect_median", 0.0),
            "allowed_body_aspect_min": stats.get("allowed_body_aspect_min", 0.0),
            "allowed_body_aspect_max": stats.get("allowed_body_aspect_max", 0.0),
            "body_aspect_bins": stats.get("body_aspect_bins", []),
            "body_aspect_bin_edges": stats.get("body_aspect_bin_edges", []),
            
            # Template ID
            "template_id_min": stats.get("template_id_min", 0.0),
            "template_id_max": stats.get("template_id_max", 0.0),
            "template_id_median": stats.get("template_id_median", 0.0),
            "allowed_template_id_min": stats.get("allowed_template_id_min", 0.0),
            "allowed_template_id_max": stats.get("allowed_template_id_max", 0.0),
            "template_id_bins": stats.get("template_id_bins", []),
            "template_id_bin_edges": stats.get("template_id_bin_edges", []),
            
            # Pattern type
            "pattern_type_min": stats.get("pattern_type_min", 0.0),
            "pattern_type_max": stats.get("pattern_type_max", 0.0),
            "pattern_type_median": stats.get("pattern_type_median", 0.0),
            "allowed_pattern_type_min": stats.get("allowed_pattern_type_min", 0.0),
            "allowed_pattern_type_max": stats.get("allowed_pattern_type_max", 0.0),
            "pattern_type_bins": stats.get("pattern_type_bins", []),
            "pattern_type_bin_edges": stats.get("pattern_type_bin_edges", []),
            
            # Pattern intensity
            "pattern_intensity_min": stats.get("pattern_intensity_min", 0.0),
            "pattern_intensity_max": stats.get("pattern_intensity_max", 0.0),
            "pattern_intensity_median": stats.get("pattern_intensity_median", 0.0),
            "allowed_pattern_intensity_min": stats.get("allowed_pattern_intensity_min", 0.0),
            "allowed_pattern_intensity_max": stats.get("allowed_pattern_intensity_max", 0.0),
            "pattern_intensity_bins": stats.get("pattern_intensity_bins", []),
            "pattern_intensity_bin_edges": stats.get("pattern_intensity_bin_edges", []),
            
            # Lifespan modifier
            "lifespan_modifier_min": stats.get("lifespan_modifier_min", 0.0),
            "lifespan_modifier_max": stats.get("lifespan_modifier_max", 0.0),
            "lifespan_modifier_median": stats.get("lifespan_modifier_median", 0.0),
            "allowed_lifespan_modifier_min": stats.get("allowed_lifespan_modifier_min", 0.0),
            "allowed_lifespan_modifier_max": stats.get("allowed_lifespan_modifier_max", 0.0),
            "lifespan_modifier_bins": stats.get("lifespan_modifier_bins", []),
            "lifespan_modifier_bin_edges": stats.get("lifespan_modifier_bin_edges", []),
        }

        # Combine into payload
        return StatsPayload(
            # Base Stats
            **base_stats,
            # Energy Stats
            **energy_stats,
            # Physical Stats
            **physical_stats,
            # Poker Stats object
            poker_stats=poker_stats,
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
        if hasattr(self, "auto_eval_service"):
             return self.auto_eval_service.get_history()
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
        if not hasattr(self, "auto_eval_service"):
            return None

        stats = self.auto_eval_service.get_stats()
        if not stats:
            return None

        return AutoEvaluateStatsPayload(
            hands_played=stats["hands_played"],
            hands_remaining=stats["hands_remaining"],
            game_over=stats["game_over"],
            winner=stats["winner"],
            reason=stats["reason"],
            players=stats["players"],
            performance_history=stats["performance_history"],
        )

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
        with self.lock:
            if command == "add_food":
                # Add food at random position
                x = self.world.rng.randint(0, SCREEN_WIDTH)
                food = entities.Food(
                    self.world.environment,
                    x,
                    0,
                    source_plant=None,
                    allow_stationary_types=False,
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT,
                )
                food.pos.y = 0
                self.world.add_entity(food)
                self._invalidate_state_cache()

            elif command == "spawn_fish":
                # Spawn a new fish at random position
                try:
                    logger.info("Spawn fish command received")

                    # Random spawn position (avoid edges)
                    x = self.world.rng.randint(
                        SPAWN_MARGIN_PIXELS, SCREEN_WIDTH - SPAWN_MARGIN_PIXELS
                    )
                    y = self.world.rng.randint(
                        SPAWN_MARGIN_PIXELS, SCREEN_HEIGHT - SPAWN_MARGIN_PIXELS
                    )

                    logger.info(f"Creating fish at position ({x}, {y})")

                    # Create new fish with random genome
                    genome = Genome.random(use_algorithm=True)
                    new_fish = entities.Fish(
                        self.world.environment,
                        movement_strategy.AlgorithmicMovement(),
                        FILES["schooling_fish"][0],
                        x,
                        y,
                        4,  # Base speed
                        genome=genome,
                        generation=0,
                        ecosystem=self.world.ecosystem,
                        screen_width=SCREEN_WIDTH,
                        screen_height=SCREEN_HEIGHT,
                    )
                    self.world.add_entity(new_fish)
                    self._invalidate_state_cache()

                except Exception as e:
                    logger.error(f"Error spawning fish: {e}")

            elif command == "pause":
                self.world.paused = True
                logger.info("Simulation paused")

            elif command == "resume":
                self.world.paused = False
                logger.info("Simulation resumed")

            elif command == "reset":
                # Reset the underlying world to a clean frame counter and entities
                if hasattr(self.world, "reset"):
                    self.world.reset()
                else:
                    self.world.setup()
                self._invalidate_state_cache()
                # Unpause after reset for intuitive behavior
                self.world.paused = False
                self.fast_forward = False
                logger.info("Simulation reset")

            elif command == "fast_forward":
                enabled = data.get("enabled", False) if data else False
                self.fast_forward = enabled
                logger.info(f"Fast forward {'enabled' if enabled else 'disabled'}")

            elif command == "start_poker":
                # Start a new poker game with top 3 fish
                logger.info("Starting human poker game...")
                try:
                    # Get top 3 fish from leaderboard
                    fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]

                    if len(fish_list) < 3:
                        logger.warning(f"Not enough fish to start poker game (need 3, have {len(fish_list)})")
                        return self._create_error_response(
                            f"Need at least 3 fish to play poker (currently {len(fish_list)})"
                        )

                    # Get leaderboard
                    leaderboard = self.world.ecosystem.get_poker_leaderboard(
                        fish_list=fish_list, limit=3, sort_by="net_energy"
                    )

                    # Create AI fish data from top 3
                    ai_fish = []
                    for entry in leaderboard[:3]:
                        # Find the actual fish object
                        fish = next((f for f in fish_list if f.fish_id == entry["fish_id"]), None)
                        if fish:
                            ai_fish.append(self._create_fish_player_data(fish, include_aggression=True))

                    # If we don't have 3 fish from leaderboard, fill with random fish
                    if len(ai_fish) < 3:
                        for fish in fish_list:
                            if len(ai_fish) >= 3:
                                break
                            if fish.fish_id not in [f["fish_id"] for f in ai_fish]:
                                ai_fish.append(self._create_fish_player_data(fish, include_aggression=True))

                    # Create poker game
                    game_id = str(uuid.uuid4())
                    human_energy = data.get("energy", 500.0) if data else 500.0

                    self.human_poker_game = HumanPokerGame(
                        game_id=game_id,
                        human_energy=human_energy,
                        ai_fish=ai_fish,
                        small_blind=5.0,
                        big_blind=10.0,
                    )

                    logger.info(f"Created human poker game {game_id} with {len(ai_fish)} AI opponents")

                    # Return the initial game state to the frontend
                    return {
                        "success": True,
                        "state": self.human_poker_game.get_state(),
                    }

                except Exception as e:
                    logger.error(f"Error starting poker game: {e}", exc_info=True)
                    return self._create_error_response(f"Failed to start poker game: {str(e)}")

            elif command == "poker_action":
                # Handle poker action (fold, check, call, raise)
                if not self.human_poker_game:
                    logger.warning("Poker action received but no game active")
                    return self._create_error_response("No poker game active")

                if not data:
                    return self._create_error_response("No action data provided")

                action = data.get("action")
                amount = data.get("amount", 0.0)

                logger.info(f"Processing poker action: {action}, amount: {amount}")

                result = self.human_poker_game.handle_action("human", action, amount)
                return result

            elif command == "poker_process_ai_turn":
                # Process a single AI player's turn (for step-by-step animation)
                if not self.human_poker_game:
                    logger.warning("AI turn processing requested but no game active")
                    return self._create_error_response("No poker game active")

                result = self.human_poker_game.process_single_ai_turn()
                return result

            elif command == "poker_new_round":
                # Start a new hand in the current poker session
                if not self.human_poker_game:
                    logger.warning("New round requested but no game active")
                    return self._create_error_response("No poker game active")

                logger.info("Starting new poker hand...")
                result = self.human_poker_game.start_new_hand()
                return result

            elif command == "poker_autopilot_action":
                # Get AI-recommended action for human player (autopilot mode)
                if not self.human_poker_game:
                    logger.warning("Autopilot action requested but no game active")
                    return self._create_error_response("No poker game active")

                game = self.human_poker_game

                # If game is over, return new_round action
                if game.game_over:
                    if game.session_over:
                        return {"success": True, "action": "exit", "amount": 0}
                    return {"success": True, "action": "new_round", "amount": 0}

                # If not human's turn, wait
                human_player = game.players[0]  # Human is always index 0
                if game.current_player_index != 0:
                    return {"success": True, "action": "wait", "amount": 0}

                # Use the same AI logic as fish opponents
                from core.poker.core import decide_action, evaluate_hand

                hand = evaluate_hand(human_player.hole_cards, game.community_cards)
                call_amount = game._get_call_amount(0)
                active_bets = [p.current_bet for p in game.players if not p.folded]
                opponent_bet = max(active_bets) if active_bets else 0.0

                action, bet_amount = decide_action(
                    hand=hand,
                    current_bet=human_player.current_bet,
                    opponent_bet=opponent_bet,
                    pot=game.pot,
                    player_energy=human_player.energy,
                    aggression=0.5,  # Medium aggression for autopilot
                    hole_cards=human_player.hole_cards,
                    community_cards=game.community_cards,
                    position_on_button=(game.current_player_index == game.button_index),
                )

                # Convert BettingAction enum to string
                action_str = action.name.lower()

                # Handle check vs call
                if action_str == "check" and call_amount > 0:
                    action_str = "call"
                    bet_amount = call_amount
                elif action_str == "call":
                    bet_amount = call_amount
                elif action_str == "raise":
                    # bet_amount is the raise amount on top of call
                    pass

                logger.info(f"Autopilot recommends: {action_str}, amount: {bet_amount}")
                return {"success": True, "action": action_str, "amount": bet_amount}

            elif command == "standard_poker_series":
                # Run standard benchmark poker series with top 3 fish vs static player
                logger.info("Starting standard poker benchmark series...")
                try:
                    # Get top fish from leaderboard
                    fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]

                    if len(fish_list) < 1:
                        logger.warning("No fish available for benchmark series")
                        return self._create_error_response("Need at least 1 fish to run benchmark series")

                    # Get top 3 fish from leaderboard
                    num_fish = min(3, len(fish_list))
                    leaderboard = self.world.ecosystem.get_poker_leaderboard(
                        fish_list=fish_list, limit=num_fish, sort_by="net_energy"
                    )

                    # Build list of fish player data
                    fish_players = []
                    for i in range(num_fish):
                        if i < len(leaderboard):
                            # Use leaderboard entry
                            entry = leaderboard[i]
                            fish = next(
                                (f for f in fish_list if f.fish_id == entry["fish_id"]),
                                fish_list[i]
                            )
                            fish_name = f"{entry['algorithm'][:15]} (Gen {entry['generation']}) #{entry['fish_id']}"
                        else:
                            # Fallback to fish from list
                            fish = fish_list[i]
                            algo_name = "Unknown"
                            if fish.genome.behavior_algorithm:
                                algo_name = fish.genome.behavior_algorithm.algorithm_id
                            fish_name = f"{algo_name[:15]} (Gen {fish.generation}) #{fish.fish_id}"

                        fish_players.append({
                            "name": fish_name,
                            "fish_id": fish.fish_id,
                            "generation": fish.generation,
                            "poker_strategy": fish.genome.poker_strategy_algorithm,
                        })

                    # Create benchmark series with multiple fish
                    game_id = str(uuid.uuid4())
                    standard_energy = data.get("standard_energy", 500.0) if data else 500.0
                    max_hands = data.get("max_hands", 1000) if data else 1000

                    self.standard_poker_series = AutoEvaluatePokerGame(
                        game_id=game_id,
                        player_pool=fish_players,
                        standard_energy=standard_energy,
                        max_hands=max_hands,
                        small_blind=5.0,
                        big_blind=10.0,
                    )

                    logger.info(
                        f"Created standard series {game_id} with {len(fish_players)} fish vs Standard"
                    )

                    # Run the series (this will complete all hands)
                    final_stats = self.standard_poker_series.run_evaluation()

                    # Convert stats to dict for JSON serialization
                    stats_dict = {
                        "hands_played": final_stats.hands_played,
                        "hands_remaining": final_stats.hands_remaining,
                        "game_over": final_stats.game_over,
                        "winner": final_stats.winner,
                        "reason": final_stats.reason,
                        "players": final_stats.players,  # List of all player stats
                        "performance_history": final_stats.performance_history,
                    }

                    logger.info(
                        f"Standard series complete: {final_stats.winner} after {final_stats.hands_played} hands!"
                    )

                    # Return the final stats to the frontend
                    return {
                        "success": True,
                        "stats": stats_dict,
                    }

                except Exception as e:
                    logger.error(f"Error running benchmark series: {e}", exc_info=True)
                    return self._create_error_response(f"Failed to run benchmark series: {str(e)}")

    async def handle_command_async(
        self, command: str, data: Optional[Dict[str, Any]] = None
    ):
        """Async wrapper to route commands off the event loop thread."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.handle_command, command, data)
