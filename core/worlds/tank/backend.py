"""Tank world backend adapter.

This module provides a MultiAgentWorldBackend for the fish tank ecosystem
simulation. It directly uses the SimulationEngine with TankPack, providing
a clean interface without any legacy wrappers.
"""

import logging
import random
from typing import Any, Dict, List, Optional

from core.config.simulation_config import SimulationConfig
from core.simulation import SimulationEngine
from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend, StepResult
from core.worlds.tank.action_bridge import apply_actions
from core.worlds.tank.observation_builder import build_tank_observations
from core.worlds.tank.pack import TankPack

logger = logging.getLogger(__name__)


class TankWorldBackendAdapter(MultiAgentWorldBackend):
    """Backend adapter for the Tank world ecosystem simulation.

    This adapter:
    - Directly uses SimulationEngine + TankPack (no legacy wrappers)
    - Provides stable snapshot format for UI rendering
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
        config: Optional[Dict[str, Any]] = None,
        **config_overrides,
    ):
        """Initialize the Tank world backend adapter.

        Args:
            seed: Random seed for deterministic simulation
            config: Optional config dict
            **config_overrides: Individual config parameters to override
        """
        self._seed = seed

        # Start with production defaults
        base_config = SimulationConfig.production(headless=True)

        merged_config = {}
        if config and isinstance(config, dict):
            merged_config.update(config)
        elif config and hasattr(config, "apply_flat_config"):
            # If it's already a SimulationConfig, use it as the base
            base_config = config

        if config_overrides:
            merged_config.update(config_overrides)

        self._simulation_config = base_config.apply_flat_config(merged_config)
        self._engine: Optional[SimulationEngine] = None
        self._pack: Optional[TankPack] = None
        self._rng: Optional[random.Random] = None
        self._current_frame = 0
        self._last_step_result: Optional[StepResult] = None
        self._cached_brain_mode: Optional[str] = None  # Cached brain mode for hot path
        self.supports_fast_step = True

    @property
    def environment(self):
        """Expose the underlying simulation environment."""
        return self._engine.environment if self._engine else None

    def add_entity(self, entity) -> None:
        """Add an entity to the world (shim for tests)."""
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before add_entity().")
        self._engine.add_entity(entity)

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
            self._simulation_config = self._simulation_config.apply_flat_config(config)

        # Create RNG from seed
        if reset_seed is None:
            # Fallback to a default seed if none provided to satisfy determinism policy
            reset_seed = 42

        self._rng = random.Random(reset_seed)

        # Create fresh SimulationEngine
        self._engine = SimulationEngine(
            config=self._simulation_config,
            rng=self._rng,
            seed=reset_seed,
        )

        # Setup with pack (either provided or default TankPack)
        self._pack = pack or TankPack(self._simulation_config)
        self._engine.setup(self._pack)
        self._current_frame = 0

        # Clear cached brain mode on reset
        self._cached_brain_mode = None

        logger.info(
            f"Tank world reset with seed={reset_seed}, " f"config={self._simulation_config}"
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
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before accessing frame_count.")
        return self._engine.frame_count

    @frame_count.setter
    def frame_count(self, value: int) -> None:
        """Set the frame count on the underlying engine."""
        if self._engine is not None:
            self._engine.frame_count = value
        self._current_frame = value

    @property
    def paused(self) -> bool:
        """Whether the simulation is paused."""
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before accessing paused.")
        return self._engine.paused

    @paused.setter
    def paused(self, value: bool) -> None:
        """Set paused state on the underlying engine."""
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before setting paused.")
        self._engine.paused = value

    @property
    def is_paused(self) -> bool:
        """Whether the simulation is paused (protocol method)."""
        if self._engine is None:
            return False
        return self._engine.paused

    def set_paused(self, value: bool) -> None:
        """Set the simulation paused state (protocol method)."""
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before setting paused.")
        self._engine.paused = value

    @property
    def entities_list(self) -> List[Any]:
        """Expose entities list for snapshot builders."""
        if self._engine is None:
            raise RuntimeError(
                "World not initialized. Call reset() before accessing entities_list."
            )
        return self._engine.entities_list

    def get_entities_for_snapshot(self) -> List[Any]:
        """Get entities for snapshot building (protocol method)."""
        if self._engine is None:
            return []
        return self._engine.entities_list

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

        brain_mode = "builtin"
        if self._engine is not None:
            config = getattr(self._engine, "config", None)
            if config is not None:
                tank_config = getattr(config, "tank", None)
                if tank_config is not None:
                    brain_mode = getattr(tank_config, "brain_mode", "builtin")

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
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before step().")

        fast_step = bool(actions_by_agent and actions_by_agent.get(FAST_STEP_ACTION))

        # Get brain mode (cached)
        brain_mode = self._get_brain_mode()

        # External brain mode: build observations and apply actions
        obs_by_agent: Dict[str, Any] = {}
        if brain_mode == "external" and not fast_step:
            observations = build_tank_observations(self)
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
                    apply_actions(action_map, self)

        # Run simulation tick
        self._engine.update()
        self._current_frame = self._engine.frame_count

        # Drain frame outputs from engine
        # This is the authoritative source for what happened this frame
        frame_outputs = self._engine.drain_frame_outputs()

        # Feed energy deltas to ecosystem for stats tracking
        if self._engine.ecosystem is not None and hasattr(
            self._engine.ecosystem, "ingest_energy_deltas"
        ):
            self._engine.ecosystem.ingest_energy_deltas(frame_outputs.energy_deltas)

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
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before update().")

        self._engine.update()
        self._current_frame = self._engine.frame_count

    def get_stats(self, include_distributions: bool = True) -> Dict[str, Any]:
        """Return current metrics."""
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before get_stats().")
        return self.get_current_metrics(include_distributions=include_distributions)

    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get current world state snapshot.

        Returns:
            Snapshot containing entities, frame count, and world dimensions
        """
        if self._engine is None:
            return {}

        return self._build_snapshot()

    def get_current_metrics(self, include_distributions: bool = True) -> Dict[str, Any]:
        """Get current simulation metrics/statistics.

        Returns:
            Dictionary with simulation stats
        """
        if self._engine is None:
            return {}

        metrics = self._engine.get_stats(include_distributions=include_distributions)
        # Ensure frame count is always present in metrics for contract conformance
        if "frame" not in metrics:
            metrics["frame"] = self._engine.frame_count
        return metrics

    def _build_snapshot(self) -> Dict[str, Any]:
        """Build a minimal snapshot of current world state.

        Returns only cheap metadata. Entity data is built separately by the
        TankSnapshotBuilder for websocket payloads, avoiding duplicate iteration.

        Returns:
            Dictionary with frame, dimensions, and paused state (no entities)
        """
        if self._engine is None:
            return {}

        return {
            "frame": self._engine.frame_count,
            "world_type": "tank",
            "paused": self._engine.paused,
            "width": self._simulation_config.display.screen_width,
            "height": self._simulation_config.display.screen_height,
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
        if self._engine is None:
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
        if self._engine is None:
            return []

        # Import locally to avoid circular imports
        from core.entities import Fish, Food, Plant, PlantNectar
        from core.entities.base import Castle
        from core.entities.predators import Crab
        from core.transfer.entity_transfer import serialize_entity_for_transfer

        # Import soccer types
        try:
            from core.entities.ball import Ball
            from core.entities.goal_zone import GoalZone
        except ImportError:
            Ball = None
            GoalZone = None

        entities_snapshot = []

        for entity in self._engine.entities_list:
            # Skip transient soccer entities - they are respawned by SoccerSystem on restore
            if Ball and isinstance(entity, Ball):
                continue
            if GoalZone and isinstance(entity, GoalZone):
                continue

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
                    "hunt_cooldown": getattr(entity, "hunt_cooldown", 0),
                    "genome_data": entity.genome.to_dict(),
                    "motion": {
                        "theta": getattr(entity, "_orbit_theta", None),
                        "dir": getattr(entity, "_orbit_dir", None),
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
            elif Ball and isinstance(entity, Ball):
                entity_dict = {
                    "type": "ball",
                    "id": entity.id,
                    "x": entity.pos.x,
                    "y": entity.pos.y,
                    "radius": entity.radius,
                    "vx": entity.vel.x,
                    "vy": entity.vel.y,
                    # Width/height for frontend compat
                    "width": entity.radius * 2,
                    "height": entity.radius * 2,
                }
            elif GoalZone and isinstance(entity, GoalZone):
                entity_dict = {
                    "type": "goalzone",
                    "id": entity.id,
                    "x": entity.pos.x,
                    "y": entity.pos.y,
                    "radius": entity.radius,
                    "team": entity.team_id,
                    "width": entity.radius * 2,
                    "height": entity.radius * 2,
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
        if self._engine is None:
            return []

        events = []

        # Collect recent poker events
        try:
            poker_events = self._engine.get_recent_poker_events(max_age_frames=60)
            for poker_event in poker_events:
                events.append(
                    {
                        "type": "poker",
                        "data": poker_event,
                        "frame": self._engine.frame_count,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to collect poker events: {e}")

        # Collect recent soccer events
        try:
            soccer_events = self._engine.get_recent_soccer_events(max_age_frames=60)
            for soccer_event in soccer_events:
                events.append(
                    {
                        "type": "soccer",
                        "data": soccer_event,
                        "frame": self._engine.frame_count,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to collect soccer events: {e}")

        return events

    # ========================================================================
    # Compatibility layer - expose engine internals for existing code
    # ========================================================================

    def get_last_step_result(self) -> Optional[StepResult]:
        """Get the last StepResult from reset() or step().

        Returns:
            Last StepResult, or None if no step has occurred yet
        """
        return self._last_step_result

    @property
    def engine(self) -> Any:
        """Access underlying simulation engine.

        This allows existing backend code to access adapter.engine.
        """
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before accessing engine.")
        return self._engine

    @property
    def ecosystem(self) -> Any:
        """Access underlying ecosystem."""
        if self._engine is None:
            raise RuntimeError("World not initialized. Call reset() before accessing ecosystem.")
        return self._engine.ecosystem

    @property
    def config(self) -> SimulationConfig:
        """Access configuration."""
        return self._simulation_config

    @property
    def rng(self) -> Any:
        """Access random number generator."""
        if self._rng is None:
            raise RuntimeError("World not initialized. Call reset() before accessing rng.")
        return self._rng

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
        if self._engine is None:
            return {}

        # Import locally to avoid circular imports (backend -> core)
        from core.contracts import SNAPSHOT_VERSION

        return {
            "schema_version": SNAPSHOT_VERSION,
            "world_id": getattr(self.environment, "world_id", "unknown"),
            "frame": self._engine.frame_count,
            "paused": self._engine.paused,
            "config": {},  # Config serialization should be handled by SimulationConfig
            "seed": self._seed,
            "entities": self._build_entities_list(),
        }

    def restore_state_from_save(self, state: Dict[str, Any]) -> None:
        """Restore world state from a saved snapshot.

        Note: Full restoration including entities is handled by
        world_persistence.restore_world_from_snapshot(). This method restores
        basic world metadata.

        Args:
            state: Previously captured state dictionary
        """
        if self._engine is None:
            return

        # Restore pause state if present
        if "paused" in state:
            self._engine.paused = state["paused"]

    # ========================================================================
    # Legacy TankWorld-compatible properties (for smooth transition)
    # ========================================================================

    def get_recent_poker_events(self, max_age_frames: int = 180) -> List[Dict[str, Any]]:
        """Get recent poker events (TankWorld API compatibility)."""
        if self._engine is None:
            return []
        return self._engine.get_recent_poker_events(max_age_frames)

    def get_soccer_league_live_state(self) -> Optional[Dict[str, Any]]:
        """Get live league match state for rendering."""
        if self._engine is None:
            return None
        return self._engine.get_soccer_league_live_state()
