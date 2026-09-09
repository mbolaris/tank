"""Controller ablation arms for the frozen foraging gym.

The gym in :mod:`core.foraging.gym` measures one controller - the neutral
composable behavior - against a provable oracle ceiling. This module makes the
gym answer a comparative question instead: *given the same genome and the same
scripted food, how much energy does each candidate controller collect?*

Four arms share one harness, so a difference between them is a difference in
steering and nothing else. They are meant to be read in two pairs: bare
controller against bare controller, and arbiter against arbiter. Each arm
produces a desired velocity and then hands it to the single production
kinematics implementation
(:func:`core.movement.kinematics.apply_movement_kinematics`), which is what
makes a unit-magnitude behavior graph and a 1.5-magnitude composable behavior
comparable at all: both are scaled by the fish's speed and capped there, so
neither wins or loses on output magnitude.

    ``composable``
        :class:`~core.algorithms.composable.behavior.ComposableBehavior`
        alone - what the tank runs today with ``graph_behavior_enabled`` off.

    ``production`` / ``production_graph``
        The real movement arbiter with ``graph_behavior_enabled`` off and on.
        This pair is the only one that answers "what would flipping the flag
        actually ship", because the arbiter lets the graph steer *and* hands
        control back to the composable behavior whenever the graph classifies
        its own intent as leisure-tier social cohesion. Comparing two arbiter
        runs (rather than an arbiter run against a bare controller) keeps
        every other drive - policy override, ball pursuit, code policy -
        identical on both sides of the comparison.

    ``graph``
        The behavior graph as the sole controller, with no composable
        fallback - the head-to-head 12.4 asks for.

``core/foraging/gym.py`` is a **locked path** (see ``DEFAULT_LOCKED_PATHS`` in
``tools/check_locked_paths.py``): it is the frozen ruler this benchmark's
published scores rest on. So the arms adapt to the gym rather than the other
way round - :func:`_install_arbiter_surface` grows the gym's deliberately
minimal fish and environment into something the production arbiter can read,
at evaluation time, without the ruler changing at all.

**A warning about the ``graph`` arm.** The default foraging graph routes to
social cohesion above its urgency threshold, and the gym is single-fish by
construction, so its cohesion vector is always zero. Above the threshold the
graph therefore emits a zero vector and the fish falls back to the anti-stuck
nudge. A raw ``graph`` score is consequently a statement about the gym's
single-fish geometry, not about the graph's steering. Pass
``urgency_threshold=1.0`` to pin the graph on its food branch and get the
comparison that is actually about foraging.
"""

from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from core.behavior.tank_adapter import build_tank_behavior_observation
from core.foraging.gym import (
    GymResult,
    _GymFish,
    _GymFood,
    _OracleGreedyPolicy,
    _RandomWalkPolicy,
    build_food_schedule,
    oracle_energy_ceiling,
    run_episode,
)
from core.math_utils import Vector2
from core.movement.kinematics import apply_movement_kinematics

if TYPE_CHECKING:
    from core.behavior.graph import BehaviorGraph
    from core.config.simulation_config import SimulationConfig
    from core.entities import Fish
    from core.foraging.gym import _GymPolicy
    from core.genetics.genome import Genome

COMPOSABLE = "composable"
GRAPH = "graph"
PRODUCTION = "production"
PRODUCTION_GRAPH = "production_graph"

# Two comparisons, each between arms that differ in exactly one thing:
# COMPOSABLE vs GRAPH is the bare controller head-to-head; PRODUCTION vs
# PRODUCTION_GRAPH is the flag-flip decision.
ARM_NAMES = (COMPOSABLE, GRAPH, PRODUCTION, PRODUCTION_GRAPH)

# Arms that need the graph feature flag (and therefore a founder graph).
_GRAPH_ARMS = frozenset({GRAPH, PRODUCTION_GRAPH})

