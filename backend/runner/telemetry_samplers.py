"""Run the read-only telemetry samplers that are due this frame.

Story events and legends both observe the same living population on their own
cadences. Driving them from one place keeps the simulation loop's view of
telemetry to a single call, and makes the ordering explicit: story events are
sampled first, so a legend promoted on the same frame is evaluated against a
world whose facts have already been recorded.

Every sampler here is strictly read-only and swallows its own failures -
telemetry must never be able to break the step loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.runner import legend_sampler, story_sampler

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner


def observe_all_if_due(runner: SimulationRunner) -> None:
    """Sample every telemetry surface whose cadence lands on this frame."""
    story_sampler.observe_if_due(runner)
    legend_sampler.observe_if_due(runner)
