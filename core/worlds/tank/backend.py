"""Tank world backend adapter.

This module wraps the existing TankWorld simulation to implement the
MultiAgentWorldBackend interface. It provides a domain-agnostic interface
for the fish tank ecosystem simulation without modifying the core simulation.
"""

import logging
from typing import Any, Dict, List, Optional

from core.tank_world import TankWorld, TankWorldConfig
from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend, StepResult
from core.worlds.tank.legacy_brain_adapter import apply_actions
from core.worlds.tank.observation_builder import build_tank_observations

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
        self._cached_brain_mode: Optional[str] = None  # Cached brain mode for hot path
        self.supports_fast_step = True

    @property
    def environment(self):
        """Expose the underlying simulation environment."""
        return self._world.environment if self._world else None

    def add_entity(self, entity) -> None:
        """Add an entity to the world (shim for tests)."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before add_entity().")
        self._world.add_entity(entity)

    def reset(
        self,
        seed: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        pack: Optional["SystemPack"] = None,
    ) -> StepResult:
        """Reset the tank world to initial state.

        Args:
            seed: Random seed (overrides constructor seed if provided)
            config: Tank-specific configuration overrides
            pack: Optional SystemPack to use
        """
        # Use provided seed or fall back to constructor seed
        reset_seed = seed if seed is not None else self._seed
        if config:
            merged = {**self._base_config.to_dict(), **config}
            self._base_config = TankWorldConfig.from_dict(merged)

        # Create fresh TankWorld instance
        self._world = TankWorld(config=self._base_config, seed=reset_seed, pack=pack)

        # Setup the simulation (creates initial entities)
        self._world.setup()
        self._current_frame = 0

        logger.info(
            f"Tank world reset with seed={reset_seed}, " f"config={self._base_config.to_dict()}"
        )

        # Return initial state
        snapshot = self._build_snapshot()
        self._last_step_result = StepResult(
            obs_by_agent={},  # No agent observations yet
            snapshot=snapshot,
            events=[],
            metrics=self.get_current_metrics(),
            done=False,
            info={"frame": self._current_frame, "seed": reset_seed},
            spawns=[],
            removals=[],
            energy_deltas=[],
            render_hint=snapshot.get("render_hint"),
        )
        return self._last_step_result

    @property
    def frame_count(self) -> int:
        """Current frame count."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing frame_count.")
        return self._world.frame_count

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused."""
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
    def is_paused(self) -> bool:
        """Whether the simulation is paused (protocol method)."""
        if self._world is None:
            return False
        return self._world.paused

    def set_paused(self, value: bool) -> None:
        """Set the simulation paused state (protocol method)."""
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

    def get_entities_for_snapshot(self) -> List[Any]:
        """Get entities for snapshot building (protocol method)."""
        if self._world is None:
            return []
        return self._world.entities_list

    @property
    def world_type(self) -> str:
        """The world type identifier (protocol method)."""
        return "tank"

    def setup(self) -> None:
        """Initialize the world using the backend reset."""
        self.reset(seed=self._seed)

    def _get_brain_mode(self) -> str:
        """Get brain mode with caching for hot path optimization."""
        if self._cached_brain_mode is not None:
            return self._cached_brain_mode

        brain_mode = "legacy"
        if self._world is not None:
            engine = getattr(self._world, "engine", None)
            if engine is not None:
                config = getattr(engine, "config", None)
                if config is not None:
                    tank_config = getattr(config, "tank", None)
                    if tank_config is not None:
                        brain_mode = getattr(tank_config, "brain_mode", "legacy")

        self._cached_brain_mode = brain_mode
        return brain_mode

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> StepResult:
        """Advance the tank world by one time step.

        The step now follows an action pipeline internally:
        1. Get brain mode (cached)
        2. Build observations if external mode
        3. Apply external actions if provided
        4. Run physics/collision/lifecycle
        5. Return result

        Args:
            actions_by_agent: Agent actions. Pass {FAST_STEP_ACTION: True} for fast stepping.

        Returns:
            StepResult with updated snapshot, events, metrics
        """
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before step().")

        fast_step = bool(actions_by_agent and actions_by_agent.get(FAST_STEP_ACTION))

        # Get brain mode (cached)
        brain_mode = self._get_brain_mode()

        # External brain mode: build observations and apply actions
        obs_by_agent: Dict[str, Any] = {}
        if brain_mode == "external" and not fast_step:
            observations = build_tank_observations(self._world)
            obs_by_agent = {str(k): v.__dict__ for k, v in observations.items()}

            if actions_by_agent:
                external_actions = {
                    k: v for k, v in actions_by_agent.items() if k != FAST_STEP_ACTION
                }
                if external_actions:
                    from core.brains.contracts import BrainAction as Action

                    action_map = {}
                    for entity_id, action_data in external_actions.items():
                        if isinstance(action_data, Action):
                            action_map[entity_id] = action_data
                        elif isinstance(action_data, dict):
                            action_map[entity_id] = Action(
                                entity_id=entity_id,
                                target_velocity=action_data.get("target_velocity", (0, 0)),
                                extra=action_data.get("extra", {}),
                            )
                    apply_actions(action_map, self._world)

        # Run simulation tick
        self._world.update()
        self._current_frame = self._world.frame_count

        # Drain frame outputs from engine
        # This is the authoritative source for what happened this frame
        frame_outputs = self.engine.drain_frame_outputs()

        # Feed energy deltas to ecosystem for stats tracking
        if getattr(self._world, "ecosystem", None) and hasattr(
            self._world.ecosystem, "ingest_energy_deltas"
        ):
            self._world.ecosystem.ingest_energy_deltas(frame_outputs.energy_deltas)

        # Build result
        snapshot = self._build_snapshot()
        self._last_step_result = StepResult(
            obs_by_agent=obs_by_agent,
            snapshot=snapshot,
            events=[] if fast_step else self._collect_recent_events(),
            metrics={} if fast_step else self.get_current_metrics(include_distributions=False),
            done=False,
            info={"frame": self._current_frame, "brain_mode": brain_mode},
            spawns=frame_outputs.spawns,
            removals=frame_outputs.removals,
            energy_deltas=frame_outputs.energy_deltas,
            render_hint=snapshot.get("render_hint"),
        )
        return self._last_step_result

    def update(self) -> None:
        """Advance the simulation by one step.

        This is the hot path for the simulation loop. It uses a fast step
        path that avoids expensive metrics/event collection.
        """
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before update().")
        self.step({FAST_STEP_ACTION: True})

    def get_stats(self, include_distributions: bool = True) -> Dict[str, Any]:
        """Return current metrics."""
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

        metrics = self._world.get_stats(include_distributions=include_distributions)
        # Ensure frame count is always present in metrics for contract conformance
        if "frame" not in metrics:
            metrics["frame"] = self._world.frame_count
        return metrics

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
            "render_hint": {
                "style": "side",
                "entity_style": "fish",
            },
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
        """Build list of all entities for persistence/debugging.

        Uses the proper entity transfer codecs to ensure full serialization
        compatible with restore_tank_from_snapshot.

        Returns:
            List of fully serialized entity dictionaries
        """
        if self._world is None:
            return []

        # Import locally to avoid circular imports
        from core.entities import Fish, Food, Plant, PlantNectar
        from core.entities.base import Castle
        from core.entities.predators import Crab
        from core.transfer.entity_transfer import serialize_entity_for_transfer

        entities_snapshot = []

        for entity in self._world.entities_list:
            entity_dict = None

            # Use transfer codecs for Fish and Plant (full serialization)
            if isinstance(entity, (Fish, Plant)):
                entity_dict = serialize_entity_for_transfer(entity)
            elif isinstance(entity, PlantNectar):
                # PlantNectar needs special handling - include source_plant_id
                entity_dict = {
                    "type": "plant_nectar",
                    "x": entity.pos.x,
                    "y": entity.pos.y,
                    "energy": entity.energy,
                    "source_plant_id": (
                        entity.source_plant.plant_id if entity.source_plant else None
                    ),
                }
            elif isinstance(entity, Food):
                entity_dict = {
                    "type": "food",
                    "x": entity.pos.x,
                    "y": entity.pos.y,
                    "energy": entity.energy,
                    "food_type": getattr(entity, "food_type", "regular"),
                }
            elif isinstance(entity, Crab):
                entity_dict = {
                    "type": "crab",
                    "x": entity.pos.x,
                    "y": entity.pos.y,
                    "energy": entity.energy,
                    "max_energy": entity.max_energy,
                    "hunt_cooldown": getattr(entity, "hunt_cooldown", 0),
                    "genome": {
                        "size_modifier": (
                            entity.genome.physical.size_modifier.value if entity.genome else 1.0
                        ),
                        "color_hue": (
                            entity.genome.physical.color_hue.value if entity.genome else 0.5
                        ),
                    },
                }
            elif isinstance(entity, Castle):
                entity_dict = {
                    "type": "castle",
                    "x": entity.pos.x,
                    "y": entity.pos.y,
                    "width": entity.width,
                    "height": entity.height,
                }
            else:
                # Fallback for unknown entity types
                entity_dict = {
                    "type": entity.__class__.__name__.lower(),
                    "x": getattr(
                        entity, "x", getattr(entity.pos, "x", 0) if hasattr(entity, "pos") else 0
                    ),
                    "y": getattr(
                        entity, "y", getattr(entity.pos, "y", 0) if hasattr(entity, "pos") else 0
                    ),
                }

            if entity_dict:
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
        """Access underlying simulation engine.

        This allows existing backend code to access adapter.engine just like
        it accessed tank_world.engine.
        """
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing engine.")
        return getattr(self._world, "engine", None)

    @property
    def ecosystem(self) -> Any:
        """Access underlying ecosystem."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing ecosystem.")
        return getattr(self._world, "ecosystem", None)

    @property
    def config(self) -> TankWorldConfig:
        """Access configuration."""
        # Config is available before reset
        if self._world is not None:
            return self._world.config
        return self._base_config

    @property
    def rng(self) -> Any:
        """Access random number generator."""
        if self._world is None:
            raise RuntimeError("World not initialized. Call reset() before accessing rng.")
        return getattr(self._world, "rng", None)

    # ========================================================================
    # Protocol methods for state persistence
    # ========================================================================

    def capture_state_for_save(self) -> Dict[str, Any]:
        """Capture complete world state for persistence.

        This provides a lightweight snapshot that can be serialized.
        For full save functionality including entity serialization,
        use SimulationManager.capture_state_for_save() which handles
        lock acquisition and entity serialization.

        Returns:
            Serializable dictionary containing world metadata.
        """
        if self._world is None:
            return {}

        # Import locally to avoid circular imports (backend -> core)
        from core.worlds.tank.schema import SCHEMA_VERSION

        return {
            "version": SCHEMA_VERSION,
            "tank_id": getattr(self, "tank_id", "unknown"),
            "frame": self._world.frame_count,
            "paused": self._world.paused,
            "config": self._base_config.to_dict(),
            "seed": self._seed,
            "entities": self._build_entities_list(),
        }

    def restore_state_from_save(self, state: Dict[str, Any]) -> None:
        """Restore world state from a saved snapshot.

        Note: Full restoration including entities is handled by
        tank_persistence.restore_tank_state(). This method restores
        basic world metadata.

        Args:
            state: Previously captured state dictionary
        """
        if self._world is None:
            return

        # Restore pause state if present
        if "paused" in state:
            self._world.paused = state["paused"]
