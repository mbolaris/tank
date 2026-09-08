"""The explicit criteria that promote an in-world legend (U8b/E6).

Like the story detectors, these are **pure functions of a sample sequence**:
they read a plain snapshot of the world and return promotions. They never touch
the simulation, consume RNG, or mutate anything, so deciding who is a legend
cannot change who becomes one.

Promotion is deliberately hard. The roadmap's instruction is "do not name every
fish", so every criterion carries an explicit threshold and fires only on the
transition that earns the title; the store deduplicates the rest.

Three of the criteria the spec names are covered:

- **longevity record** - a fish outlives every fish this tank has recorded
- **lineage founding / surviving descendants** - a founder's line reaches a
  share of the living population
- **collapse survival** - a fish is alive on both sides of a population crash

The remaining named criteria (tournament result, migration success,
cross-domain performance) need per-fish measurement the world does not record
yet. They are left out rather than approximated: a legend whose stated reason
is a guess is worse than no legend.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from backend.legends import make_legend
from core.config.ecosystem import CRITICAL_POPULATION_THRESHOLD
from core.config.fish import LIFE_STAGE_MATURE_MAX

logger = logging.getLogger(__name__)

# The population at or below which the tank counts as collapsing. Same reasoning
# as the story detectors: one below the line at which the ecosystem force-spawns,
# so a tank sitting at its designed founding size is not "collapsing".
DEFAULT_COLLAPSE_AT_OR_BELOW = CRITICAL_POPULATION_THRESHOLD - 1
DEFAULT_COLLAPSE_RECOVERED_AT_OR_ABOVE = 25

# A fish becomes an Elder past the last named life stage, so "old" here means
# the simulation's own definition of old rather than a number chosen to feel
# impressive. This matters: an earlier hand-picked 3000 turned out to exceed
# the oldest age any fish reached (~2300 over 12k frames on seed 42), which
# made the longevity criterion unreachable dead code.
DEFAULT_MIN_LONGEVITY_FRAMES = LIFE_STAGE_MATURE_MAX


@dataclass(frozen=True)
class LegendSample:
    """One read-only observation of the world, taken on a fixed frame cadence.

    ``ages`` maps a living fish id to its current age in frames.
    ``lineage_members`` maps a founder lineage id to the living fish descended
    from it - the same grouping the story-event sampler builds.
    """

    frame: int
    simulation_time: float
    population: int
    ages: Mapping[int, int] = field(default_factory=dict)
    lineage_members: Mapping[str, Sequence[int]] = field(default_factory=dict)


@dataclass(frozen=True)
class LegendCriteriaConfig:
    """Explicit thresholds. Every one is reported on the legend's evidence."""

    # A record-holder must also be genuinely old, so the very first fish to be
    # sampled does not take the title simply for existing first. The record
    # itself then ratchets: after the first, only a strictly older fish wins.
    min_longevity_frames: int = DEFAULT_MIN_LONGEVITY_FRAMES
    # A founder's line must hold this share of the living population, over a
    # minimum absolute size so a two-fish tank cannot mint a dynasty.
    lineage_share: float = 0.4
    lineage_min_members: int = 8
    collapse_at_or_below: int = DEFAULT_COLLAPSE_AT_OR_BELOW
    collapse_recovered_at_or_above: int = DEFAULT_COLLAPSE_RECOVERED_AT_OR_ABOVE

    def __post_init__(self) -> None:
        if self.min_longevity_frames < 1:
            raise ValueError("min_longevity_frames must be >= 1")
        if not 0.0 < self.lineage_share <= 1.0:
            raise ValueError("lineage_share must be in (0, 1]")
        if self.lineage_min_members < 1:
            raise ValueError("lineage_min_members must be >= 1")
        if self.collapse_recovered_at_or_above <= self.collapse_at_or_below:
            raise ValueError(
                "collapse_recovered_at_or_above must exceed collapse_at_or_below "
                "so the collapse latch has hysteresis"
            )

    def to_payload(self) -> dict[str, Any]:
        return {
            "min_longevity_frames": self.min_longevity_frames,
            "lineage_share": self.lineage_share,
            "lineage_min_members": self.lineage_min_members,
            "collapse_at_or_below": self.collapse_at_or_below,
            "collapse_recovered_at_or_above": self.collapse_recovered_at_or_above,
        }

    @classmethod
    def from_payload(cls, payload: Any) -> LegendCriteriaConfig:
        if not isinstance(payload, dict):
            return cls()
        defaults = cls()
        try:
            return cls(
                **{key: payload.get(key, getattr(defaults, key)) for key in defaults.to_payload()}
            )
        except (TypeError, ValueError) as exc:
            logger.warning("LegendCriteriaConfig: invalid payload (%s); using defaults.", exc)
            return defaults


