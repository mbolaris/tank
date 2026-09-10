"""Run the foraging arms against a predator, to price cohesion in survival.

`core.foraging.school_arms` found the graph's social-cohesion branch a
monotonic *foraging* cost and said what it could not test: that gym has no
predator. This runs the same four arms over
:mod:`core.foraging.predator_gym`, where grouping can pay for itself through
the tank's own attack cooldown.

The decisive measurement is the urgency sweep read against the school gym's.
There, every step away from cohesion improved the score. If cohesion is
protective under predation, the sweep here must lean the *other* way; if it
leans the same way, cohesion has no constituency in this tank and 12.5 can
stop treating it as a design to preserve.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.foraging.arms import (
    ARM_NAMES,
    GRAPH,
    PRODUCTION_GRAPH,
    build_arm_policy,
    gym_config,
    make_founder_genome,
)
from core.foraging.predator_gym import (
    SCHOOL_SIZE,
    PredatorResult,
    _PredatorPolicy,
    build_predator_schedule,
    run_predator_episode,
)
from core.foraging.predator_references import (
    FeedAndFleePolicy,
    FeedIgnoringPredatorPolicy,
    HidePolicy,
    reference_pressures,
)

if TYPE_CHECKING:
    from core.config.simulation_config import SimulationConfig
    from core.genetics.genome import Genome

HIDE = "hide"
FEED_IGNORING = "feed_ignoring_predator"
FEED_AND_FLEE = "feed_and_flee"

REFERENCE_ARMS = (HIDE, FEED_IGNORING, FEED_AND_FLEE)
PREDATOR_ARM_NAMES = (*REFERENCE_ARMS, *ARM_NAMES)

_GRAPH_ARMS = frozenset({GRAPH, PRODUCTION_GRAPH})

__all__ = [
    "FEED_AND_FLEE",
    "FEED_IGNORING",
    "HIDE",
    "PREDATOR_ARM_NAMES",
    "REFERENCE_ARMS",
    "PredatorArmScore",
    "PredatorComparison",
    "compare_predator_arms",
    "evaluate_predator_arm",
]


@dataclass(frozen=True)
class PredatorArmScore:
    arm: str
    seed: int
    result: PredatorResult

    @property
    def survival_ratio(self) -> float:
        return self.result.survival_ratio

    def to_dict(self) -> dict[str, object]:
        return {"arm": self.arm, "seed": self.seed, **self.result.to_dict()}


def _reference_policies(arm: str) -> list[_PredatorPolicy]:
    if arm == HIDE:
        return [HidePolicy() for _ in range(SCHOOL_SIZE)]
    if arm == FEED_IGNORING:
        return [FeedIgnoringPredatorPolicy() for _ in range(SCHOOL_SIZE)]
    return [FeedAndFleePolicy() for _ in range(SCHOOL_SIZE)]


def evaluate_predator_arm(
    arm: str,
    genome: Genome | None,
    seed: int,
    config: SimulationConfig | None,
    *,
    urgency_threshold: float | None = None,
) -> PredatorArmScore:
    """Run one arm over one predator episode."""
    schedule = build_predator_schedule(seed)

    if arm in REFERENCE_ARMS:
        policies = _reference_policies(arm)
    else:
        if genome is None or config is None:
            raise ValueError(f"arm {arm!r} needs a genome and a config")
        policies = [
            build_arm_policy(
                arm,
                copy.deepcopy(genome),
                seed * 100 + index,
                config,
                urgency_threshold=urgency_threshold,
            )
            for index in range(SCHOOL_SIZE)
        ]

    return PredatorArmScore(
        arm=arm, seed=seed, result=run_predator_episode(schedule, policies, seed)
    )


@dataclass(frozen=True)
class PredatorComparison:
    genome_seeds: tuple[int, ...]
    episode_seeds: tuple[int, ...]
    scores: tuple[PredatorArmScore, ...]

    def arms(self) -> tuple[str, ...]:
        seen: list[str] = []
        for score in self.scores:
            if score.arm not in seen:
                seen.append(score.arm)
        return tuple(seen)

    def _for(self, arm: str) -> list[PredatorArmScore]:
        return [score for score in self.scores if score.arm == arm]

    def _mean(self, arm: str, attribute: str) -> float:
        scores = self._for(arm)
        if not scores:
            return 0.0
        return sum(float(getattr(score.result, attribute)) for score in scores) / len(scores)

    def mean_survival(self, arm: str) -> float:
        return self._mean(arm, "survival_ratio")

    def mean_predation_deaths(self, arm: str) -> float:
        return self._mean(arm, "deaths_predation")

    def mean_starvation_deaths(self, arm: str) -> float:
        return self._mean(arm, "deaths_starvation")

    def mean_neighbour_distance(self, arm: str) -> float:
        return self._mean(arm, "mean_neighbour_distance")

    def to_dict(self) -> dict[str, object]:
        return {
            "genome_seeds": list(self.genome_seeds),
            "episode_seeds": list(self.episode_seeds),
            "survival": {arm: self.mean_survival(arm) for arm in self.arms()},
            "deaths_predation": {arm: self.mean_predation_deaths(arm) for arm in self.arms()},
            "deaths_starvation": {arm: self.mean_starvation_deaths(arm) for arm in self.arms()},
            "mean_neighbour_distance": {
                arm: self.mean_neighbour_distance(arm) for arm in self.arms()
            },
            "scores": [score.to_dict() for score in self.scores],
        }


def compare_predator_arms(
    genome_seeds: tuple[int, ...],
    episode_seeds: tuple[int, ...],
    *,
    arms: tuple[str, ...] = PREDATOR_ARM_NAMES,
    pursuit_module: bool = True,
    urgency_threshold: float | None = None,
) -> PredatorComparison:
    """Score every arm, after confirming the gym's two pressures both bite."""
    for episode_seed in episode_seeds:
        reference_pressures(episode_seed)

    scores: list[PredatorArmScore] = []
    for arm in arms:
        if arm in REFERENCE_ARMS:
            scores.extend(
                evaluate_predator_arm(arm, None, episode_seed, None)
                for episode_seed in episode_seeds
            )
            continue

        config = gym_config(graph=arm in _GRAPH_ARMS, pursuit_module=pursuit_module)
        for genome_seed in genome_seeds:
            genome = make_founder_genome(genome_seed, config)
            scores.extend(
                evaluate_predator_arm(
                    arm, genome, episode_seed, config, urgency_threshold=urgency_threshold
                )
                for episode_seed in episode_seeds
            )
    return PredatorComparison(
        genome_seeds=tuple(genome_seeds),
        episode_seeds=tuple(episode_seeds),
        scores=tuple(scores),
    )
