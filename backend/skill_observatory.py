"""Production-controller evaluation primitives for the Skill Observatory."""

from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict
from dataclasses import dataclass
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


@dataclass(frozen=True)
class FishSkillSnapshot:
    """Point-in-time, worker-thread-safe copy of one living fish.

    A living ``Fish``'s ``taxon_id``/``common_name`` can be reassigned by
    ``TaxonomySystem.update()`` on any simulation tick (species promotion
    swaps the record's id), so holding a live ``Fish`` reference across a
    multi-seed background evaluation can silently mix data from two points
    in time. This snapshot is built once, synchronously, before the worker
    thread starts.
    """

    fish_id: int
    taxon_id: str
    common_name: str
    generation: int
    parent_id: int | None
    genome: Any
    parent_pursuit_params: dict[str, float] | None


@dataclass(frozen=True)
class SpeciesSkillSnapshot:
    """Point-in-time copy of one species record's observatory-relevant state."""

    taxon_id: str
    common_name: str
    legacy_prediction_skill: float | None


@dataclass(frozen=True)
class WorldSkillSnapshot:
    """Immutable copy of everything an observatory evaluation needs.

    Built synchronously on the caller's thread from live simulation state,
    then handed to a worker thread (via ``asyncio.to_thread``) that must not
    touch the live world - the simulation keeps mutating fish, species
    records, and the genome code pool concurrently with the worker.
    """

    world_id: str
    frame: int
    living_fish: tuple[FishSkillSnapshot, ...]
    species_by_taxon_id: dict[str, SpeciesSkillSnapshot]
    simulation_config: Any
    genome_code_pool: Any


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


_MAX_OBSERVATORY_CACHE_ENTRIES = 256
_OBSERVATORY_EVALUATION_CACHE: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()


def controller_fingerprint(genome: Any) -> str:
    """Stable identity hash for a genome's movement-controller-relevant genes.

    Two genomes that differ only in unrelated physical traits must fingerprint
    identically, so the Observatory doesn't create a separate cache entry (and
    a separate multi-seed evaluation) for phenotypically identical controllers.
    """
    from unittest.mock import Mock

    from core.genetics.genome import GENOME_SCHEMA_VERSION
    from core.genetics.genome_codec import genome_to_dict

    if isinstance(genome, Mock):
        return "mock_controller"
    payload = genome_to_dict(genome, schema_version=GENOME_SCHEMA_VERSION)
    controller_fields = (
        "aggression",
        "pursuit_aggression",
        "prediction_skill",
        "hunting_stamina",
        "behavior",
        "behavior_graph",
        "target_pursuit_module",
        "movement_policy_id",
        "movement_policy_params",
    )
    controller_payload = {key: payload.get(key) for key in controller_fields}
    encoded = json.dumps(controller_payload, sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def module_fingerprint(genome: Any) -> str:
    """Stable identity hash for a genome's target-pursuit behavior module."""
    from unittest.mock import Mock

    if isinstance(genome, Mock):
        return "mock_module"

    module_trait = getattr(genome.behavioral, "target_pursuit_module", None)
    module = module_trait.value if module_trait is not None else None
    if module is not None:
        payload = module.to_dict()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
        return "graph_" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:8]

    behavior_trait = getattr(genome.behavioral, "behavior", None)
    behavior = behavior_trait.value if behavior_trait is not None else None
    if behavior is not None:
        payload = {
            "threat_response": behavior.threat_response.name,
            "food_approach": behavior.food_approach.name,
            "social_mode": behavior.social_mode.name,
            "poker_engagement": behavior.poker_engagement.name,
            "parameters": behavior.parameters,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
        return "comp_" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:8]

    return "default"


def legacy_prediction_skill_of(genome: Any) -> float | None:
    """Best-effort float extraction of a genome's legacy prediction_skill trait."""
    from unittest.mock import Mock

    behavioral = getattr(genome, "behavioral", None)
    trait = getattr(behavioral, "prediction_skill", None) if behavioral is not None else None
    if trait is None:
        return None
    val = getattr(trait, "value", None)
    if val is None or isinstance(val, Mock):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def evaluate_genome_with_cache(
    genome: Any,
    config_hash: str,
    seeds: tuple[int, ...],
    simulation_config: Any,
    genome_code_pool: Any,
) -> dict[str, Any]:
    """Score one genome across ``seeds``, cached by (controller fingerprint, config_hash)."""
    cache_key = (controller_fingerprint(genome), config_hash)
    if cache_key in _OBSERVATORY_EVALUATION_CACHE:
        _OBSERVATORY_EVALUATION_CACHE.move_to_end(cache_key)
        return _OBSERVATORY_EVALUATION_CACHE[cache_key]

    scores = []
    food_collected_list = []
    for seed in seeds:
        res = evaluate_custom_genome(
            genome,
            seed,
            subject="full_production",
            simulation_config=simulation_config,
            genome_code_pool=genome_code_pool,
        )
        scores.append(res.composable_ratio)
        food_collected_list.append(res.composable.food_collected)

    n_trials = len(scores)
    mean_score = sum(scores) / n_trials
    if n_trials > 1:
        variance = sum((x - mean_score) ** 2 for x in scores) / (n_trials - 1)
        sem = math.sqrt(variance) / math.sqrt(n_trials)
    else:
        sem = 0.0

    result = {
        "score": mean_score,
        "average_food": sum(food_collected_list) / len(food_collected_list),
        "uncertainty": sem,
        "sample_size": n_trials,
    }
    _OBSERVATORY_EVALUATION_CACHE[cache_key] = result
    _OBSERVATORY_EVALUATION_CACHE.move_to_end(cache_key)
    while len(_OBSERVATORY_EVALUATION_CACHE) > _MAX_OBSERVATORY_CACHE_ENTRIES:
        _OBSERVATORY_EVALUATION_CACHE.popitem(last=False)
    return result
