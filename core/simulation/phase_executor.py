"""Phase execution - the ordered update-phase implementations.

Extracted from SimulationEngine so the per-phase logic is an individually
testable unit. The engine keeps thin ``_phase_*`` facades that delegate here,
and the pipeline keeps driving phases through the engine, preserving the
exact execution order and mutation commit points.

Determinism notes:
- Phase order is owned by the EnginePipeline; this class only implements the
  body of each phase exactly as the engine did.
- All engine state is accessed dynamically through the engine reference, so
  monkeypatching engine attributes (e.g. ``_apply_entity_mutations`` in
  invariant tests) keeps working unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.update_phases import PHASE_DESCRIPTIONS, UpdatePhase

if TYPE_CHECKING:
    from core import entities
    from core.simulation.engine import SimulationEngine


class PhaseExecutor:
    """Executes the ordered update phases on behalf of the engine.

    Tracks the currently running phase (used to guard privileged entity
    mutations) and implements each phase body by coordinating the engine's
    SystemCoordinator, mutation commits, and phase hooks.
    """

    def __init__(self, engine: SimulationEngine) -> None:
        self._engine = engine
        self.current_phase: UpdatePhase | None = None

    def describe_phase(self, phase: UpdatePhase | None = None) -> str:
        """Get a human-readable description of a phase."""
        if phase is None:
            phase = self.current_phase
        if phase is None:
            return "Not in update loop"
        return PHASE_DESCRIPTIONS.get(phase, phase.name)

    # -------------------------------------------------------------------------
    # Phase Implementations (invoked via the engine's _phase_* facades)
    # -------------------------------------------------------------------------

    def frame_start(self) -> None:
        """FRAME_START: Reset counters, increment frame."""
        engine = self._engine
        self.current_phase = UpdatePhase.FRAME_START
        engine.frame_count += 1

        # Clear frame output buffers from previous frame
        engine.frame_aggregator.clear()

        engine.coordinator.run_frame_start(engine.frame_count)
        engine._apply_entity_mutations("frame_start")

    def time_update(self) -> tuple[float, float]:
        """TIME_UPDATE: Advance day/night cycle and store time values."""
        engine = self._engine
        self.current_phase = UpdatePhase.TIME_UPDATE

        time_modifier = 1.0
        time_of_day = 0.5
        if engine.time_system:
            engine.time_system.update(engine.frame_count)
            time_modifier = engine.time_system.get_activity_modifier()
            time_of_day = engine.time_system.get_time_of_day()

        engine._apply_entity_mutations("time_update")
        return time_modifier, time_of_day

    def environment(self) -> None:
        """ENVIRONMENT: Update ecosystem and detection modifiers."""
        engine = self._engine
        self.current_phase = UpdatePhase.ENVIRONMENT
        engine.coordinator.run_environment(engine.frame_count)
        engine._apply_entity_mutations("environment")

    def entity_act(
        self,
        time_modifier: float,
        time_of_day: float,
    ) -> tuple[list[entities.Agent], list[entities.Agent]]:
        """ENTITY_ACT: Update all entities, collect spawns/deaths."""
        engine = self._engine
        self.current_phase = UpdatePhase.ENTITY_ACT

        new_entities, entities_to_remove = engine.coordinator.run_entity_act(
            engine.frame_count,
            time_modifier,
            time_of_day,
            engine,
        )
        return new_entities, entities_to_remove

    def lifecycle(
        self,
        new_entities: list[entities.Agent],
        entities_to_remove: list[entities.Agent],
    ) -> None:
        """LIFECYCLE: Process deaths, add/remove entities."""
        engine = self._engine
        self.current_phase = UpdatePhase.LIFECYCLE

        engine.coordinator.run_lifecycle(engine, new_entities, entities_to_remove)

        engine._apply_entity_mutations("lifecycle")

    def spawn(self) -> None:
        """SPAWN: Auto-spawn food and update spatial positions."""
        engine = self._engine
        self.current_phase = UpdatePhase.SPAWN
        engine.coordinator.run_spawn(engine.frame_count)
        engine._apply_entity_mutations("spawn")

        # Update spatial grid for moved entities
        if engine.environment is not None:
            update_position = engine.environment.update_agent_position
            for entity in engine.entity_manager.entities_list:
                update_position(entity)

    def collision(self) -> None:
        """COLLISION: Handle physical collisions between entities."""
        engine = self._engine
        self.current_phase = UpdatePhase.COLLISION
        engine.coordinator.run_collision(engine.frame_count)
        engine._apply_entity_mutations("collision")

    def interaction(self) -> None:
        """INTERACTION: Handle social interactions between entities."""
        engine = self._engine
        self.current_phase = UpdatePhase.INTERACTION
        engine.coordinator.run_interaction(engine.frame_count)
        engine._apply_entity_mutations("interaction")

    def reproduction(self) -> None:
        """REPRODUCTION: Handle mating and emergency spawns."""
        engine = self._engine
        self.current_phase = UpdatePhase.REPRODUCTION

        engine.coordinator.run_reproduction(engine.frame_count)
        engine._apply_entity_mutations("reproduction")

        if engine._phase_hooks:
            engine._phase_hooks.on_reproduction_complete(engine)

    def frame_end(self) -> None:
        """FRAME_END: Update stats, rebuild caches."""
        engine = self._engine
        self.current_phase = UpdatePhase.FRAME_END

        if engine._phase_hooks:
            engine._phase_hooks.on_frame_end(engine)

        # Prune stale identity mappings
        if engine._identity_provider is not None and hasattr(
            engine._identity_provider, "prune_stale_ids"
        ):
            current_entity_ids = {id(e) for e in engine.entity_manager.entities_list}
            engine._identity_provider.prune_stale_ids(current_entity_ids)

        if engine.entity_manager.is_dirty:
            engine._rebuild_caches()

        if engine._phase_debug_enabled:
            pending_spawns = engine.mutations.pending_spawn_count()
            pending_removals = engine.mutations.pending_removal_count()
            if pending_spawns or pending_removals:
                raise RuntimeError(
                    "End-of-frame invariant violated: pending entity mutations remain "
                    f"(spawns={pending_spawns}, removals={pending_removals})"
                )

        self.current_phase = None
