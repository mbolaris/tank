"""A frozen, single-agent foraging gym with a provable energy ceiling.

The tank benchmarks are deliberately rich ecosystems: reproduction, predators,
side games, and population dynamics all affect their scores.  This module
instead measures the food-pursuit substrate alone.  Its scripted food schedule
has one item per interval and is constructed so a max-speed, full-information
greedy policy can collect every item.  Consequently the sum of scheduled food
energy is an attainable upper bound, not a fitted reference score.

The evaluator uses the production ``ComposableBehavior.execute`` food path
with a minimal world adapter.  It therefore exercises the same target
selection, prediction, genetic foraging traits, and food-approach modes that a
fish uses in the tank, while intentionally excluding reproduction, poker,
predators, and the soccer ball.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, cast

from core.algorithms.composable.behavior import ComposableBehavior
from core.energy.energy_utils import apply_energy_delta
from core.entities import Food
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities import Fish


WORLD_WIDTH = 600.0
WORLD_HEIGHT = 400.0
MAX_SPEED = 2.2
CAPTURE_RADIUS = 12.0
ENERGY_COST_PER_DISTANCE = 0.01
SPAWN_INTERVAL = 160
FOOD_COUNT = 12
SETTLE_FRAMES = 160
RANDOM_WALK_TURN_INTERVAL = 30


@dataclass(frozen=True)
class FoodSpawn:
    """An immutable, scripted food item in a gym episode."""

    frame: int
    x: float
    y: float
    energy: float


@dataclass(frozen=True)
class GymResult:
    """One policy's outcome on a fixed foraging episode."""

    energy_collected: float
    food_collected: int
    energy_spent: float
    travel_distance: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "energy_collected": self.energy_collected,
            "food_collected": self.food_collected,
            "energy_spent": self.energy_spent,
            "travel_distance": self.travel_distance,
        }


@dataclass(frozen=True)
class ForagingGymEvaluation:
    """Comparable floor, substrate, and ceiling outcomes for one seed."""

    oracle_energy: float
    oracle: GymResult
    random_walk: GymResult
    composable: GymResult

    @property
    def composable_ratio(self) -> float:
        return self.composable.energy_collected / self.oracle_energy if self.oracle_energy else 0.0

    @property
    def random_walk_ratio(self) -> float:
        return self.random_walk.energy_collected / self.oracle_energy if self.oracle_energy else 0.0


@dataclass
class _Trait:
    value: float


@dataclass
class _BehavioralTraits:
    aggression: _Trait = field(default_factory=lambda: _Trait(0.5))
    pursuit_aggression: _Trait = field(default_factory=lambda: _Trait(0.5))
    prediction_skill: _Trait = field(default_factory=lambda: _Trait(0.5))
    hunting_stamina: _Trait = field(default_factory=lambda: _Trait(0.5))


@dataclass
class _GymGenome:
    behavioral: _BehavioralTraits = field(default_factory=_BehavioralTraits)


@dataclass
class _GymFood:
    pos: Vector2
    energy: float
    vel: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    food_properties: dict[str, float] = field(default_factory=lambda: {"sink_multiplier": 1.0})

    def get_energy_value(self) -> float:
        """Expose the production food-selection energy contract."""
        return self.energy


class _GymEnvironment:
    """Minimal production-behavior adapter over the episode's active food."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.active_food: list[_GymFood] = []

    def get_detection_modifier(self) -> float:
        return 1.0

    def nearby_resources(self, _fish: object, _radius: int) -> list[_GymFood]:
        return self.active_food

    def nearby_agents_by_type(
        self, _fish: object, _radius: int, agent_type: type[object]
    ) -> list[_GymFood]:
        return self.active_food if agent_type is Food else []


@dataclass
class _GymFish:
    pos: Vector2
    environment: _GymEnvironment
    speed: float = MAX_SPEED
    energy: float = 200.0
    max_energy: float = 1_000.0
    genome: _GymGenome = field(default_factory=_GymGenome)

    def get_energy_ratio(self) -> float:
        return self.energy / self.max_energy

    def is_critical_energy(self) -> bool:
        return False

    def is_low_energy(self) -> bool:
        return False

    def can_eat(self) -> bool:
        return True


class _GymPolicy(Protocol):
    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        """Choose a desired movement vector for one simulation frame."""


def build_food_schedule(seed: int) -> tuple[FoodSpawn, ...]:
    """Build the immutable scripted schedule for ``seed``.

    Food alternates between distant left/right lanes.  The maximum possible
    lane-to-lane distance is below ``MAX_SPEED * SPAWN_INTERVAL``; an oracle
    that knows each exact spawn can therefore collect every item before the
    next one appears.  A fixed integer recurrence, rather than platform RNG,
    supplies the per-seed lane heights and energy values.
    """
    state = seed & 0xFFFFFFFF
    spawns: list[FoodSpawn] = []
    for index in range(FOOD_COUNT):
        state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
        y = 140.0 + float(state % 121)
        state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
        energy = 40.0 + float(state % 61)
        spawns.append(
            FoodSpawn(
                frame=(index + 1) * SPAWN_INTERVAL,
                x=170.0 if index % 2 == 0 else 430.0,
                y=y,
                energy=energy,
            )
        )
    return tuple(spawns)


def oracle_energy_ceiling(schedule: tuple[FoodSpawn, ...]) -> float:
    """Return the attainable gross-energy maximum for this episode."""
    return sum(spawn.energy for spawn in schedule)


class _RandomWalkPolicy:
    """Frozen floor policy: ignores food and changes heading at fixed intervals."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._frames_until_turn = 0
        self._velocity = Vector2(0.0, 0.0)

    def velocity(self, _fish: _GymFish, _active_food: tuple[_GymFood, ...]) -> Vector2:
        if self._frames_until_turn <= 0:
            angle = self._rng.random() * math.tau
            self._velocity = Vector2(math.cos(angle) * MAX_SPEED, math.sin(angle) * MAX_SPEED)
            self._frames_until_turn = RANDOM_WALK_TURN_INTERVAL
        self._frames_until_turn -= 1
        return self._velocity