__all__ = [
    "ARM_NAMES",
    "ArmScore",
    "COMPOSABLE",
    "GRAPH",
    "PRODUCTION",
    "PRODUCTION_GRAPH",
    "ArmComparison",
    "build_production_policy",
    "compare_arms",
    "evaluate_arm",
    "gym_config",
    "make_founder_genome",
]


@dataclass(frozen=True)
class ArmScore:
    """One arm's outcome on one episode seed."""

    arm: str
    seed: int
    energy_ratio: float
    result: GymResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "arm": self.arm,
            "seed": self.seed,
            "energy_ratio": self.energy_ratio,
            **self.result.to_dict(),
        }


@dataclass(frozen=True)
class ArmComparison:
    """Per-arm scores over a genome cohort crossed with an episode cohort."""

    genome_seeds: tuple[int, ...]
    episode_seeds: tuple[int, ...]
    scores: tuple[ArmScore, ...]

    def mean_ratio(self, arm: str) -> float:
        ratios = [score.energy_ratio for score in self.scores if score.arm == arm]
        return sum(ratios) / len(ratios) if ratios else 0.0

    def arms(self) -> tuple[str, ...]:
        seen: list[str] = []
        for score in self.scores:
            if score.arm not in seen:
                seen.append(score.arm)
        return tuple(seen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "genome_seeds": list(self.genome_seeds),
            "episode_seeds": list(self.episode_seeds),
            "means": {arm: self.mean_ratio(arm) for arm in self.arms()},
            "scores": [score.to_dict() for score in self.scores],
        }


def gym_config(*, graph: bool, pursuit_module: bool) -> SimulationConfig:
    """Build the SimulationConfig an arm reads its feature flags from."""
    from core.config.simulation_config import SimulationConfig

    config = SimulationConfig.headless_fast()
    config.tank.graph_behavior_enabled = graph
    config.tank.target_pursuit_module_enabled = pursuit_module
    return config


def make_founder_genome(seed: int, config: SimulationConfig) -> Genome:
    """Draw a founder genome and install whatever ``config`` opts it into.

    Uses the production installer rather than hand-building traits, so an arm
    always carries exactly the graph and pursuit module a founder fish would
    inherit under the same flags.
    """
    from core.behavior.feature_flags import install_default_behavior_graph_features
    from core.genetics.genome import Genome

    genome: Genome = Genome.random(rng=random.Random(seed))
    install_default_behavior_graph_features(genome, config)
    return genome


def _with_urgency_threshold(graph: BehaviorGraph, threshold: float) -> BehaviorGraph:
    """Return ``graph`` with its ``urgency`` selector threshold replaced.

    Rebuilt through ``to_dict``/``from_dict`` rather than mutated, because the
    caller's graph is shared with the genome it came from.
    """
    from core.behavior.graph import BehaviorGraph as _BehaviorGraph

    payload: dict[str, Any] = dict(graph.to_dict())
    nodes: list[dict[str, Any]] = [dict(node) for node in payload["nodes"]]
    for node in nodes:
        if node["id"] == "urgency":
            node["parameters"] = {**node.get("parameters", {}), "threshold": threshold}
    payload["nodes"] = nodes
    return _BehaviorGraph.from_dict(payload)


def _install_arbiter_surface(fish: Any) -> None:
    """Give the gym's minimal fish and environment the surface a tank fish has.

    The gym models exactly what its own frozen composable ruler reads and no
    more, and it is a locked path, so the extra attributes the production
    movement arbiter and the graph observation builder touch are attached here
    instead. Every value is the gym's own truth rather than a stub of
    convenience: the gym is single-fish, so there is never a school; nothing
    kills the fish; and there is no code pool or poker table to consult.

    Called exactly once per episode, from the owning policy's first frame -
    the attributes then carry real state forward, which is what ``vel`` and
    ``age`` are for.
    """
    fish.vel = Vector2(0.0, 0.0)
    fish.age = 0
    fish.fish_id = 1
    fish.poker_cooldown = 0
    fish.can_play_poker = False
    fish.movement_policy = None
    fish.is_dead = lambda: False
    # Read by build_tank_behavior_observation. Empty means "no memory decision
    # this frame", which is what target_memory_enabled=False produces in
    # production too.
    fish.last_target_memory_decisions = {}
    fish.environment.nearby_evolving_agents = lambda *_args, **_kwargs: []


