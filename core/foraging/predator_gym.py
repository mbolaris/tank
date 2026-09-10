"""A foraging gym with a predator, to price social cohesion in survival.

`core.foraging.school_gym` established that cohesion is a *foraging* cost, and
said plainly what it could not establish: that gym has no predator, which is
what schooling is actually for. This is the other half. Together the two
bracket the question 12.4 left open.

**Why the answer is not rigged by construction.** How a predator is modelled
decides whether grouping helps, so this one is not invented: it reproduces the
tank's own mechanic. In production a crab patrols the bottom lane
(`Crab._update_tank_patrol`), kills a fish on contact, and then cannot kill
again until `CRAB_ATTACK_COOLDOWN` frames have passed
(`CollisionSystem._handle_fish_crab_collision`). That cooldown *is* dilution:
a tight school crossing a crab loses roughly one member, while a strung-out
line meets a recovered crab again and again. The constants are imported from
`core.config.entities` rather than restated, so the gym cannot quietly drift
away from the tank it is meant to describe.

**The trade-off is the point.** Food spawns low, inside the patrol lane, and
fish burn energy every frame. A school that never descends starves; one that
feeds without regard for the crab is eaten. Neither pressure is optional, and
`reference_pressures()` asserts both actually bite before any arm is scored -
an instrument where one pressure is inert would produce a confident number
about nothing.

**There is deliberately no oracle ceiling here.** The food gyms can prove
theirs by construction; survival under a joint forage-and-evade problem has no
attainable maximum this module can honestly derive, so it reports a survival
ratio bounded by its own definition and three reference arms that bracket it.
Inventing a ceiling would be the fitted-reference-score mistake those gyms
exist to avoid.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Protocol

from core.config.entities import CRAB_ATTACK_COOLDOWN
from core.energy.energy_utils import apply_energy_delta
from core.entities import Food
from core.entities.predators import Crab
from core.math_utils import Vector2

WORLD_WIDTH = 600.0
WORLD_HEIGHT = 400.0
MAX_SPEED = 2.2
CAPTURE_RADIUS = 12.0
ENERGY_COST_PER_DISTANCE = 0.01

# Metabolism, which is what makes hiding a losing strategy rather than a safe
# one. Tuned so a fish that never eats dies partway through the episode.
IDLE_ENERGY_DRAIN = 0.05
START_ENERGY = 120.0

SCHOOL_SIZE = 4
EPISODE_FRAMES = 2400
WAVE_INTERVAL = 240
FOOD_LIFETIME = 220

# The crab's lane, and the fish's starting cluster, at opposite ends: food is
# only reachable by descending into the hazard.
CRAB_LANE_Y = 340.0
CRAB_SPEED = 1.5
CRAB_CONTACT_RADIUS = 18.0
START_Y = 70.0
START_SPREAD = 14.0

# Food spawns low, spread horizontally across the lane.
FOOD_Y_MIN = 300.0
FOOD_Y_SPAN = 60.0
FOOD_PER_WAVE = 4

THREAT_RADIUS = 200.0

__all__ = [
    "CRAB_LANE_Y",
    "EPISODE_FRAMES",
    "MAX_SPEED",
    "SCHOOL_SIZE",
    "START_Y",
    "PredatorResult",
    "build_predator_schedule",
    "run_predator_episode",
]


@dataclass(frozen=True)
class PredatorSpawn:
    frame: int
    x: float
    y: float
    energy: float

    @property
    def expires_at(self) -> int:
        return self.frame + FOOD_LIFETIME


@dataclass(frozen=True)
class PredatorResult:
    """Survival first, with the cause of death and the school's shape beside it.

    A survival number on its own cannot distinguish "evaded well" from "never
    went near the food and got lucky on the clock", so deaths are split by
    cause and the spacing travels with them.
    """

    survival_ratio: float
    alive_at_end: int
    deaths_predation: int
    deaths_starvation: int
    energy_collected: float
    food_collected: int
    mean_neighbour_distance: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "survival_ratio": self.survival_ratio,
            "alive_at_end": self.alive_at_end,
            "deaths_predation": self.deaths_predation,
            "deaths_starvation": self.deaths_starvation,
            "energy_collected": self.energy_collected,
            "food_collected": self.food_collected,
            "mean_neighbour_distance": self.mean_neighbour_distance,
        }


class _PredatorPolicy(Protocol):
    """One fish's controller for one frame.

    ``Any``, not a concrete type: a Protocol's parameters are contravariant,
    and the arms in :mod:`core.foraging.arms` declare theirs as the
    single-fish gym's types. A stricter signature would reject exactly the
    controllers this gym exists to run.
    """

    def velocity(self, fish: Any, active_food: Any) -> Vector2:
        """Choose a desired movement vector for one fish for one frame."""


@dataclass
class _Trait:
    value: float


@dataclass
class _PredatorTraits:
    aggression: _Trait = field(default_factory=lambda: _Trait(0.5))
    pursuit_aggression: _Trait = field(default_factory=lambda: _Trait(0.5))
    prediction_skill: _Trait = field(default_factory=lambda: _Trait(0.5))
    hunting_stamina: _Trait = field(default_factory=lambda: _Trait(0.5))
    behavior_graph: object | None = None
    target_pursuit_module: object | None = None


@dataclass
class _PredatorGenome:
    behavioral: _PredatorTraits = field(default_factory=_PredatorTraits)


@dataclass
class _PredatorFood:
    pos: Vector2
    energy: float
    expires_at: int
    vel: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    food_properties: dict[str, float] = field(default_factory=lambda: {"sink_multiplier": 1.0})

    def get_energy_value(self) -> float:
        return self.energy


class _GymCrab(Crab):
    """The tank's patrol-and-cooldown predator, in the gym's minimal world.

    Subclasses the production :class:`~core.entities.predators.Crab` without
    calling its ``__init__``, which needs a full World. That is deliberate and
    load-bearing rather than a shortcut: the behavior adapters find threats
    with ``isinstance(entity, Crab)``
    (``core.behavior.tank_adapter._nearest_threat``), so only a real subclass
    is visible to them. This gym is the first place the graph's threat branch
    reads a nonzero threat vector at all.

    The patrol-and-cooldown *mechanic* is reproduced rather than inherited,
    because the production update path needs world bounds, an RNG and display
    config. The constants are imported, so a change to the tank's cooldown
    reaches this gym instead of silently diverging from it.
    """

    def __init__(self, x: float) -> None:
        self.pos = Vector2(x, CRAB_LANE_Y)
        self.vel = Vector2(CRAB_SPEED, 0.0)
        self.hunt_cooldown = 0
        self.is_predator = True

    def step(self) -> None:
        if self.hunt_cooldown > 0:
            self.hunt_cooldown -= 1
        self.pos.x += self.vel.x
        if self.pos.x <= 0.0 or self.pos.x >= WORLD_WIDTH:
            self.pos.x = min(WORLD_WIDTH, max(0.0, self.pos.x))
            self.vel.x = -self.vel.x

    def can_hunt(self) -> bool:
        return self.hunt_cooldown <= 0

    def eat(self) -> None:
        self.hunt_cooldown = CRAB_ATTACK_COOLDOWN


class _PredatorEnvironment:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.active_food: list[_PredatorFood] = []
        self.fish: list[_PredatorFish] = []
        self.crabs: list[_GymCrab] = []
        self.simulation_config: object | None = None
        self.genome_code_pool: object | None = None

    def get_detection_modifier(self) -> float:
        return 1.0

    def nearby_resources(self, _fish: object, _radius: int) -> list[_PredatorFood]:
        return self.active_food

    def nearby_agents_by_type(
        self, fish: object, radius: int, agent_type: type[object]
    ) -> list[Any]:
        if agent_type is Food:
            return list(self.active_food)
        if agent_type is Crab:
            origin = getattr(fish, "pos", None)
            if origin is None:
                return []
            return [crab for crab in self.crabs if (crab.pos - origin).length() <= float(radius)]
        return []

    def nearby_evolving_agents(self, fish: object, radius: float) -> list[_PredatorFish]:
        origin = getattr(fish, "pos", None)
        if origin is None:
            return []
        return [
            other
            for other in self.fish
            if other is not fish and not other.dead and (other.pos - origin).length() <= radius
        ]


@dataclass
class _PredatorFish:
    pos: Vector2
    environment: _PredatorEnvironment
    fish_id: int
    speed: float = MAX_SPEED
    energy: float = START_ENERGY
    max_energy: float = 1_000.0
    genome: _PredatorGenome = field(default_factory=_PredatorGenome)
    vel: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    age: int = 0
    dead: bool = False
    poker_cooldown: int = 0
    can_play_poker: bool = False
    movement_policy: object | None = None
    last_target_memory_decisions: dict[str, object] = field(default_factory=dict)

    def is_dead(self) -> bool:
        return self.dead

    def get_energy_ratio(self) -> float:
        return self.energy / self.max_energy

    def is_critical_energy(self) -> bool:
        return self.energy < START_ENERGY * 0.2

    def is_low_energy(self) -> bool:
        return self.energy < START_ENERGY * 0.5

    def can_eat(self) -> bool:
        return True


def build_predator_schedule(seed: int) -> tuple[PredatorSpawn, ...]:
    """Scripted food, low in the world so feeding means entering the lane."""
    state = seed & 0xFFFFFFFF
    spawns: list[PredatorSpawn] = []
    waves = EPISODE_FRAMES // WAVE_INTERVAL
    for wave in range(waves):
        frame = (wave + 1) * WAVE_INTERVAL
        for slot in range(FOOD_PER_WAVE):
            state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
            lane_width = WORLD_WIDTH / FOOD_PER_WAVE
            x = lane_width * slot + float(state % int(lane_width))
            state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
            y = FOOD_Y_MIN + float(state % int(FOOD_Y_SPAN))
            state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
            energy = 40.0 + float(state % 61)
            spawns.append(PredatorSpawn(frame=frame, x=x, y=y, energy=energy))
    return tuple(spawns)


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


def _starting_positions() -> list[Vector2]:
    centre_x = WORLD_WIDTH / 2.0
    return [
        Vector2(
            centre_x + math.cos(math.tau * index / SCHOOL_SIZE) * START_SPREAD,
            START_Y + math.sin(math.tau * index / SCHOOL_SIZE) * START_SPREAD,
        )
        for index in range(SCHOOL_SIZE)
    ]


def _mean_neighbour_distance(fish: list[_PredatorFish]) -> float:
    alive = [swimmer for swimmer in fish if not swimmer.dead]
    pairs = [
        (alive[i].pos - alive[j].pos).length()
        for i in range(len(alive))
        for j in range(i + 1, len(alive))
    ]
    return sum(pairs) / len(pairs) if pairs else 0.0


def run_predator_episode(
    schedule: tuple[PredatorSpawn, ...],
    policies: list[_PredatorPolicy],
    seed: int,
) -> PredatorResult:
    """Run one deterministic episode of the joint forage-and-evade problem."""
    if len(policies) != SCHOOL_SIZE:
        raise ValueError(f"expected {SCHOOL_SIZE} policies, got {len(policies)}")

    environment = _PredatorEnvironment(random.Random(seed))
    fish = [
        _PredatorFish(pos=position, environment=environment, fish_id=index)
        for index, position in enumerate(_starting_positions())
    ]
    environment.fish = fish
    environment.crabs = [_GymCrab(WORLD_WIDTH * 0.25), _GymCrab(WORLD_WIDTH * 0.75)]

    active_food: list[_PredatorFood] = []
    spawns_by_frame: dict[int, list[PredatorSpawn]] = {}
    for spawn in schedule:
        spawns_by_frame.setdefault(spawn.frame, []).append(spawn)

    energy_collected = 0.0
    food_collected = 0
    deaths_predation = 0
    deaths_starvation = 0
    alive_frames = 0
    neighbour_samples: list[float] = []

    for frame in range(EPISODE_FRAMES + 1):
        for spawn in spawns_by_frame.get(frame, ()):
            active_food.append(
                _PredatorFood(
                    pos=Vector2(spawn.x, spawn.y),
                    energy=spawn.energy,
                    expires_at=spawn.expires_at,
                )
            )
        environment.active_food = active_food
        for crab in environment.crabs:
            crab.step()

        food_view = tuple(active_food)
        for swimmer, policy in zip(fish, policies, strict=True):
            if swimmer.dead:
                continue
            swimmer.age += 1
            alive_frames += 1

            velocity = _clamp_velocity(policy.velocity(swimmer, food_view))
            next_pos = _step_position(swimmer.pos, velocity)
            distance = (next_pos - swimmer.pos).length()
            swimmer.pos = next_pos
            apply_energy_delta(
                swimmer,
                -(distance * ENERGY_COST_PER_DISTANCE + IDLE_ENERGY_DRAIN),
                source="predator_gym_metabolism",
                allow_direct_assignment=True,
            )

            remaining: list[_PredatorFood] = []
            for food in active_food:
                if (food.pos - swimmer.pos).length() <= CAPTURE_RADIUS:
                    energy_collected += food.energy
                    food_collected += 1
                    apply_energy_delta(
                        swimmer,
                        food.energy,
                        source="predator_gym_food",
                        allow_direct_assignment=True,
                    )
                else:
                    remaining.append(food)
            active_food = remaining

            if swimmer.energy <= 0.0:
                swimmer.dead = True
                deaths_starvation += 1
                continue

            for crab in environment.crabs:
                if (crab.pos - swimmer.pos).length() <= CRAB_CONTACT_RADIUS and crab.can_hunt():
                    crab.eat()
                    swimmer.dead = True
                    deaths_predation += 1
                    break

        active_food = [food for food in active_food if frame < food.expires_at]
        neighbour_samples.append(_mean_neighbour_distance(fish))

    total_possible = SCHOOL_SIZE * (EPISODE_FRAMES + 1)
    return PredatorResult(
        survival_ratio=alive_frames / total_possible if total_possible else 0.0,
        alive_at_end=sum(1 for swimmer in fish if not swimmer.dead),
        deaths_predation=deaths_predation,
        deaths_starvation=deaths_starvation,
        energy_collected=energy_collected,
        food_collected=food_collected,
        mean_neighbour_distance=(
            sum(neighbour_samples) / len(neighbour_samples) if neighbour_samples else 0.0
        ),
    )