class _OracleGreedyPolicy:
    """Frozen ceiling policy: direct max-speed pursuit of the best active food."""

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        if not active_food:
            return Vector2(0.0, 0.0)
        target = max(
            active_food,
            key=lambda food: (food.energy / max((food.pos - fish.pos).length(), 1.0), food.energy),
        )
        return _seek(fish.pos, target.pos, MAX_SPEED)


class _ComposablePolicy:
    """The neutral-default production foraging substrate under test."""

    def __init__(self, seed: int) -> None:
        self._behavior = ComposableBehavior()
        self._wander = _RandomWalkPolicy(seed)

    def velocity(self, fish: _GymFish, active_food: tuple[_GymFood, ...]) -> Vector2:
        if not active_food:
            return self._wander.velocity(fish, active_food)
        vx, vy = self._behavior.execute(cast("Fish", fish))
        return Vector2(vx, vy)


def _seek(origin: Vector2, target: Vector2, speed: float) -> Vector2:
    delta = target - origin
    distance = delta.length()
    if distance <= 1e-12:
        return Vector2(0.0, 0.0)
    return Vector2(delta.x * speed / distance, delta.y * speed / distance)


def _clamp_velocity(velocity: Vector2) -> Vector2:
    magnitude = velocity.length()
    if magnitude <= MAX_SPEED:
        return velocity
    return Vector2(velocity.x * MAX_SPEED / magnitude, velocity.y * MAX_SPEED / magnitude)


def _step_position(position: Vector2, velocity: Vector2) -> Vector2:
    return Vector2(
        min(WORLD_WIDTH, max(0.0, position.x + velocity.x)),
        min(WORLD_HEIGHT, max(0.0, position.y + velocity.y)),
    )


def run_episode(schedule: tuple[FoodSpawn, ...], policy: _GymPolicy, seed: int) -> GymResult:
    """Run one deterministic policy episode against a fixed spawn schedule."""
    environment = _GymEnvironment(random.Random(seed))
    fish = _GymFish(pos=Vector2(WORLD_WIDTH / 2.0, WORLD_HEIGHT / 2.0), environment=environment)
    active_food: list[_GymFood] = []
    energy_collected = 0.0
    energy_spent = 0.0
    travel_distance = 0.0
    food_collected = 0
    spawns_by_frame = {spawn.frame: spawn for spawn in schedule}
    final_frame = max(spawns_by_frame, default=0) + SETTLE_FRAMES

    for frame in range(final_frame + 1):
        spawn = spawns_by_frame.get(frame)
        if spawn is not None:
            active_food.append(_GymFood(pos=Vector2(spawn.x, spawn.y), energy=spawn.energy))

        environment.active_food = active_food
        velocity = _clamp_velocity(policy.velocity(fish, tuple(active_food)))
        next_pos = _step_position(fish.pos, velocity)
        distance = (next_pos - fish.pos).length()
        fish.pos = next_pos
        travel_distance += distance
        spent = distance * ENERGY_COST_PER_DISTANCE
        energy_spent += spent
        apply_energy_delta(
            fish,
            -spent,
            source="foraging_gym_movement",
            allow_direct_assignment=True,
        )

        remaining: list[_GymFood] = []
        for food in active_food:
            if (food.pos - fish.pos).length() <= CAPTURE_RADIUS:
                energy_collected += food.energy
                apply_energy_delta(
                    fish,
                    food.energy,
                    source="foraging_gym_food",
                    allow_direct_assignment=True,
                )
                food_collected += 1
            else:
                remaining.append(food)
        active_food = remaining

    return GymResult(
        energy_collected=energy_collected,
        food_collected=food_collected,
        energy_spent=energy_spent,
        travel_distance=travel_distance,
    )


def evaluate_foraging_gym(seed: int) -> ForagingGymEvaluation:
    """Evaluate the frozen floor, production substrate, and ceiling for ``seed``."""
    schedule = build_food_schedule(seed)
    ceiling = oracle_energy_ceiling(schedule)
    oracle = run_episode(schedule, _OracleGreedyPolicy(), seed)
    if not math.isclose(oracle.energy_collected, ceiling, abs_tol=1e-9):
        raise AssertionError("Foraging-gym oracle did not attain its scripted energy ceiling")

    random_floor = run_episode(schedule, _RandomWalkPolicy(seed), seed)
    composable = run_episode(schedule, _ComposablePolicy(seed), seed)
    return ForagingGymEvaluation(
        oracle_energy=ceiling,
        oracle=oracle,
        random_walk=random_floor,
        composable=composable,
    )
