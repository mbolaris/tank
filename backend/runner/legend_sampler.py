"""Build a :class:`LegendSample` from a live runner, on the legend cadence.

Strictly read-only, exactly like the story sampler: it iterates the living
agents and reads the lineage log directly rather than calling
``get_lineage_data()``, which repairs orphans in place. Deciding who becomes a
legend must never change the world that produced them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from backend.legend_criteria import LegendSample
from backend.legend_service import LegendService
from backend.runner.story_sampler import lineage_members_for, living_agents
from core.config.display import FRAME_RATE

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


def observe_if_due(runner: SimulationRunner) -> list[dict[str, Any]]:
    """Sample the world and run the legend criteria when the frame is due.

    Returns newly promoted legends (empty on a frame that is not due, on a world
    without a legend service, or on any failure). Telemetry must never be able
    to break the simulation loop.
    """
    service: LegendService | None = getattr(runner, "legends", None)
    if service is None:
        return []
    try:
        frame = int(runner.world.frame_count)
        if not service.is_evaluation_due(frame):
            return []
        return service.observe(build_sample(runner, frame))
    except Exception:
        logger.warning("Legend evaluation failed; skipping this sample.", exc_info=True)
        return []


def build_sample(runner: SimulationRunner, frame: int) -> LegendSample:
    """Read the living population, their ages, and their founder lineages."""
    living = living_agents(runner)
    ages = {
        int(agent.fish_id): int(getattr(agent, "age", 0) or 0)
        for agent in living
        if getattr(agent, "fish_id", None) is not None
    }
    return LegendSample(
        frame=frame,
        simulation_time=frame / FRAME_RATE if FRAME_RATE else 0.0,
        population=len(living),
        ages=ages,
        lineage_members=lineage_members_for(runner, living),
    )