class _ArmPolicy:
    """Shared plumbing: bind the genome and config, then apply real kinematics."""

    def __init__(self, genome: Genome, seed: int, config: SimulationConfig) -> None:
        self._genome = genome
        self._config = config
        # Every arm falls back to the same frozen wander, and only for the same
        # reason: this genome carries no controller of that arm's kind. Arms
        # deliberately do NOT wander merely because no food is on screen - the
        # gym's own frozen ruler does, but an arm that wandered there would be
        # scoring the wander rather than the controller, and the no-food frames
        # are where two controllers most visibly differ.
        self._wander = _RandomWalkPolicy(seed)
        # One policy drives exactly one episode over exactly one gym fish, so
        # "have I set this fish up yet" is the policy's own state rather than
        # something to probe for on the fish.
        self._installed = False

    def _bind(self, fish: _GymFish) -> Any:
        """Attach this arm's genome and flags, and advance the fish's age.

        Every arm ages the fish, not just the arbiter-driven ones: the
        composable behavior caches its nearest-predator lookup keyed on
        ``fish.age``, so an arm that left age pinned at zero would run a
        different cache schedule and stop being comparable.
        """
        fish_any: Any = fish
        if not self._installed:
            _install_arbiter_surface(fish_any)
            self._installed = True
        fish_any.genome = self._genome
        fish_any.age += 1
        fish_any.environment.simulation_config = self._config
        return fish_any

    def _kinematics(self, fish: Any, desired: tuple[float, float]) -> Vector2:
        apply_movement_kinematics(fish.vel, desired, float(fish.speed), fish.environment.rng)
        return Vector2(float(fish.vel.x), float(fish.vel.y))


class _ComposableArmPolicy(_ArmPolicy):
    """The genome's inherited ComposableBehavior, and nothing else."""

    def __init__(self, genome: Genome, seed: int, config: SimulationConfig) -> None:
        super().__init__(genome, seed, config)
        trait = genome.behavioral.behavior
        self._behavior = trait.value if trait is not None else None

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        fish_any = self._bind(fish)
        if self._behavior is None:
            return self._wander.velocity(fish, active_food)
        return self._kinematics(fish_any, self._behavior.execute(cast("Fish", fish_any)))


class _GraphArmPolicy(_ArmPolicy):
    """The genome's behavior graph as the only controller."""

    def __init__(
        self,
        genome: Genome,
        seed: int,
        config: SimulationConfig,
        urgency_threshold: float | None = None,
    ) -> None:
        super().__init__(genome, seed, config)
        trait = genome.behavioral.behavior_graph
        graph = trait.value if trait is not None else None
        if graph is not None and urgency_threshold is not None:
            graph = _with_urgency_threshold(graph, urgency_threshold)
        self._graph = graph

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        fish_any = self._bind(fish)
        if self._graph is None:
            return self._wander.velocity(fish, active_food)
        observation = build_tank_behavior_observation(cast("Fish", fish_any))
        output = self._graph.compile_cached().evaluate(observation.values)
        if not isinstance(output, tuple) or len(output) != 2:
            return self._wander.velocity(fish, active_food)
        return self._kinematics(fish_any, (float(output[0]), float(output[1])))


