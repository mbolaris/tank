"""Tank world backend adapter.

This module wraps the existing TankWorld simulation to implement the
MultiAgentWorldBackend interface. It provides a domain-agnostic interface
for the fish tank ecosystem simulation without modifying the core simulation.
"""

import logging
from typing import Any, Dict, List, Optional

from core.tank_world import TankWorld, TankWorldConfig
from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend, StepResult

logger = logging.getLogger(__name__)


class TankWorldBackendAdapter(MultiAgentWorldBackend):
    """Adapter wrapping TankWorld to implement MultiAgentWorldBackend.

    This adapter:
    - Wraps existing TankWorld without changing simulation internals
    - Provides stable snapshot format for current UI rendering
    - Returns minimal observations (empty for now - no agent observations yet)
    - Exposes simulation metrics and events

    Args:
        seed: Random seed for deterministic simulation
        config: Tank world configuration (optional)
        **config_overrides: Override specific config parameters

    Example:
        >>> adapter = TankWorldBackendAdapter(seed=42, max_population=100)
        >>> result = adapter.reset(seed=42)
        >>> result = adapter.step()
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        config: Optional[TankWorldConfig] = None,
        **config_overrides,
    ):
        """Initialize the Tank world backend adapter.

        Args:
            seed: Random seed for deterministic simulation
            config: Complete TankWorldConfig (if provided, overrides are ignored)
            **config_overrides: Individual config parameters to override
        """
        self._seed = seed
        self._config_overrides = config_overrides

        # Create config from overrides if not provided
        if config is None:
            config = TankWorldConfig(**config_overrides)

        self._base_config = config
        self._world: Optional[TankWorld] = None
        self._current_frame = 0
        self._last_step_result: Optional[StepResult] = None
        self.supports_fast_step = True

    def reset(
        self, seed: Optional[int] = None, config: Optional[Dict[str, Any]] = None
    ) -> StepResult:
        """Reset the tank world to initial state.

        Args:
            seed: Random seed (overrides constructor seed if provided)
            config: Tank-specific configuration overrides

        Returns:
            StepResult with initial snapshot and metrics
        """
        # Use provided seed or fall back to constructor seed
        reset_seed = seed if seed is not None else self._seed
        if config:
            merged = {**self._base_config.to_dict(), **config}
            self._base_config = TankWorldConfig.from_dict(merged)

        # Create fresh TankWorld instance
        self._world = TankWorld(config=self._base_config, seed=reset_seed)

        # Setup the simulation (creates initial entities)
        self._world.setup()
        self._current_frame = 0

        logger.info(
            f"Tank world reset with seed={reset_seed}, " f"config={self._base_config.to_dict()}"
        )

        # Return initial state
        self._last_step_result = StepResult(
            obs_by_agent={},  # No agent observations yet
            snapshot=self._build_snapshot(),
            events=[],
            metrics=self.get_current_metrics(),
            done=False,
            info={"frame": self._current_frame, "seed": reset_seed},
        )
        return self._last_step_result

    @property
    def frame_count(self) -> int:
        """Current frame count for compatibility with legacy world runners."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing frame_count.")
        return self._world.frame_count

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused (compatibility shim)."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing paused.")
        return self._world.paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set paused state on the underlying TankWorld when available."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before setting paused.")
        self._world.paused = value

    @property
    def entities_list(self) -> List[Any]:
        """Expose entities list for snapshot builders."""
        if self._world is None:
            raise RuntimeError(
                "World not initialized. Call reset() before accessing entities_list."
            )
        return self._world.entities_list

    def setup(self) -> None:
        """Initialize the world using the backend reset."""
        self.reset(seed=self._seed)

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> StepResult:
        """Advance the tank world by one time step.

        Args:
            actions_by_agent: Agent actions (not used in Tank - autonomous simulation)

        Returns:
            StepResult with updated snapshot, events, metrics
        """
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before step().")

        fast_step = bool(actions_by_agent and actions_by_agent.get(FAST_STEP_ACTION))

        # Run one simulation tick
        self._world.update()
        self._current_frame = self._world.frame_count

        # Collect recent events (e.g., poker games)
        events = [] if fast_step else self._collect_recent_events()

        # Check if simulation is done (for now, never terminates automatically)
        done = False

        self._last_step_result = StepResult(
            obs_by_agent={},  # No agent observations yet
            snapshot=self._build_snapshot(),
            events=events,
            # Use lightweight metrics by default (no distributions) to minimize per-step cost
            metrics={} if fast_step else self.get_current_metrics(include_distributions=False),
            done=done,
            info={"frame": self._current_frame},
        )
        return self._last_step_result

    def update(self) -> None:
        """Advance the simulation by one step (compatibility shim).

        This is the hot path for the simulation loop. It uses a fast step
        path that avoids expensive metrics/event collection.
        """
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before update().")
        self.step({FAST_STEP_ACTION: True})

    def get_stats(self, include_distributions: bool = True) -> Dict[str, Any]:
        """Return current metrics for legacy callers."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before get_stats().")
        return self.get_current_metrics(include_distributions=include_distributions)

    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get current world state snapshot.

        Returns:
            Snapshot containing entities, frame count, and world dimensions
        """
        if self._world is None:
            return {}

        return self._build_snapshot()

    def get_current_metrics(self, include_distributions: bool = True) -> Dict[str, Any]:
        """Get current simulation metrics/statistics.

        Returns:
            Dictionary with simulation stats
        """
        if self._world is None:
            return {}

        return self._world.get_stats(include_distributions=include_distributions)

    def _build_snapshot(self) -> Dict[str, Any]:
        """Build a minimal snapshot of current world state.

        Returns only cheap metadata. Entity data is built separately by the
        TankSnapshotBuilder for websocket payloads, avoiding duplicate iteration.

        Returns:
            Dictionary with frame, dimensions, and paused state (no entities)
        """
        if self._world is None:
            return {}

        return {
            "frame": self._world.frame_count,
            "world_type": "tank",
            "paused": self._world.paused,
            "width": self._world.config.screen_width,
            "height": self._world.config.screen_height,
        }

    def get_debug_snapshot(self) -> Dict[str, Any]:
        """Build a full snapshot including all entities (for debugging/testing).

        This method builds a complete snapshot with entity data. It should NOT
        be called in the main simulation loop as it performs O(N_entities) work.

        Returns:
            Dictionary with frame, dimensions, paused state, and entities list
        """
        if self._world is None:
            return {}

        # Start with minimal snapshot
        snapshot = self._build_snapshot()
        # Add full entity data
        snapshot["entities"] = self._build_entities_list()
        return snapshot

    def _build_entities_list(self) -> List[Dict[str, Any]]:
        """Build list of all entities in minimal format.

        Internal helper for get_debug_snapshot(). NOT called in the hot path.

        Returns:
            List of entity dictionaries with essential attributes
        """
        if self._world is None:
            return []

        entities_snapshot = []

        for entity in self._world.entities_list:
            # Build minimal entity snapshot with essential attributes
            entity_dict = {
                "type": entity.__class__.__name__,
                "x": getattr(entity, "x", 0),
                "y": getattr(entity, "y", 0),
            }

            # Add entity-specific attributes
            if hasattr(entity, "fish_id"):
                entity_dict["fish_id"] = entity.fish_id
            if hasattr(entity, "energy"):
                entity_dict["energy"] = entity.energy
            if hasattr(entity, "generation"):
                entity_dict["generation"] = entity.generation
            if hasattr(entity, "plant_id"):
                entity_dict["plant_id"] = entity.plant_id
            if hasattr(entity, "genome"):
                # Include minimal genome data for rendering
                entity_dict["genome"] = self._extract_genome_data(entity)

            entities_snapshot.append(entity_dict)

        return entities_snapshot

    def _extract_genome_data(self, entity: Any) -> Optional[Dict[str, Any]]:
        """Extract minimal genome data for rendering.

        Args:
            entity: Entity with genome attribute

        Returns:
            Dictionary with visual genome traits or None
        """
        if not hasattr(entity, "genome"):
            return None

        genome = entity.genome

        # Extract visual traits for rendering
        genome_data = {}

        # Fish genome
        if hasattr(genome, "physical"):
            physical = genome.physical
            genome_data.update(
                {
                    "color_hue": getattr(physical, "color_hue", None),
                    "size": getattr(physical, "size_modifier", None),
                    "template_id": getattr(physical, "template_id", None),
                }
            )

        # Plant genome
        if hasattr(genome, "visual"):
            visual = genome.visual
            genome_data.update(
                {
                    "hue": getattr(visual, "hue", None),
                    "stem_height": getattr(visual, "stem_height", None),
                    "leaf_count": getattr(visual, "leaf_count", None),
                }
            )

        return genome_data if genome_data else None

    def _collect_recent_events(self) -> List[Dict[str, Any]]:
        """Collect recent events from the simulation.

        Returns:
            List of event dictionaries (e.g., poker games, reproductions)
        """
        if self._world is None:
            return []

        events = []

        # Collect recent poker events
        try:
            poker_events = self._world.get_recent_poker_events(max_age_frames=60)
            for poker_event in poker_events:
                events.append(
                    {
                        "type": "poker",
                        "data": poker_event,
                        "frame": self._world.frame_count,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to collect poker events: {e}")

        return events

    @property
    def world(self) -> Optional[TankWorld]:
        """Access underlying TankWorld instance (for debugging/testing)."""
        return self._world

    # ========================================================================
    # Legacy compatibility layer
    # ========================================================================
    # These properties and methods make TankWorldBackendAdapter a drop-in
    # replacement for TankWorld in existing backend code.

    def get_last_step_result(self) -> Optional[StepResult]:
        """Get the last StepResult from reset() or step().

        Returns:
            Last StepResult, or None if no step has occurred yet
        """
        return self._last_step_result

    @property
    def engine(self) -> Any:
        """Access underlying simulation engine for legacy compatibility.

        This allows existing backend code to access adapter.engine just like
        it accessed tank_world.engine.
        """
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing engine.")
        return getattr(self._world, "engine", None)

    @property
    def ecosystem(self) -> Any:
        """Access underlying ecosystem for legacy compatibility."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing ecosystem.")
        return getattr(self._world, "ecosystem", None)

    @property
    def config(self) -> TankWorldConfig:
        """Access configuration for legacy compatibility."""
        # Config is available before reset
        if self._world is not None:
            return self._world.config
        return self._base_config

    @property
    def rng(self) -> Any:
        """Access random number generator for legacy compatibility."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing rng.")
        return getattr(self._world, "rng", None)
