"""The three story-event detectors E3 ships with.

Detectors are **pure functions of a sample sequence**. They take a
:class:`StorySample` — a plain read-only snapshot of a few simulation numbers —
and return event records. They never touch the world, never consume RNG, and
never mutate simulation state, so running them cannot perturb an experiment.
That also makes them testable against synthetic sample sequences, which is how
their thresholds are pinned in ``tests/test_story_events.py``.

Every detector is **latched**: it fires on the *transition* across a threshold
and stays silent while the metric remains on that side of it. Population uses
explicit hysteresis (a lower entry threshold than exit threshold) so a metric
hovering on the boundary cannot chatter a feed full of duplicates.

Detector state is part of the persisted payload, so a world restored from a
snapshot does not re-announce facts a viewer has already been told.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from backend.story_events import make_event
from core.config.ecosystem import CRITICAL_POPULATION_THRESHOLD

logger = logging.getLogger(__name__)

# One fish below the line at which the ecosystem force-spawns to avoid extinction.
# Deriving it from the simulation's own constant keeps the two honest about each
# other, and picking "past" rather than "at" that line matters: a tank sits at its
# designed founding size (``NUM_SCHOOLING_FISH``) on frame 1, and a feed that opens
# every fresh world with an emergency is a feed nobody trusts. Falling *through*
# the emergency line is what is actually news.
DEFAULT_POPULATION_DANGER = CRITICAL_POPULATION_THRESHOLD - 1

# Comfortably above a founding population, so "recovered" means the tank is
# genuinely running again rather than briefly off the floor.
DEFAULT_POPULATION_RECOVERED = 25


@dataclass(frozen=True)
class StorySample:
    """One read-only observation of the world, taken on a fixed frame cadence.

    ``lineage_members`` maps a founder-lineage id to the ids of the living fish
    descended from it. Shares are derived from it rather than passed alongside,
    so a sample cannot describe a population and a share that disagree.
    """

    frame: int
    simulation_time: float
    population: int
    max_generation: int
    lineage_members: Mapping[str, Sequence[int]] = field(default_factory=dict)

    def shares(self) -> dict[str, float]:
        """Fraction of the living population held by each founder lineage."""
        if self.population <= 0:
            return {}
        return {
            lid: len(members) / self.population for lid, members in self.lineage_members.items()
        }


@dataclass(frozen=True)
class StoryDetectorConfig:
    """Explicit, deterministic thresholds. Every one is reported on the event.

    The population pair is hysteretic on purpose: entering danger and leaving it
    use different numbers, so a population oscillating around one value emits at
    most one event, not one per sample.
    """

    population_danger_at_or_below: int = DEFAULT_POPULATION_DANGER
    population_recovered_at_or_above: int = DEFAULT_POPULATION_RECOVERED
    generation_milestone_interval: int = 5
    lineage_dominant_share: float = 0.5
    lineage_relinquish_share: float = 0.4
    max_entity_ids: int = 8

    def __post_init__(self) -> None:
        if self.population_recovered_at_or_above <= self.population_danger_at_or_below:
            raise ValueError(
                "population_recovered_at_or_above must exceed population_danger_at_or_below "
                "so the danger latch has hysteresis"
            )
        if self.generation_milestone_interval < 1:
            raise ValueError("generation_milestone_interval must be >= 1")
        if not 0.0 < self.lineage_dominant_share <= 1.0:
            raise ValueError("lineage_dominant_share must be in (0, 1]")
        if not 0.0 <= self.lineage_relinquish_share <= self.lineage_dominant_share:
            raise ValueError(
                "lineage_relinquish_share must be in [0, lineage_dominant_share] "
                "so the dominance latch has hysteresis"
            )
        if self.max_entity_ids < 0:
            raise ValueError("max_entity_ids must be >= 0")

    def to_payload(self) -> dict[str, Any]:
        return {
            "population_danger_at_or_below": self.population_danger_at_or_below,
            "population_recovered_at_or_above": self.population_recovered_at_or_above,
            "generation_milestone_interval": self.generation_milestone_interval,
            "lineage_dominant_share": self.lineage_dominant_share,
            "lineage_relinquish_share": self.lineage_relinquish_share,
            "max_entity_ids": self.max_entity_ids,
        }

    @classmethod
    def from_payload(cls, payload: Any) -> StoryDetectorConfig:
        """Rebuild a config from a payload, falling back to defaults on junk."""
        if not isinstance(payload, dict):
            return cls()
        defaults = cls()
        try:
            return cls(
                **{key: payload.get(key, getattr(defaults, key)) for key in defaults.to_payload()}
            )
        except (TypeError, ValueError) as exc:
            logger.warning("StoryDetectorConfig: invalid payload (%s); using defaults.", exc)
            return defaults


class PopulationDangerDetector:
    """Announces the tank entering and leaving population danger.

    Latched with hysteresis: danger is entered at or below one threshold and only
    left at or above a strictly higher one.
    """

    name = "population_danger"

    def __init__(self, config: StoryDetectorConfig) -> None:
        self.config = config
        self.in_danger = False
        self.last_population: int | None = None

    def observe(self, sample: StorySample) -> list[dict[str, Any]]:
        cfg = self.config
        before = {"population": self.last_population} if self.last_population is not None else {}
        events: list[dict[str, Any]] = []

        if not self.in_danger and sample.population <= cfg.population_danger_at_or_below:
            self.in_danger = True
            events.append(
                make_event(
                    event_type="population_danger",
                    frame=sample.frame,
                    simulation_time=sample.simulation_time,
                    severity="concern",
                    title=f"Population fell to {sample.population}",
                    detector_name=self.name,
                    detector_threshold={
                        "population_danger_at_or_below": cfg.population_danger_at_or_below
                    },
                    metrics_before=before,
                    metrics_after={"population": sample.population},
                )
            )
        elif self.in_danger and sample.population >= cfg.population_recovered_at_or_above:
            self.in_danger = False
            events.append(
                make_event(
                    event_type="population_recovered",
                    frame=sample.frame,
                    simulation_time=sample.simulation_time,
                    severity="info",
                    title=f"Population recovered to {sample.population}",
                    detector_name=self.name,
                    detector_threshold={
                        "population_recovered_at_or_above": cfg.population_recovered_at_or_above
                    },
                    metrics_before=before,
                    metrics_after={"population": sample.population},
                )
            )

        self.last_population = sample.population
        return events

    def to_payload(self) -> dict[str, Any]:
        return {"in_danger": self.in_danger, "last_population": self.last_population}

    def load(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        self.in_danger = bool(payload.get("in_danger", False))
        last = payload.get("last_population")
        self.last_population = int(last) if isinstance(last, (int, float)) else None


class GenerationMilestoneDetector:
    """Announces the highest generation crossing a multiple of the interval.

    When several milestones are crossed between two samples only the highest is
    announced — one sample yields at most one event, so a fast-forwarded or
    restored world cannot flood the feed. The skipped span stays legible because
    ``metrics_before`` carries the previously announced milestone.
    """

    name = "generation_milestone"

    def __init__(self, config: StoryDetectorConfig) -> None:
        self.config = config
        self.last_milestone = 0
        self.last_generation: int | None = None

    def observe(self, sample: StorySample) -> list[dict[str, Any]]:
        interval = self.config.generation_milestone_interval
        milestone = (max(0, sample.max_generation) // interval) * interval
        events: list[dict[str, Any]] = []

        if milestone > self.last_milestone:
            before: dict[str, Any] = {"milestone": self.last_milestone}
            if self.last_generation is not None:
                before["max_generation"] = self.last_generation
            events.append(
                make_event(
                    event_type="generation_milestone",
                    frame=sample.frame,
                    simulation_time=sample.simulation_time,
                    severity="insight",
                    title=f"Generation {milestone} reached",
                    detector_name=self.name,
                    detector_threshold={"generation_milestone_interval": interval},
                    metrics_before=before,
                    metrics_after={
                        "milestone": milestone,
                        "max_generation": sample.max_generation,
                    },
                )
            )
            self.last_milestone = milestone

        self.last_generation = sample.max_generation
        return events

    def to_payload(self) -> dict[str, Any]:
        return {"last_milestone": self.last_milestone, "last_generation": self.last_generation}

    def load(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        raw_milestone = payload.get("last_milestone", 0)
        self.last_milestone = int(raw_milestone) if isinstance(raw_milestone, (int, float)) else 0
        last = payload.get("last_generation")
        self.last_generation = int(last) if isinstance(last, (int, float)) else None


class LineageShareDetector:
    """Announces a founder lineage crossing a share of the living population.

    Latched per lineage, with hysteresis: a lineage announces dominance once and
    only becomes announceable again after its share falls back below the
    relinquish threshold. The latch set is bounded by construction — dominance
    requires a majority-sized share, so only a handful of lineages can hold it.
    """

    name = "lineage_share"

    def __init__(self, config: StoryDetectorConfig) -> None:
        self.config = config
        self.dominant: set[str] = set()
        self.last_shares: dict[str, float] = {}

    def observe(self, sample: StorySample) -> list[dict[str, Any]]:
        cfg = self.config
        shares = sample.shares()
        events: list[dict[str, Any]] = []

        # Sorted iteration keeps the emitted order a function of the sample
        # alone, never of dict insertion order.
        for lineage_id in sorted(shares):
            share = shares[lineage_id]
            if share >= cfg.lineage_dominant_share and lineage_id not in self.dominant:
                self.dominant.add(lineage_id)
                members = sorted(int(m) for m in sample.lineage_members.get(lineage_id, ()))
                events.append(
                    make_event(
                        event_type="lineage_dominant",
                        frame=sample.frame,
                        simulation_time=sample.simulation_time,
                        severity="insight",
                        title=(
                            f"Lineage {lineage_id} holds {round(share * 100)}% of the population"
                        ),
                        detector_name=self.name,
                        detector_threshold={"lineage_dominant_share": cfg.lineage_dominant_share},
                        entity_ids=members[: cfg.max_entity_ids],
                        lineage_ids=[lineage_id],
                        metrics_before={
                            "share": round(self.last_shares.get(lineage_id, 0.0), 4),
                        },
                        metrics_after={
                            "share": round(share, 4),
                            "members": len(members),
                            "population": sample.population,
                        },
                    )
                )

        # Un-latch lineages that have fallen back (absent ones count as zero) so
        # a genuine second rise can be announced again.
        for lineage_id in sorted(self.dominant):
            if shares.get(lineage_id, 0.0) < cfg.lineage_relinquish_share:
                self.dominant.discard(lineage_id)

        self.last_shares = shares
        return events

    def to_payload(self) -> dict[str, Any]:
        return {
            "dominant": sorted(self.dominant),
            "last_shares": {k: round(v, 4) for k, v in sorted(self.last_shares.items())},
        }

    def load(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        self.dominant = {str(x) for x in (payload.get("dominant") or [])}
        raw = payload.get("last_shares")
        self.last_shares = (
            {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}
            if isinstance(raw, dict)
            else {}
        )


class StoryDetectorSuite:
    """The ordered set of detectors run against every sample.

    Order is fixed (population, generation, lineage) so identical sample
    sequences produce identical *ordered* events.
    """

    def __init__(self, config: StoryDetectorConfig | None = None) -> None:
        self.config = config or StoryDetectorConfig()
        self.population = PopulationDangerDetector(self.config)
        self.generation = GenerationMilestoneDetector(self.config)
        self.lineage = LineageShareDetector(self.config)

    @property
    def detectors(self) -> tuple[Any, ...]:
        return (self.population, self.generation, self.lineage)

    def observe(self, sample: StorySample) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for detector in self.detectors:
            events.extend(detector.observe(sample))
        return events

    def to_payload(self) -> dict[str, Any]:
        return {
            "config": self.config.to_payload(),
            "population": self.population.to_payload(),
            "generation": self.generation.to_payload(),
            "lineage": self.lineage.to_payload(),
        }

    def load(self, payload: Any) -> None:
        """Restore detector latches so a restored world does not re-announce."""
        if not isinstance(payload, dict):
            return
        self.config = StoryDetectorConfig.from_payload(payload.get("config"))
        for detector in self.detectors:
            detector.config = self.config
        self.population.load(payload.get("population"))
        self.generation.load(payload.get("generation"))
        self.lineage.load(payload.get("lineage"))
