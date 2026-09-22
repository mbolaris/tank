"""Assemble per-domain skill-progress verdicts for one world.

`core/research/skill_progress.py` decides what a series of measurements means;
this gathers the series. The three domains do not measure the same way, and
flattening that difference would be the easiest way to make the indicator lie:

* **poker** and **soccer** already record live ladder snapshots into the
  engine's `SkillSnapshotStore`, one per sampled subject.
* **foraging** has no snapshot stream. Its live signal is the observatory
  evaluation, which scores the whole population against a wandering floor and a
  perfect-oracle ceiling - a *continuous* number rather than the ladder's five
  quantised steps, and a better one. It is only ever kept as "the latest
  result", so this service retains the bounded series that a trend needs.

Foraging's series is in memory and starts empty after a restart. That is
reported honestly as `no_data` with the sample count rather than papered over:
an indicator that invented history would defeat its own purpose.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from core.research.skill_progress import ProgressAssessment, SkillObservation, assess_domain

#: Domains whose live measurements arrive as ladder snapshots.
LADDER_DOMAINS = ("poker", "soccer")
FORAGING_DOMAIN = "foraging"

#: Reported in this order: what the fish do constantly, then the two games.
DOMAINS = (FORAGING_DOMAIN, "poker", "soccer")

#: The observatory evaluates every few minutes, so this is hours of history.
MAX_FORAGING_OBSERVATIONS = 60

#: Ladder snapshots to consider. Matches SkillSnapshotStore.MAX_SNAPSHOTS.
MAX_LADDER_SNAPSHOTS = 50


def foraging_skill_index(tank_average: float, wandering_mean: float, perfect_mean: float) -> float:
    """Put a foraging score on the ladder's 0-100 scale.

    The ladder convention is 0 = floor, 100 = ceiling (core/skill/ladder.py), and
    foraging already measures both: `wandering_mean` is what a fish that ignores
    food achieves, `perfect_mean` what an oracle does. Rescaling between them
    makes foraging comparable with the other two domains instead of being a raw
    ratio that happens to look high because its floor is not zero.
    """
    span = perfect_mean - wandering_mean
    if span <= 0:
        # A degenerate ruler cannot rank anything; report the floor rather than
        # dividing by zero or inventing a percentage.
        return 0.0
    return max(0.0, (tank_average - wandering_mean) / span * 100.0)


def foraging_observation(result: dict[str, Any]) -> SkillObservation | None:
    """Convert one completed observatory evaluation into an observation.

    Returns None for anything that is not a successful evaluation carrying the
    numbers needed - a pending or failed evaluation is absence of evidence, not
    a measurement of zero.
    """
    if result.get("status") != "success":
        return None
    try:
        tank_average = float(result["tank_average"])
        wandering = float(result["wandering_mean"])
        perfect = float(result["perfect_mean"])
        frame = int(result["evaluated_at_frame"])
        generation = int(result["evaluated_at_generation"])
    except (KeyError, TypeError, ValueError):
        return None

    index = foraging_skill_index(tank_average, wandering, perfect)
    # Two rungs: clear the wandering floor, then match the oracle. Only the
    # second is the ceiling, so a population at 96% of oracle is still judged on
    # its trend rather than being congratulated as finished.
    beaten = 0
    if tank_average > wandering:
        beaten = 1
    if tank_average >= perfect:
        beaten = 2
    return SkillObservation(
        generation=generation,
        frame=frame,
        skill_index=index,
        rungs_beaten=beaten,
        total_rungs=2,
    )


class SkillProgressService:
    """Per-world skill-progress verdicts across the three evolving domains."""

    def __init__(self, world_manager: Any | None) -> None:
        self._world_manager = world_manager
        self._foraging: dict[str, deque[SkillObservation]] = {}

    # -- foraging series -------------------------------------------------

    def record_foraging_result(self, world_id: str, result: dict[str, Any]) -> None:
        """Retain one observatory evaluation as a foraging measurement.

        Repeated stores of the same evaluation are ignored by frame, so a
        replayed or re-persisted result cannot inflate the series into looking
        like more evidence than it is.
        """
        observation = foraging_observation(result)
        if observation is None:
            return
        series = self._foraging.setdefault(world_id, deque(maxlen=MAX_FORAGING_OBSERVATIONS))
        if any(existing.frame == observation.frame for existing in series):
            return
        series.append(observation)

    def foraging_observations(self, world_id: str) -> list[SkillObservation]:
        return list(self._foraging.get(world_id, ()))

    # -- ladder series ---------------------------------------------------

    def _ladder_observations(self, world_id: str, domain: str) -> list[SkillObservation]:
        store = self._snapshot_store(world_id)
        if store is None:
            return []
        snapshots = store.get_snapshots(limit=MAX_LADDER_SNAPSHOTS, domain=domain)
        observations: list[SkillObservation] = []
        for snapshot in snapshots:
            summary = getattr(snapshot, "summary", None)
            if summary is None:
                continue
            observations.append(
                SkillObservation(
                    generation=int(getattr(snapshot, "generation", 0)),
                    frame=int(getattr(snapshot, "frame", 0)),
                    skill_index=float(getattr(summary, "skill_index", 0.0)),
                    rungs_beaten=int(getattr(summary, "rungs_beaten", 0)),
                    total_rungs=int(getattr(summary, "total_rungs", 0)),
                )
            )
        return observations

    def _snapshot_store(self, world_id: str) -> Any | None:
        if self._world_manager is None:
            return None
        instance = self._world_manager.get_world(world_id)
        if instance is None:
            return None
        runner = getattr(instance, "runner", None)
        engine = getattr(runner, "engine", None) if runner else getattr(instance, "engine", None)
        return getattr(engine, "skill_snapshot_store", None) if engine else None

    # -- verdicts --------------------------------------------------------

    def assess(self, world_id: str) -> list[ProgressAssessment]:
        """One assessment per domain, always all three and always in order."""
        assessments: list[ProgressAssessment] = []
        for domain in DOMAINS:
            if domain == FORAGING_DOMAIN:
                observations = self.foraging_observations(world_id)
            else:
                observations = self._ladder_observations(world_id, domain)
            assessments.append(assess_domain(domain, observations))
        return assessments
