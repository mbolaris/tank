"""Movement policies used to evaluate a genome in one foraging-gym episode."""

from __future__ import annotations

from typing import Any, cast

from core.entities.fish import Fish

# The "full production" subject is core.foraging.arms' production arm: one
# implementation of "run the real movement arbiter over a gym episode", rather
# than a copy that can drift from it. The copy this replaced had already
# drifted, using math.tau where the live simulation uses a slightly different
# turn constant for its anti-stuck nudge.
from core.foraging.arms import build_production_policy
from core.foraging.gym import (
    ForagingGymEvaluation,
    _GymFish,
    _GymFood,
    _OracleGreedyPolicy,
    _RandomWalkPolicy,
    build_food_schedule,
    oracle_energy_ceiling,
    run_episode,
)
from core.math_utils import Vector2


class _LegacyComposablePolicy:
    """Evaluate only the fish's inherited legacy ComposableBehavior."""

    def __init__(self, genome: Any, seed: int) -> None:
        self._wander = _RandomWalkPolicy(seed)
        self._genome = genome
        behavior_trait = getattr(genome.behavioral, "behavior", None)
        self._behavior = behavior_trait.value if behavior_trait is not None else None

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        if self._behavior is None or not active_food:
            return self._wander.velocity(fish, active_food)
        fish_any: Any = fish
        fish_any.genome = self._genome
        vx, vy = self._behavior.execute(cast(Fish, fish_any))
        return Vector2(vx, vy)


class _SharedPursuitModulePolicy:
    """Evaluate the fish's inherited target_pursuit_module BehaviorGraph."""

    def __init__(self, genome: Any, seed: int) -> None:
        self._wander = _RandomWalkPolicy(seed)
        self._genome = genome
        module_trait = getattr(genome.behavioral, "target_pursuit_module", None)
        self._module = module_trait.value if module_trait is not None else None

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        if self._module is None or not active_food:
            return self._wander.velocity(fish, active_food)

        from core.algorithms.composable.food_selection import select_food_target
        from core.behavior.targeting import TargetObservation

        fish_any: Any = fish
        fish_any.genome = self._genome
        env_any: Any = fish.environment
        if not hasattr(env_any, "get_detection_modifier"):
            env_any.get_detection_modifier = lambda: 1.0
        food = select_food_target(cast(Fish, fish_any))
        if food is None:
            return self._wander.velocity(fish, active_food)

        offset = food.pos - fish.pos
        target_obs = TargetObservation(
            target_vector=(float(offset.x), float(offset.y)),
            target_velocity=(0.0, 0.0),
            target_exists=True,
            threat_vector=(0.0, 0.0),
            self_velocity=(float(fish_any.vel.x), float(fish_any.vel.y)),
            self_speed=float(fish_any.speed),
            energy_ratio=float(fish_any.get_energy_ratio()),
        )
        output = self._module.compile_cached().evaluate(target_obs.to_values())
        if isinstance(output, tuple) and len(output) == 2:
            return Vector2(float(output[0]), float(output[1]))
        return self._wander.velocity(fish, active_food)


def evaluate_custom_genome(
    genome: Any,
    seed: int,
    subject: str = "full_production",
    simulation_config: Any = None,
    genome_code_pool: Any = None,
) -> ForagingGymEvaluation:
    """Evaluate a controller snapshot in one deterministic foraging episode."""
    schedule = build_food_schedule(seed)
    ceiling = oracle_energy_ceiling(schedule)
    oracle = run_episode(schedule, _OracleGreedyPolicy(), seed)
    random_floor = run_episode(schedule, _RandomWalkPolicy(seed), seed)
    if subject == "legacy_composable":
        policy: Any = _LegacyComposablePolicy(genome, seed)
    elif subject == "shared_pursuit_module":
        policy = _SharedPursuitModulePolicy(genome, seed)
    else:
        policy = build_production_policy(genome, seed, simulation_config, genome_code_pool)
    composable = run_episode(schedule, policy, seed)
    return ForagingGymEvaluation(
        oracle_energy=ceiling,
        oracle=oracle,
        random_walk=random_floor,
        composable=composable,
    )
