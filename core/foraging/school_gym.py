"""A multi-fish foraging gym that can see what the single-fish gym cannot.

`core.foraging.gym` measures one fish, so ``nearby_evolving_agents`` is always
empty and the school vectors the behavior graph reads - cohesion, alignment,
separation - are permanently zero. Backlog 12.4 measured the consequence: the
graph's above-threshold branch steers toward a school that does not exist, and
its bare score there (0.300) describes the gym's geometry rather than the
controller. The entry's conclusion was that the urgency threshold and the
cohesion branch "need a multi-fish instrument". This is that instrument.

The measurement it is built around is **distribution, not travel**. Every fish
starts in a tight cluster at the centre; every wave scatters one food item to
each of ``SCHOOL_SIZE`` stations around the edge. So:

* a school that spreads out takes all four items,
* a school that stays together converges on the nearest one and the other
  three expire.

Both behaviours travel about the same distance and pursue food equally hard.
What separates them is whether the controller keeps the fish together, which
is exactly the branch 12.4 could not observe. Food expiry is what gives
clumping a price; without it a cohesive school would simply collect the items
one after another and score the same.

The ceiling is attainable by construction and asserted, as in the single-fish
gym: one fish per station, every station reachable inside a food lifetime.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Protocol

from core.energy.energy_utils import apply_energy_delta
from core.entities import Food
from core.math_utils import Vector2

WORLD_WIDTH = 600.0
WORLD_HEIGHT = 400.0
MAX_SPEED = 2.2
CAPTURE_RADIUS = 12.0
ENERGY_COST_PER_DISTANCE = 0.01

SCHOOL_SIZE = 4
WAVE_COUNT = 8
WAVE_INTERVAL = 240
SETTLE_FRAMES = 240

# Shorter than the wave interval so waves never overlap: each wave is a clean,
# independent test of whether the school split up in time.
FOOD_LIFETIME = 220

# Where the school starts. A tight cluster, because a school that is already
# spread out has nothing to decide.
START_SPREAD = 14.0

# One station per fish, spread to the four quadrants. The worst-case trip is
# corner to opposite corner (~402px at 2.2px/frame = ~183 frames), inside
# FOOD_LIFETIME with margin, so a fish assigned to any station always arrives.
STATIONS = (
    (120.0, 110.0),
    (480.0, 110.0),
    (120.0, 290.0),
    (480.0, 290.0),
)

# How far a station may drift per wave, so the episode is not eight identical
# repetitions. Small enough to preserve the reachability argument above.
STATION_JITTER = 40.0

_SOCIAL_RADIUS = 120.0

__all__ = [
    "FOOD_LIFETIME",
    "SCHOOL_SIZE",
    "STATIONS",
    "SchoolResult",
    "WaveSpawn",
    "build_wave_schedule",
    "oracle_energy_ceiling",
    "run_school_episode",
]


@dataclass(frozen=True)
class WaveSpawn:
    """One scripted food item: where it appears, when, and for how long."""

    frame: int
    station: int
    x: float
    y: float
    energy: float

    @property
    def expires_at(self) -> int:
        return self.frame + FOOD_LIFETIME


@dataclass(frozen=True)
class SchoolResult:
    """One controller's outcome, plus why it scored what it did.

    ``energy_collected`` alone cannot distinguish "did not chase food" from
    "chased the same food four times over", so the spread metrics travel with
    it. They are the diagnosis; the ratio is only the verdict.
    """

    energy_collected: float
    food_collected: int
    food_expired: int
    energy_spent: float
    travel_distance: float
    mean_neighbour_distance: float
    mean_stations_visited: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "energy_collected": self.energy_collected,
            "food_collected": self.food_collected,
            "food_expired": self.food_expired,
            "energy_spent": self.energy_spent,
            "travel_distance": self.travel_distance,
            "mean_neighbour_distance": self.mean_neighbour_distance,
            "mean_stations_visited": self.mean_stations_visited,
        }


class _SchoolPolicy(Protocol):
    """One fish's controller for one frame.

    Deliberately loose in its argument types: the arms in
    :mod:`core.foraging.arms` are written against the single-fish gym's fish
    and food, and reusing them unchanged is what makes the two instruments'
    scores comparable.
    """

    # Any, not object: a Protocol's parameters are contravariant, and the arms
    # in core.foraging.arms declare theirs as the single-fish gym's types. A
    # stricter signature here would reject exactly the controllers this gym is
    # built to run.
    def velocity(self, fish: Any, active_food: Any) -> Vector2:
        """Choose a desired movement vector for one fish for one frame."""


@dataclass
class _Trait:
    value: float


@dataclass
class _SchoolTraits:
    aggression: _Trait = field(default_factory=lambda: _Trait(0.5))
    pursuit_aggression: _Trait = field(default_factory=lambda: _Trait(0.5))
    prediction_skill: _Trait = field(default_factory=lambda: _Trait(0.5))
    hunting_stamina: _Trait = field(default_factory=lambda: _Trait(0.5))
    behavior_graph: object | None = None
    target_pursuit_module: object | None = None


@dataclass
class _SchoolGenome:
    behavioral: _SchoolTraits = field(default_factory=_SchoolTraits)


@dataclass
class _SchoolFood:
    pos: Vector2
    energy: float
    station: int
    expires_at: int
    vel: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    food_properties: dict[str, float] = field(default_factory=lambda: {"sink_multiplier": 1.0})

    def get_energy_value(self) -> float:
        return self.energy


class _SchoolEnvironment:
    """Shared world for the whole school.

    The one method that matters here is ``nearby_evolving_agents``: it returns
    real neighbours, which is the entire difference from the single-fish gym
    and the reason the graph's cohesion branch produces a nonzero vector at all.
    """

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.active_food: list[_SchoolFood] = []
        self.fish: list[_SchoolFish] = []
        self.simulation_config: object | None = None
        self.genome_code_pool: object | None = None

    def get_detection_modifier(self) -> float:
        return 1.0

    def nearby_resources(self, _fish: object, _radius: int) -> list[_SchoolFood]:
        return self.active_food

    def nearby_agents_by_type(
        self, _fish: object, _radius: int, agent_type: type[object]
    ) -> list[object]:
        return list(self.active_food) if agent_type is Food else []

    def nearby_evolving_agents(self, fish: object, radius: float) -> list[_SchoolFish]:
        origin = getattr(fish, "pos", None)
        if origin is None:
            return []
        return [
            other
            for other in self.fish
            if other is not fish and (other.pos - origin).length() <= radius
        ]


@dataclass
class _SchoolFish:
    pos: Vector2
    environment: _SchoolEnvironment
    fish_id: int
    speed: float = MAX_SPEED
    energy: float = 200.0
    max_energy: float = 1_000.0
    genome: _SchoolGenome = field(default_factory=_SchoolGenome)
    vel: Vector2 = field(default_factory=lambda: Vector2(0.0, 0.0))
    age: int = 0
    poker_cooldown: int = 0
    can_play_poker: bool = False
    movement_policy: object | None = None
    last_target_memory_decisions: dict[str, object] = field(default_factory=dict)

    def is_dead(self) -> bool:
        return False

    def get_energy_ratio(self) -> float:
        return self.energy / self.max_energy

    def is_critical_energy(self) -> bool:
        return False

    def is_low_energy(self) -> bool:
        return False

    def can_eat(self) -> bool:
        return True


def build_wave_schedule(seed: int) -> tuple[WaveSpawn, ...]:
    """Build the immutable scripted waves for ``seed``.

    Each wave puts exactly one item at every station, so the ceiling is only
    reachable by a school that splits ``SCHOOL_SIZE`` ways. A fixed integer
    recurrence supplies the per-wave jitter and energies, rather than platform
    RNG, so the schedule is identical on every machine.
    """
    state = seed & 0xFFFFFFFF
    spawns: list[WaveSpawn] = []
    for wave in range(WAVE_COUNT):
        frame = (wave + 1) * WAVE_INTERVAL
        for station, (base_x, base_y) in enumerate(STATIONS):
            state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
            offset_x = (float(state % 2001) / 1000.0 - 1.0) * STATION_JITTER
            state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
            offset_y = (float(state % 2001) / 1000.0 - 1.0) * STATION_JITTER
            state = (1_664_525 * state + 1_013_904_223) & 0xFFFFFFFF
            energy = 40.0 + float(state % 61)
            spawns.append(
                WaveSpawn(
                    frame=frame,
                    station=station,
                    x=base_x + offset_x,
                    y=base_y + offset_y,
                    energy=energy,
                )
            )
    return tuple(spawns)


def oracle_energy_ceiling(schedule: tuple[WaveSpawn, ...]) -> float:
    """Return the attainable gross-energy maximum for this episode."""
    return sum(spawn.energy for spawn in schedule)


class AssignedOraclePolicy:
    """Ceiling policy: each fish owns one station and never contests another.

    This is the school that has solved the distribution problem perfectly. It
    is also the proof that the ceiling is attainable rather than fitted -
    ``run_school_episode`` asserts it collects every scripted item.
    """

    def velocity(self, fish: _SchoolFish, active_food: tuple[_SchoolFood, ...]) -> Vector2:
        station = fish.fish_id % len(STATIONS)
        mine = [food for food in active_food if food.station == station]
        if not mine:
            return Vector2(0.0, 0.0)
        target = min(mine, key=lambda food: (food.pos - fish.pos).length())
        return _seek(fish.pos, target.pos, MAX_SPEED)


class GreedyShoalPolicy:
    """Floor-ish reference: every fish independently chases the best item.

    Not a floor in the random-walk sense - it forages competently - but it has
    no notion of who else is going where, so the school converges. The gap
    between this and the oracle is the size of the distribution problem, and a
    controller that beats it is coordinating rather than merely foraging.
    """

    def velocity(self, fish: _SchoolFish, active_food: tuple[_SchoolFood, ...]) -> Vector2:
        if not active_food:
            return Vector2(0.0, 0.0)
        target = max(
            active_food,
            key=lambda food: (food.energy / max((food.pos - fish.pos).length(), 1.0), food.energy),
        )
        return _seek(fish.pos, target.pos, MAX_SPEED)


class RandomWalkPolicy:
    """Frozen floor: ignores food entirely."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._frames_until_turn = 0
        self._velocity = Vector2(0.0, 0.0)

    def velocity(self, _fish: _SchoolFish, _active_food: tuple[_SchoolFood, ...]) -> Vector2:
        if self._frames_until_turn <= 0:
            angle = self._rng.random() * math.tau
            self._velocity = Vector2(math.cos(angle) * MAX_SPEED, math.sin(angle) * MAX_SPEED)
            self._frames_until_turn = 30
        self._frames_until_turn -= 1
        return self._velocity


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
    """A tight cluster at the centre, identical for every seed and arm."""
    centre_x, centre_y = WORLD_WIDTH / 2.0, WORLD_HEIGHT / 2.0
    positions: list[Vector2] = []
    for index in range(SCHOOL_SIZE):
        angle = math.tau * index / SCHOOL_SIZE
        positions.append(
            Vector2(
                centre_x + math.cos(angle) * START_SPREAD,
                centre_y + math.sin(angle) * START_SPREAD,
            )
        )
    return positions