class LongevityRecordCriterion:
    """Promotes a fish that outlives every fish this tank has recorded."""

    kind = "longevity_record"

    def __init__(self, config: LegendCriteriaConfig) -> None:
        self.config = config
        self.best_age = 0

    def evaluate(self, sample: LegendSample) -> list[dict[str, Any]]:
        if not sample.ages:
            return []
        # Sorted so a tie between two equally-old fish resolves the same way
        # every run rather than by dict order.
        fish_id, age = max(sorted(sample.ages.items()), key=lambda item: (item[1], -item[0]))
        if age < self.config.min_longevity_frames or age <= self.best_age:
            return []

        previous = self.best_age
        self.best_age = age
        return [
            make_legend(
                kind=self.kind,
                subject_type="fish",
                subject_id=str(fish_id),
                title="Oldest fish this tank has known",
                reason=(
                    f"Reached {age} frames of age, passing the previous record of {previous}."
                    if previous
                    else f"Reached {age} frames of age, the first fish to pass "
                    f"{self.config.min_longevity_frames}."
                ),
                evidence={
                    "age_frames": age,
                    "previous_record_frames": previous,
                    "min_longevity_frames": self.config.min_longevity_frames,
                },
                frame=sample.frame,
                simulation_time=sample.simulation_time,
            )
        ]

    def to_payload(self) -> dict[str, Any]:
        return {"best_age": self.best_age}

    def load(self, payload: Any) -> None:
        if isinstance(payload, dict):
            raw = payload.get("best_age", 0)
            self.best_age = int(raw) if isinstance(raw, (int, float)) else 0


class LineageFounderCriterion:
    """Promotes a founder whose line holds a share of the living population.

    This is the spec's "lineage founding" and "surviving descendants" in one
    rule: founding only matters here because the line survived.
    """

    kind = "lineage_founder"

    def __init__(self, config: LegendCriteriaConfig) -> None:
        self.config = config

    def evaluate(self, sample: LegendSample) -> list[dict[str, Any]]:
        if sample.population <= 0:
            return []
        promotions: list[dict[str, Any]] = []
        # Sorted so emission order is a function of the sample alone.
        for lineage_id in sorted(sample.lineage_members):
            members = sample.lineage_members[lineage_id]
            count = len(members)
            share = count / sample.population
            if count < self.config.lineage_min_members or share < self.config.lineage_share:
                continue
            promotions.append(
                make_legend(
                    kind=self.kind,
                    subject_type="lineage",
                    subject_id=str(lineage_id),
                    title="Founder of a surviving line",
                    reason=(
                        f"{count} of the tank's {sample.population} living fish descend "
                        f"from this founder ({round(share * 100)}%)."
                    ),
                    evidence={
                        "living_descendants": count,
                        "population": sample.population,
                        "share": round(share, 4),
                        "lineage_share": self.config.lineage_share,
                        "lineage_min_members": self.config.lineage_min_members,
                    },
                    frame=sample.frame,
                    simulation_time=sample.simulation_time,
                )
            )
        return promotions