class _ProductionArmPolicy(_ArmPolicy):
    """The full production movement arbiter, exactly as the tank runs it."""

    def __init__(
        self,
        genome: Genome,
        seed: int,
        config: SimulationConfig,
        genome_code_pool: object | None = None,
    ) -> None:
        super().__init__(genome, seed, config)
        from core.movement_strategy import AlgorithmicMovement

        self._strategy = AlgorithmicMovement()
        self._genome_code_pool = genome_code_pool

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        fish_any = self._bind(fish)
        fish_any.environment.genome_code_pool = self._genome_code_pool
        arbitration = self._strategy._arbiter.arbitrate(self._strategy, cast("Fish", fish_any))
        selected = arbitration.selected
        desired = selected.velocity if selected is not None else None
        if desired is None:
            return self._wander.velocity(fish, active_food)
        return self._kinematics(fish_any, desired)


def build_production_policy(
    genome: Genome,
    seed: int,
    config: SimulationConfig,
    genome_code_pool: object | None = None,
) -> _GymPolicy:
    """Build the "run the real movement arbiter over a gym episode" policy.

    Exposed so the Skill Observatory scores a genome through the same object
    the ``production`` arms use, instead of keeping a second copy of the
    arbiter-plus-kinematics loop that can drift away from it.
    """
    return _ProductionArmPolicy(genome, seed, config, genome_code_pool)


def evaluate_arm(
    arm: str,
    genome: Genome,
    seed: int,
    config: SimulationConfig,
    *,
    urgency_threshold: float | None = None,
) -> ArmScore:
    """Run one arm on one episode seed and score it against the oracle ceiling."""
    schedule = build_food_schedule(seed)
    ceiling = oracle_energy_ceiling(schedule)
    oracle = run_episode(schedule, _OracleGreedyPolicy(), seed)
    if not math.isclose(oracle.energy_collected, ceiling, abs_tol=1e-9):
        raise AssertionError("Foraging-gym oracle did not attain its scripted energy ceiling")

    # Each episode gets its own genome copy. The composable behavior's
    # sub-behaviors carry live state - circling angle, zigzag phase, patrol
    # heading - so a genome reused across episodes would let one episode's
    # trajectory bias the next, and running the same arm twice would not
    # reproduce.
    episode_genome = copy.deepcopy(genome)

    policy: _GymPolicy
    if arm == COMPOSABLE:
        policy = _ComposableArmPolicy(episode_genome, seed, config)
    elif arm == GRAPH:
        policy = _GraphArmPolicy(episode_genome, seed, config, urgency_threshold)
    elif arm in (PRODUCTION, PRODUCTION_GRAPH):
        policy = _ProductionArmPolicy(episode_genome, seed, config)
    else:
        raise ValueError(f"Unknown foraging-gym arm: {arm!r}")

    result = run_episode(schedule, policy, seed)
    ratio = result.energy_collected / ceiling if ceiling else 0.0
    return ArmScore(arm=arm, seed=seed, energy_ratio=ratio, result=result)


def compare_arms(
    genome_seeds: tuple[int, ...],
    episode_seeds: tuple[int, ...],
    *,
    arms: tuple[str, ...] = ARM_NAMES,
    pursuit_module: bool = True,
    urgency_threshold: float | None = None,
) -> ArmComparison:
    """Score every arm over ``genome_seeds`` x ``episode_seeds``.

    Averaging over a genome cohort matters: the composable behavior's
    foraging skill varies a lot with the traits a founder happens to draw,
    while the default behavior graph is the same fixed topology for every
    founder. A single genome would therefore measure that draw, not the
    controllers.
    """
    scores: list[ArmScore] = []
    for arm in arms:
        wants_graph = arm in _GRAPH_ARMS
        config = gym_config(graph=wants_graph, pursuit_module=pursuit_module)
        for genome_seed in genome_seeds:
            genome = make_founder_genome(genome_seed, config)
            for episode_seed in episode_seeds:
                scores.append(
                    evaluate_arm(
                        arm,
                        genome,
                        episode_seed,
                        config,
                        urgency_threshold=urgency_threshold,
                    )
                )
    return ArmComparison(
        genome_seeds=tuple(genome_seeds),
        episode_seeds=tuple(episode_seeds),
        scores=tuple(scores),
    )
