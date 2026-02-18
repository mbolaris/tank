"""Pluggable engine pipeline abstraction.

This module provides the EnginePipeline abstraction that allows different modes
to customize the simulation update loop without modifying SimulationEngine.

The default pipeline reproduces the exact current order of phases in Tank mode.
Other modes can provide custom pipelines to add, remove, or reorder steps.

Design Notes:
- Steps receive the engine AND a FrameContext for explicit data flow
- The pipeline is selected during engine.setup() based on the SystemPack
- Tank's default pipeline is canonical; other modes may override steps
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from collections.abc import Callable

from core.simulation.frame_context import FrameContext

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine


@dataclass
class PipelineStep:
    """A single step in the engine update pipeline.

    Attributes:
        name: Human-readable identifier for the step (e.g., "frame_start")
        fn: Function that executes this step, receiving engine and context
    """

    name: str
    fn: Callable[[SimulationEngine, FrameContext], None]


class EnginePipeline:
    """Ordered sequence of steps that define the simulation update loop.

    The pipeline is executed once per frame by SimulationEngine.update().
    Each step receives the engine instance and a FrameContext for per-frame state.
    """

    def __init__(self, steps: list[PipelineStep]) -> None:
        """Initialize the pipeline with an ordered list of steps.

        Args:
            steps: List of PipelineStep instances in execution order
        """
        self._steps = steps

    @property
    def steps(self) -> list[PipelineStep]:
        """Get the list of pipeline steps."""
        return self._steps

    @property
    def step_names(self) -> list[str]:
        """Get the names of all steps in order."""
        return [step.name for step in self._steps]

    def run(self, engine: SimulationEngine) -> None:
        """Execute all pipeline steps in order.

        Creates a fresh FrameContext for per-frame state and passes it
        through all steps, making data flow explicit.

        Args:
            engine: The SimulationEngine instance to update
        """
        ctx = FrameContext()
        for step in self._steps:
            step.fn(engine, ctx)


# =============================================================================
# Default Pipeline (Tank canonical order)
# =============================================================================


def _step_frame_start(engine: SimulationEngine, ctx: FrameContext) -> None:
    """FRAME_START: Reset counters, increment frame."""
    engine._phase_frame_start()


def _step_time_update(engine: SimulationEngine, ctx: FrameContext) -> None:
    """TIME_UPDATE: Advance day/night cycle and store time values."""
    time_modifier, time_of_day = engine._phase_time_update()
    # Store in context for use by entity_act step
    ctx.time_modifier = time_modifier
    ctx.time_of_day = time_of_day


def _step_environment(engine: SimulationEngine, ctx: FrameContext) -> None:
    """ENVIRONMENT: Update ecosystem and detection modifiers."""
    engine._phase_environment()


def _step_entity_act(engine: SimulationEngine, ctx: FrameContext) -> None:
    """ENTITY_ACT: Update all entities, collect spawns/deaths."""
    new_entities, entities_to_remove = engine._phase_entity_act(ctx.time_modifier, ctx.time_of_day)
    # Store in context for use by lifecycle step
    ctx.new_entities = new_entities
    ctx.entities_to_remove = entities_to_remove


def _step_lifecycle(engine: SimulationEngine, ctx: FrameContext) -> None:
    """LIFECYCLE: Process deaths, add/remove entities."""
    engine._phase_lifecycle(ctx.new_entities, ctx.entities_to_remove)


def _step_spawn(engine: SimulationEngine, ctx: FrameContext) -> None:
    """SPAWN: Auto-spawn food and update spatial positions."""
    engine._phase_spawn()


def _step_collision(engine: SimulationEngine, ctx: FrameContext) -> None:
    """COLLISION: Handle physical collisions between entities."""
    engine._phase_collision()


def _step_interaction(engine: SimulationEngine, ctx: FrameContext) -> None:
    """INTERACTION: Handle social interactions between entities."""
    engine._phase_interaction()


def _step_reproduction(engine: SimulationEngine, ctx: FrameContext) -> None:
    """REPRODUCTION: Handle mating and emergency spawns."""
    engine._phase_reproduction()


def _step_soccer(engine: SimulationEngine, ctx: FrameContext) -> None:
    """SOCCER: Update ball physics and agent-ball interactions."""
    soccer_system = getattr(engine, "soccer_system", None)
    if soccer_system and soccer_system.enabled:
        soccer_system.update(engine.frame_count)


def _step_frame_end(engine: SimulationEngine, ctx: FrameContext) -> None:
    """FRAME_END: Update stats, rebuild caches."""
    engine._phase_frame_end()


def default_pipeline() -> EnginePipeline:
    """Build the canonical Tank pipeline (exact current order).

    This pipeline reproduces the exact sequence of phases currently
    hard-coded in SimulationEngine.update(). It is the default for
    all modes unless they provide a custom pipeline_factory.

    Phase Order:
        1. frame_start: Reset counters, increment frame
        2. time_update: Advance day/night cycle
        3. environment: Update ecosystem and detection modifiers
        4. entity_act: Update all entities, collect spawns/deaths
        5. lifecycle: Process deaths, add/remove entities
        6. spawn: Auto-spawn food
        7. collision: Handle collisions
        8. interaction: Handle social interactions (poker)
        9. reproduction: Handle mating and emergency spawns
        10. frame_end: Update stats, rebuild caches

    Returns:
        EnginePipeline configured with Tank's canonical step order
    """
    return EnginePipeline(
        [
            PipelineStep("frame_start", _step_frame_start),
            PipelineStep("time_update", _step_time_update),
            PipelineStep("environment", _step_environment),
            PipelineStep("entity_act", _step_entity_act),
            PipelineStep("lifecycle", _step_lifecycle),
            PipelineStep("spawn", _step_spawn),
            PipelineStep("collision", _step_collision),
            PipelineStep("soccer", _step_soccer),
            PipelineStep("interaction", _step_interaction),
            PipelineStep("reproduction", _step_reproduction),
            PipelineStep("frame_end", _step_frame_end),
        ]
    )
