"""Background simulation runner thread."""

import asyncio
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from backend.world_manager import WorldManager
    from core.entities import Fish

from backend.runner import (
    CommandHandlerMixin,
    evolution_benchmark,
    loop,
    stats_collector,
    world_switch,
)
from backend.runner.perf_tracker import PerfTracker
from backend.runner.state_builders import collect_poker_stats_payload
from backend.runner.state_publisher import StatePublisher
from backend.runner.world_hooks import get_hooks_for_world
from backend.metrics_history import MetricsHistory
from backend.state_payloads import EntitySnapshot, PokerStatsPayload, StatsPayload
from backend.world_registry import create_world, get_world_metadata
from core import entities
from core.config.display import FRAME_RATE
from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend

logger = logging.getLogger(__name__)


class SimulationRunner(CommandHandlerMixin):
    """Runs the simulation in a background thread and provides state updates.

    Inherits command handling from CommandHandlerMixin to reduce class size.
    """

    def __init__(
        self,
        seed: int | None = None,
        world_id: str | None = None,
        world_name: str | None = None,
        world_type: str = "tank",
        world_manager: Optional["WorldManager"] = None,
        config: dict[str, Any] | None = None,
    ):
        """Initialize the simulation runner.
        world_type: Type of world to create (default "tank")
        """
        super().__init__()
        self.world_manager = world_manager
        self._seed = seed  # Store for later use (e.g., switch_world_type)
        self._config = dict(config) if config else None
        # Create world via registry (world-agnostic)
        self.world: MultiAgentWorldBackend
        self.world, self._entity_snapshot_builder = create_world(
            world_type, seed=seed, config=self._config
        )
        self.world.runner = self

        # Store world metadata for payloads
        metadata = get_world_metadata(world_type)
        self.mode_id = metadata.mode_id if metadata else world_type
        self.world_type = metadata.world_type if metadata else world_type
        self.view_mode = metadata.view_mode if metadata else "side"

        # Create world-specific hooks for feature extensions
        self.world_hooks = get_hooks_for_world(world_type)

        # Worlds start unpaused by default - they run as soon as the server starts
        self.world.set_paused(False)

        self.running = False
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()

        # Performance instrumentation
        self._enable_perf_logging = True
        self.perf_tracker = PerfTracker(enable_logging=self._enable_perf_logging)

        # World identity (used for persistence, migration context, and UI attribution)
        self.world_id = world_id or str(uuid.uuid4())
        self.world_name = world_name or f"World {self.world_id[:8]}"

        # Target frame rate
        self.fps = FRAME_RATE
        self.frame_time = 1.0 / self.fps
        self.fast_forward = False

        # FPS Tracking
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        self.current_actual_fps = 0.0

        self._cached_gene_distributions: dict[str, Any] = {}
        self._last_distribution_time = 0.0
        raw_distribution_interval = os.getenv("BROADCAST_DISTRIBUTIONS_INTERVAL_SECONDS", "10")
        try:
            self._distribution_interval_seconds = float(raw_distribution_interval)
        except ValueError:
            self._distribution_interval_seconds = 10.0
        if self._distribution_interval_seconds < 0:
            self._distribution_interval_seconds = 0.0

        # State publishing
        self.state_publisher = StatePublisher(
            perf_tracker=self.perf_tracker, websocket_update_interval=2, delta_sync_interval=90
        )

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

        # Initialize metrics history tracking
        self.metrics_history = MetricsHistory(world_id=self.world_id)

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

    @property
    def evolution_benchmark_tracker(self):
        """Delegate to world hooks for the evolution benchmark tracker."""
        return getattr(self.world_hooks, "evolution_benchmark_tracker", None)

    @property
    def _evolution_benchmark_guard(self):
        """Delegate to world hooks for the benchmark threading guard."""
        return getattr(self.world_hooks, "_evolution_benchmark_guard", None)

    @property
    def _evolution_benchmark_last_completed_time(self):
        """Delegate to world hooks for the last benchmark completion time."""
        return getattr(self.world_hooks, "_evolution_benchmark_last_completed_time", 0.0)

    @_evolution_benchmark_last_completed_time.setter
    def _evolution_benchmark_last_completed_time(self, value):
        """Set the last benchmark completion time on world hooks."""
        if hasattr(self.world_hooks, "_evolution_benchmark_last_completed_time"):
            self.world_hooks._evolution_benchmark_last_completed_time = value

    def _get_evolution_benchmark_export_path(self) -> Path:
        """Get the benchmark export path scoped to this world."""
        world_id = getattr(self, "world_id", None) or "default"
        # Write to shared benchmarks directory to avoid creating orphan world directories
        return Path("data") / "benchmarks" / f"poker_evolution_{world_id[:8]}.json"

    def set_world_identity(self, world_id: str, world_name: str | None = None) -> None:
        """Update world identity for restored/renamed worlds.

        This keeps runner-level persistence paths and migration context consistent
        with the SimulationManager's world metadata.
        """
        self.world_id = world_id
        if world_name is not None:
            self.world_name = world_name

        # Update metrics history world_id
        if hasattr(self, "metrics_history") and self.metrics_history is not None:
            self.metrics_history.world_id = world_id

        # Update hooks with new world identity
        if hasattr(self.world_hooks, "update_benchmark_tracker_path"):
            self.world_hooks.update_benchmark_tracker_path(self)

        self._update_environment_migration_context()

    def switch_world_type(self, new_world_type: str) -> None:
        """Switch to a different world type while preserving entities.

        This hot-swaps between tank and petri modes without resetting the
        simulation. Delegates to ``backend.runner.world_switch`` (extracted
        verbatim); the swap happens entirely under ``self.lock``.

        Args:
            new_world_type: Target world type ("tank" or "petri")

        Raises:
            ValueError: If switching between incompatible world types
        """
        world_switch.switch_world_type(self, new_world_type)

    # Removed: _apply_petri_physics, _remove_petri_physics, _relocate_plants_to_spots, _clamp_entities_to_dish
    # These are now handled by WorldHooks (PetriWorldHooks).

    def _update_environment_migration_context(self) -> None:
        """Update the environment with current migration context."""
        world_switch.update_environment_migration_context(self)

    def _create_error_response(self, error_msg: str) -> dict[str, Any]:
        """Create a standardized error response.

        Args:
            error_msg: The error message to return

        Returns:
            Dictionary with success=False and error message
        """
        return {"success": False, "error": error_msg}

    def _invalidate_state_cache(self) -> None:
        """Clear cached state (wrapper for legacy command handlers)."""
        self.state_publisher.invalidate_cache()

    # Removed: _invalidate_state_cache (delegate directly to publisher or use wrapper)

    def invalidate_state_cache(self) -> None:
        """Public wrapper to invalidate cached websocket state.

        Other backend modules (migrations/transfers) should call this instead of
        reaching into private cache implementation details.
        """

        self.state_publisher.invalidate_cache()

    @property
    def engine(self):
        """Expose the underlying simulation engine for testing."""
        return self.world.engine

    @property
    def frame_count(self) -> int:
        """Current frame count from the simulation."""
        # MultiAgentWorldBackend doesn't have frame_count directly, but adapters often do.
        # Fall back to 0 if not present.
        return int(getattr(self.world, "frame_count", 0))

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused."""
        return self.world.is_paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set the simulation paused state."""
        self.world.set_paused(value)
        # Also set the attribute directly so tests and external code
        # that access the attribute directly see the correct value.
        if hasattr(self.world, "paused"):
            self.world.paused = value

    def get_entities_snapshot(self) -> list[EntitySnapshot]:
        """Get entity snapshots for rendering (public API for RunnerProtocol).

        Returns:
            List of EntitySnapshot DTOs for all entities
        """
        return self._collect_entities()

    def get_stats(self) -> dict[str, Any]:
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

    def get_world_info(self) -> dict[str, str]:
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
        self, fish: "Fish", include_aggression: bool = False
    ) -> dict[str, Any]:
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
            self.world.set_paused(start_paused)

            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop the simulation."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def step(self, actions_by_agent: dict[str, Any] | None = None) -> None:
        """Advance the simulation by one step.

        Note: This explicitly steps even if the world is paused,
        allowing API-driven stepping for testing and manual control.
        """
        with self.lock:
            # Temporarily unpause to allow stepping (API step should always work)
            was_paused = self.world.is_paused
            if was_paused:
                self.world.set_paused(False)

            try:
                if getattr(self.world, "supports_fast_step", False):
                    self.world.step({FAST_STEP_ACTION: True})
                else:
                    self.world.step()
            finally:
                # Restore paused state
                if was_paused:
                    self.world.set_paused(True)

            self._start_auto_evaluation_if_needed()
            self._sample_metrics_if_due()
            self.fps_frame_count += 1
            self.state_publisher.invalidate_cache()

    def reset(
        self,
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> Any:
        """Reset the world to initial state."""
        with self.lock:
            if seed is not None:
                self.seed = seed
            if config is not None:
                self._config = dict(config)

            # create_world expects tank_type/world_type as first arg, but we call function create_world
            # self.create_world() in code refers to backend.world_registry.create_world?
            # No, self.world, self._entity_snapshot_builder = create_world(self.world_type, seed=seed)
            # We import create_world at top level

            self.world, self._entity_snapshot_builder = create_world(
                self.world_type, seed=self.seed, config=self._config
            )
            self.world.runner = self
            self.metrics_history = MetricsHistory(world_id=self.world_id)
            # Use getattr/setattr or direct access if known to be an adapter
            if hasattr(self.world, "frame_count"):
                self.world.frame_count = 0
            self.state_publisher.invalidate_cache()

    def _run_loop(self):
        """Main simulation loop (thread target).

        Delegates to ``backend.runner.loop`` (extracted verbatim). The pause
        gate (a paused world must not advance) and the lock discipline (all
        stepping happens under ``self.lock``) live there unchanged.
        """
        loop.run_simulation_loop(self)

    def _start_auto_evaluation_if_needed(self) -> None:
        """Periodically benchmark top fish against the static evaluator."""
        # AutoEvalService removed. Now using EvolutionBenchmarkTracker only.

        # Run evolution benchmark tracker (runs in background thread when due)
        self._run_evolution_benchmark_if_needed()

    def _run_evolution_benchmark_if_needed(self) -> None:
        """Run evolution benchmark if interval has passed.

        Delegates to ``backend.runner.evolution_benchmark`` (extracted
        verbatim); the benchmark runs in a background thread and applies
        rewards under ``self.lock``.
        """
        evolution_benchmark.run_evolution_benchmark_if_needed(self)

    # Original _run_auto_evaluation and _reward_auto_eval_winners are removed
    # as they are now handled by the AutoEvalService.

    def get_state(self, force_full: bool = False, allow_delta: bool = True):
        """Get current simulation state for WebSocket broadcast.

        Delegates to StatePublisher for caching and state construction.
        """
        with self.lock:
            return self.state_publisher.get_state(
                runner=self, force_full=force_full, allow_delta=allow_delta
            )

    async def get_state_async(self, force_full: bool = False, allow_delta: bool = True):
        """Async wrapper to fetch simulation state without blocking the event loop."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_state, force_full, allow_delta)

    def serialize_state(self, state: Any) -> bytes:
        """Serialize a state payload with fast JSON and log slow frames."""
        return self.state_publisher.serialize_state(state)

    # Removed: _build_full_state
    # This logic is now likely in StatePublisher, or not needed.
    # Note: StatePublisher has its own _build_full_state.

    def _collect_entities(self) -> list[EntitySnapshot]:
        """Collect entity snapshots (delegates to stats_collector module)."""
        return stats_collector.collect_entities(self)

    def _collect_poker_stats_payload(self, stats: dict[str, Any]) -> PokerStatsPayload:
        """Delegate to state_builders module."""
        return collect_poker_stats_payload(stats)

    def _collect_stats(self, frame: int, include_distributions: bool = True) -> StatsPayload:
        """Collect and organize simulation statistics (delegates to stats_collector)."""
        return stats_collector.collect_stats(self, frame, include_distributions)

    def _sample_metrics_if_due(self) -> None:
        """Collect a history sample even when no client is requesting state."""
        frame = self.world.frame_count
        if frame > 0 and frame % self.metrics_history.sample_interval_frames == 0:
            self._collect_stats(frame, include_distributions=False)

    # Removed: _collect_poker_events, _collect_soccer_events, _collect_soccer_league_live,
    # _collect_poker_leaderboard, _collect_auto_eval (moved to WorldHooks)

    def get_full_evaluation_history(self) -> list[dict[str, Any]]:
        """Return the full auto-evaluation history."""
        return evolution_benchmark.get_full_evaluation_history(self)

    def get_evolution_benchmark_data(self) -> dict[str, Any]:
        """Return the evolution benchmark tracking data.

        Returns:
            Dictionary with benchmark history, improvement metrics, and latest snapshot.
            Returns empty dict with status if tracker not available.
        """
        return evolution_benchmark.get_evolution_benchmark_data(self)

    def _entity_to_data(self, entity: entities.Agent) -> EntitySnapshot | None:
        """Convert an entity to a lightweight snapshot for serialization.

        Kept for compatibility/greppability; delegates to `EntitySnapshotBuilder`.
        """

        return self._entity_snapshot_builder.to_snapshot(entity)

    def handle_command(self, command: str, data: dict[str, Any] | None = None):
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
                "set_soccer_league_enabled": self._cmd_set_soccer_league_enabled,
                "set_soccer_league_config": self._cmd_set_soccer_league_config,
                "start_soccer": self._cmd_start_soccer,
                "soccer_step": self._cmd_soccer_step,
                "end_soccer": self._cmd_end_soccer,
                "set_tank_soccer_enabled": self._cmd_set_tank_soccer_enabled,
            }

            # Try universal handlers first
            handler = universal_handlers.get(command)
            if handler:
                return handler(data)

            # Try fish-world handlers (tank, petri - any world with fish/poker)
            if command in tank_handlers:
                tank_only_commands = {"add_food", "spawn_fish"}
                if command in tank_only_commands and self.world_type != "tank":
                    return self._create_error_response(
                        f"Command '{command}' not supported for world_type={self.world_type}"
                    )

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

    async def handle_command_async(self, command: str, data: dict[str, Any] | None = None):
        """Async wrapper to route commands off the event loop thread."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.handle_command, command, data)
