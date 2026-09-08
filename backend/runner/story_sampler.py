"""Build a :class:`StorySample` from a live runner, on the detection cadence.

This is the only place the story-event service touches the simulation, and it is
strictly read-only: it iterates the living agents and reads the lineage log. It
does not call ``get_lineage_data()`` (which repairs orphans in place), does not
draw from any RNG stream, and does not write to the world — the E3 guardrail is
that detecting a story must never change the story.

The scan runs on a fixed frame cadence (see
``StoryEventService.detect_interval_frames``), not on every broadcast, so its
cost is amortized and its results do not depend on how many clients are
connected.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from backend.story_detectors import StorySample
from backend.story_event_service import StoryEventService
from core.config.display import FRAME_RATE

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)

# Guards the ancestry walk against a malformed log with a parent cycle.
MAX_ANCESTRY_DEPTH = 10000


def observe_if_due(runner: SimulationRunner) -> list[dict[str, Any]]:
    """Sample the world and run the story detectors when the frame is due.

    Returns the newly stored events (empty on a frame that is not due, on a
    world without a story service, or on any failure). Telemetry must never be
    able to break the simulation loop, so every error is swallowed and logged.
    """
    service: StoryEventService | None = getattr(runner, "story_events", None)
    if service is None:
        return []
    try:
        frame = int(runner.world.frame_count)
        if not service.is_detection_due(frame):
            return []
        return service.observe(build_sample(runner, frame))
    except Exception:
        logger.warning("Story-event detection failed; skipping this sample.", exc_info=True)
        return []


def build_sample(runner: SimulationRunner, frame: int) -> StorySample:
    """Read the living population and its founder lineages into a sample."""
    living = living_agents(runner)
    population = len(living)
    max_generation = max((int(getattr(a, "generation", 0) or 0) for a in living), default=0)

    return StorySample(
        frame=frame,
        simulation_time=frame / FRAME_RATE if FRAME_RATE else 0.0,
        population=population,
        max_generation=max_generation,
        lineage_members=lineage_members_for(runner, living),
    )


def living_agents(runner: SimulationRunner) -> list[Any]:
    """The living, reproducing agents — the population a viewer would count.

    Identified structurally (a heritable genome plus a stable ``fish_id``) so
    this works for any tank-like world without importing world-specific types.
    """
    entities = getattr(runner.world, "entities_list", None) or []
    return [e for e in entities if hasattr(e, "genome") and getattr(e, "fish_id", None) is not None]


def lineage_members_for(runner: SimulationRunner, living: list[Any]) -> dict[str, list[int]]:
    """Group living agents by the founder each one descends from.

    Shared with the legend sampler: a "founder" must mean the same thing to the
    lineage-share detector and to the lineage-founder legend criterion.

    A founder is the oldest recorded ancestor: walk ``parent_id`` up the lineage
    log until it hits ``"root"`` or an id the log does not contain. An agent with
    no lineage record at all founds its own line.
    """
    parent_of = _parent_map(runner)
    members: dict[str, list[int]] = {}
    founder_of: dict[str, str] = {}

    for agent in living:
        agent_id = str(agent.fish_id)
        founder = _founder(agent_id, parent_of, founder_of)
        members.setdefault(founder, []).append(int(agent.fish_id))

    return members


def _parent_map(runner: SimulationRunner) -> dict[str, str]:
    """``child id -> parent id`` from the world's lineage log, or empty."""
    try:
        ecosystem = getattr(runner.world, "ecosystem", None)
    except Exception:
        # Worlds expose ``ecosystem`` as a property that raises before reset().
        return {}
    tracker = getattr(ecosystem, "lineage", None)
    log = getattr(tracker, "lineage_log", None)
    if not log:
        return {}
    return {
        str(record["id"]): str(record.get("parent_id", "root"))
        for record in log
        if isinstance(record, dict) and "id" in record
    }


def _founder(agent_id: str, parent_of: dict[str, str], memo: dict[str, str]) -> str:
    """Walk to the oldest recorded ancestor, memoizing the whole chain."""
    chain: list[str] = []
    current = agent_id
    while current not in memo:
        chain.append(current)
        parent = parent_of.get(current)
        if parent is None or parent == "root" or parent == current:
            memo[current] = current
            break
        if len(chain) > MAX_ANCESTRY_DEPTH:
            logger.warning(
                "Lineage ancestry walk exceeded %d hops; treating %s as a founder.",
                MAX_ANCESTRY_DEPTH,
                current,
            )
            memo[current] = current
            break
        current = parent

    founder = memo[current]
    for node in chain:
        memo[node] = founder
    return founder