class CollapseSurvivorCriterion:
    """Promotes fish alive on both sides of a population collapse.

    Latched with hysteresis: the tank enters collapse at or below one threshold
    and the survivors are only crowned once it has genuinely recovered past a
    higher one. The roster held between those two points is tiny by definition -
    a collapsing tank has fewer than ten fish in it.
    """

    kind = "collapse_survivor"

    def __init__(self, config: LegendCriteriaConfig) -> None:
        self.config = config
        self.in_collapse = False
        self.collapse_frame = 0
        self.low_population = 0
        self.roster: set[int] = set()

    def evaluate(self, sample: LegendSample) -> list[dict[str, Any]]:
        living = set(sample.ages)

        if sample.population <= self.config.collapse_at_or_below:
            if not self.in_collapse:
                self.in_collapse = True
                self.collapse_frame = sample.frame
                self.low_population = sample.population
                self.roster = set(living)
            else:
                # Track the true nadir, and keep only fish that have been
                # present throughout: leaving and being replaced is not surviving.
                self.low_population = min(self.low_population, sample.population)
                self.roster &= living
            return []

        if not self.in_collapse:
            return []
        if sample.population < self.config.collapse_recovered_at_or_above:
            # Still climbing back; a fish that dies before recovery does not
            # get the title, so keep narrowing the roster.
            self.roster &= living
            return []

        survivors = sorted(self.roster & living)
        collapse_frame = self.collapse_frame
        low = self.low_population
        self.in_collapse = False
        self.roster = set()

        return [
            make_legend(
                kind=self.kind,
                subject_type="fish",
                subject_id=str(fish_id),
                title="Survived the collapse",
                reason=(
                    f"Alive through a crash to {low} fish at frame {collapse_frame}, "
                    f"and still alive at recovery to {sample.population}."
                ),
                evidence={
                    "low_population": low,
                    "collapse_frame": collapse_frame,
                    "recovered_population": sample.population,
                    "survivors": len(survivors),
                },
                frame=sample.frame,
                simulation_time=sample.simulation_time,
            )
            for fish_id in survivors
        ]

    def to_payload(self) -> dict[str, Any]:
        return {
            "in_collapse": self.in_collapse,
            "collapse_frame": self.collapse_frame,
            "low_population": self.low_population,
            "roster": sorted(self.roster),
        }

    def load(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        self.in_collapse = bool(payload.get("in_collapse", False))
        self.collapse_frame = int(payload.get("collapse_frame", 0) or 0)
        self.low_population = int(payload.get("low_population", 0) or 0)
        raw = payload.get("roster")
        self.roster = {int(x) for x in raw} if isinstance(raw, list) else set()


class LegendCriteriaSuite:
    """The ordered set of criteria run against every sample."""

    def __init__(self, config: LegendCriteriaConfig | None = None) -> None:
        self.config = config or LegendCriteriaConfig()
        self.longevity = LongevityRecordCriterion(self.config)
        self.lineage = LineageFounderCriterion(self.config)
        self.collapse = CollapseSurvivorCriterion(self.config)

    @property
    def criteria(self) -> tuple[Any, ...]:
        return (self.longevity, self.lineage, self.collapse)

    def evaluate(self, sample: LegendSample) -> list[dict[str, Any]]:
        promotions: list[dict[str, Any]] = []
        for criterion in self.criteria:
            promotions.extend(criterion.evaluate(sample))
        return promotions

    def to_payload(self) -> dict[str, Any]:
        return {
            "config": self.config.to_payload(),
            "longevity": self.longevity.to_payload(),
            "collapse": self.collapse.to_payload(),
        }

    def load(self, payload: Any) -> None:
        """Restore criterion state so a restored world re-crowns nobody."""
        if not isinstance(payload, dict):
            return
        self.config = LegendCriteriaConfig.from_payload(payload.get("config"))
        for criterion in self.criteria:
            criterion.config = self.config
        self.longevity.load(payload.get("longevity"))
        self.collapse.load(payload.get("collapse"))
