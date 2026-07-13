"""Production-controller evaluation primitives for the Skill Observatory."""

from __future__ import annotations

import math
from typing import Any, cast

from core.entities.fish import Fish
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
from core.movement_strategy import AlgorithmicMovement


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


class _FullProductionPolicy:
    """Evaluate the full production movement controller with arbiter considerations."""

    def __init__(
        self, genome: Any, seed: int, simulation_config: Any, genome_code_pool: Any
    ) -> None:
        self._strategy = AlgorithmicMovement()
        self._wander = _RandomWalkPolicy(seed)
        self._genome = genome
        self._simulation_config = simulation_config
        self._genome_code_pool = genome_code_pool

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        fish_any: Any = fish
        if not hasattr(fish_any, "vel"):
            fish_any.vel = Vector2(0.0, 0.0)
        if not hasattr(fish_any, "age"):
            fish_any.age = 0
        if not hasattr(fish_any, "fish_id"):
            fish_any.fish_id = 1
        if not hasattr(fish_any, "poker_cooldown"):
            fish_any.poker_cooldown = 0
        if not hasattr(fish_any, "can_play_poker"):
            fish_any.can_play_poker = False
        if not hasattr(fish_any, "is_dead"):
            fish_any.is_dead = lambda: False
        if not hasattr(fish_any, "movement_policy"):
            fish_any.movement_policy = None

        env_any: Any = fish.environment
        if not hasattr(env_any, "simulation_config"):
            env_any.simulation_config = self._simulation_config
        if not hasattr(env_any, "genome_code_pool"):
            env_any.genome_code_pool = self._genome_code_pool
        if not hasattr(env_any, "nearby_evolving_agents"):
            env_any.nearby_evolving_agents = lambda *args, **kwargs: []
        if not hasattr(env_any, "get_detection_modifier"):
            env_any.get_detection_modifier = lambda: 1.0

        fish_any.age += 1
        fish_any.genome = self._genome
        from core.movement_strategy import (
            ALGORITHMIC_MAX_SPEED_MULTIPLIER,
            ALGORITHMIC_MOVEMENT_SMOOTHING,
        )

        arbitration = self._strategy._arbiter.arbitrate(self._strategy, cast(Fish, fish_any))
        selected = arbitration.selected
        desired = selected.velocity if selected is not None else None
        if desired is None:
            return self._wander.velocity(fish, active_food)

        desired_vx = max(-5.0, min(5.0, float(desired[0])))
        desired_vy = max(-5.0, min(5.0, float(desired[1])))
        speed = fish_any.speed
        target_vx = desired_vx * speed
        target_vy = desired_vy * speed
        vel = fish_any.vel
        vel.x += (target_vx - vel.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
        vel.y += (target_vy - vel.y) * ALGORITHMIC_MOVEMENT_SMOOTHING
        vel_x, vel_y = vel.x, vel.y
        vel_length_sq = vel_x * vel_x + vel_y * vel_y
        if vel_length_sq < 0.01:
            angle = env_any.rng.random() * math.tau
            nudge_speed = speed * 0.3
            vel.x = nudge_speed * math.cos(angle)
            vel.y = nudge_speed * math.sin(angle)
            vel_length_sq = vel.x * vel.x + vel.y * vel.y
        if vel_length_sq > 0:
            max_speed_sq = speed * speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER**2
            if vel_length_sq > max_speed_sq:
                scale = speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER / math.sqrt(vel_length_sq)
                vel.x = vel_x * scale
                vel.y = vel_y * scale
        return Vector2(float(vel.x), float(vel.y))


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
        policy = _FullProductionPolicy(genome, seed, simulation_config, genome_code_pool)
    composable = run_episode(schedule, policy, seed)
    return ForagingGymEvaluation(
        oracle_energy=ceiling,
        oracle=oracle,
        random_walk=random_floor,
        composable=composable,
    )