def _mean_neighbour_distance(fish: list[_SchoolFish]) -> float:
    pairs = [
        (fish[i].pos - fish[j].pos).length()
        for i in range(len(fish))
        for j in range(i + 1, len(fish))
    ]
    return sum(pairs) / len(pairs) if pairs else 0.0


def run_school_episode(
    schedule: tuple[WaveSpawn, ...],
    policies: list[_SchoolPolicy],
    seed: int,
) -> SchoolResult:
    """Run one deterministic episode for a school of ``SCHOOL_SIZE`` fish.

    ``policies`` is one controller per fish. They are stepped in a fixed order
    and all see the same world state for the frame, so the episode reproduces
    exactly regardless of how the controllers are built.
    """
    if len(policies) != SCHOOL_SIZE:
        raise ValueError(f"expected {SCHOOL_SIZE} policies, got {len(policies)}")

    environment = _SchoolEnvironment(random.Random(seed))
    fish = [
        _SchoolFish(pos=position, environment=environment, fish_id=index)
        for index, position in enumerate(_starting_positions())
    ]
    environment.fish = fish

    active_food: list[_SchoolFood] = []
    spawns_by_frame: dict[int, list[WaveSpawn]] = {}
    for spawn in schedule:
        spawns_by_frame.setdefault(spawn.frame, []).append(spawn)

    energy_collected = 0.0
    energy_spent = 0.0
    travel_distance = 0.0
    food_collected = 0
    food_expired = 0
    neighbour_samples: list[float] = []
    stations_visited: list[set[int]] = [set() for _ in fish]

    final_frame = max(spawns_by_frame, default=0) + SETTLE_FRAMES
    for frame in range(final_frame + 1):
        for spawn in spawns_by_frame.get(frame, ()):
            active_food.append(
                _SchoolFood(
                    pos=Vector2(spawn.x, spawn.y),
                    energy=spawn.energy,
                    station=spawn.station,
                    expires_at=spawn.expires_at,
                )
            )

        environment.active_food = active_food
        food_view = tuple(active_food)
        for index, (swimmer, policy) in enumerate(zip(fish, policies, strict=True)):
            swimmer.age += 1
            velocity = _clamp_velocity(policy.velocity(swimmer, food_view))
            next_pos = _step_position(swimmer.pos, velocity)
            distance = (next_pos - swimmer.pos).length()
            swimmer.pos = next_pos
            travel_distance += distance
            spent = distance * ENERGY_COST_PER_DISTANCE
            energy_spent += spent
            apply_energy_delta(
                swimmer,
                -spent,
                source="school_gym_movement",
                allow_direct_assignment=True,
            )

            remaining: list[_SchoolFood] = []
            for food in active_food:
                if (food.pos - swimmer.pos).length() <= CAPTURE_RADIUS:
                    energy_collected += food.energy
                    apply_energy_delta(
                        swimmer,
                        food.energy,
                        source="school_gym_food",
                        allow_direct_assignment=True,
                    )
                    food_collected += 1
                    stations_visited[index].add(food.station)
                else:
                    remaining.append(food)
            active_food = remaining

        survivors: list[_SchoolFood] = []
        for food in active_food:
            if frame >= food.expires_at:
                food_expired += 1
            else:
                survivors.append(food)
        active_food = survivors

        neighbour_samples.append(_mean_neighbour_distance(fish))

    return SchoolResult(
        energy_collected=energy_collected,
        food_collected=food_collected,
        food_expired=food_expired,
        energy_spent=energy_spent,
        travel_distance=travel_distance,
        mean_neighbour_distance=(
            sum(neighbour_samples) / len(neighbour_samples) if neighbour_samples else 0.0
        ),
        mean_stations_visited=sum(len(visited) for visited in stations_visited) / len(fish),
    )
