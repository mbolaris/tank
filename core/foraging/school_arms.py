"""Run the foraging arms against a school instead of a lone fish.

Backlog 12.4 compared `ComposableBehavior` with the behavior graph on the
single-fish gym and could not evaluate half of the graph: above its urgency
threshold the graph steers toward social cohesion, and a gym with one fish has
no school, so that branch emitted a zero vector. The entry's open question was
whether that branch is a good idea at all.

This module answers it by running the *same four arms* - so the numbers stay
comparable with 12.4's - over :mod:`core.foraging.school_gym`, where cohesion
has both a meaning and a price.
"""

from __future__ import annotations

import copy
import math
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
from core.foraging.school_gym import (
    SCHOOL_SIZE,
    AssignedOraclePolicy,
    GreedyShoalPolicy,
    RandomWalkPolicy,
    SchoolResult,
    _SchoolPolicy,
    build_wave_schedule,
    oracle_energy_ceiling,
    run_school_episode,
)

if TYPE_CHECKING:
    from core.config.simulation_config import SimulationConfig
    from core.genetics.genome import Genome

ORACLE = "oracle"
GREEDY_SHOAL = "greedy_shoal"
RANDOM_WALK = "random_walk"

# The frozen references. They bracket every evolvable arm: nobody should score
# above the oracle, and an arm below the greedy shoal is not foraging.
REFERENCE_ARMS = (ORACLE, GREEDY_SHOAL, RANDOM_WALK)
SCHOOL_ARM_NAMES = (*REFERENCE_ARMS, *ARM_NAMES)

_GRAPH_ARMS = frozenset({GRAPH, PRODUCTION_GRAPH})

__all__ = [
    "GREEDY_SHOAL",
    "ORACLE",
    "RANDOM_WALK",
    "REFERENCE_ARMS",
    "SCHOOL_ARM_NAMES",
    "SchoolArmScore",
    "compare_school_arms",
    "evaluate_school_arm",
]


@dataclass(frozen=True)
class SchoolArmScore:
    """One arm's outcome on one episode seed."""

    arm: str
    seed: int
    energy_ratio: float
    result: SchoolResult

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "seed": self.seed,
            "energy_ratio": self.energy_ratio,
            **self.result.to_dict(),
        }


def _reference_policies(arm: str, seed: int) -> list[_SchoolPolicy]:
    if arm == ORACLE:
        return [AssignedOraclePolicy() for _ in range(SCHOOL_SIZE)]
    if arm == GREEDY_SHOAL:
        return [GreedyShoalPolicy() for _ in range(SCHOOL_SIZE)]
    # Each fish gets its own wander seed, or the whole school would turn in
    # unison and the floor would measure a rigid formation instead of noise.
    return [RandomWalkPolicy(seed * 1000 + index) for index in range(SCHOOL_SIZE)]


def evaluate_school_arm(
    arm: str,
    genome: Genome | None,
    seed: int,
    config: SimulationConfig | None,
    *,
    urgency_threshold: float | None = None,
) -> SchoolArmScore:
    """Run one arm over one school episode and score it against the ceiling."""
    schedule = build_wave_schedule(seed)
    ceiling = oracle_energy_ceiling(schedule)

    if arm in REFERENCE_ARMS:
        policies = _reference_policies(arm, seed)
    else:
        if genome is None or config is None:
            raise ValueError(f"arm {arm!r} needs a genome and a config")
        # One controller per fish, each over its own genome copy: the
        # composable behavior's sub-behaviors carry live state, and a shared
        # instance would couple the school's members through it.
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

    result = run_school_episode(schedule, policies, seed)
    if arm == ORACLE and not math.isclose(result.energy_collected, ceiling, abs_tol=1e-9):
        raise AssertionError("School-gym oracle did not attain its scripted energy ceiling")

    ratio = result.energy_collected / ceiling if ceiling else 0.0
    return SchoolArmScore(arm=arm, seed=seed, energy_ratio=ratio, result=result)


@dataclass(frozen=True)
class SchoolComparison:
    """Per-arm scores over a genome cohort crossed with an episode cohort."""

    genome_seeds: tuple[int, ...]
    episode_seeds: tuple[int, ...]
    scores: tuple[SchoolArmScore, ...]

    def arms(self) -> tuple[str, ...]:
        seen: list[str] = []
        for score in self.scores:
            if score.arm not in seen:
                seen.append(score.arm)
        return tuple(seen)

    def _for(self, arm: str) -> list[SchoolArmScore]:
        return [score for score in self.scores if score.arm == arm]

    def mean_ratio(self, arm: str) -> float:
        scores = self._for(arm)
        return sum(score.energy_ratio for score in scores) / len(scores) if scores else 0.0

    def mean_neighbour_distance(self, arm: str) -> float:
        scores = self._for(arm)
        if not scores:
            return 0.0
        return sum(score.result.mean_neighbour_distance for score in scores) / len(scores)

    def mean_stations_visited(self, arm: str) -> float:
        scores = self._for(arm)
        if not scores:
            return 0.0
        return sum(score.result.mean_stations_visited for score in scores) / len(scores)

    def to_dict(self) -> dict[str, object]:
        return {
            "genome_seeds": list(self.genome_seeds),
            "episode_seeds": list(self.episode_seeds),
            "means": {arm: self.mean_ratio(arm) for arm in self.arms()},
            "mean_neighbour_distance": {
                arm: self.mean_neighbour_distance(arm) for arm in self.arms()
            },
            "mean_stations_visited": {arm: self.mean_stations_visited(arm) for arm in self.arms()},
            "scores": [score.to_dict() for score in self.scores],
        }


def compare_school_arms(
    genome_seeds: tuple[int, ...],
    episode_seeds: tuple[int, ...],
    *,
    arms: tuple[str, ...] = SCHOOL_ARM_NAMES,
    pursuit_module: bool = True,
    urgency_threshold: float | None = None,
) -> SchoolComparison:
    """Score every arm over ``genome_seeds`` x ``episode_seeds``.

    Reference arms carry no genome, so they run once per episode seed rather
    than once per genome; repeating them per genome would only pad the average
    with identical numbers.
    """
    scores: list[SchoolArmScore] = []
    for arm in arms:
        if arm in REFERENCE_ARMS:
            scores.extend(
                evaluate_school_arm(arm, None, episode_seed, None) for episode_seed in episode_seeds
            )
            continue

        config = gym_config(graph=arm in _GRAPH_ARMS, pursuit_module=pursuit_module)
        for genome_seed in genome_seeds:
            genome = make_founder_genome(genome_seed, config)
            scores.extend(
                evaluate_school_arm(
                    arm,
                    genome,
                    episode_seed,
                    config,
                    urgency_threshold=urgency_threshold,
                )
                for episode_seed in episode_seeds
            )
    return SchoolComparison(
        genome_seeds=tuple(genome_seeds),
        episode_seeds=tuple(episode_seeds),
        scores=tuple(scores),
    )
