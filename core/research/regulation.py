"""Measure what a tank benchmark actually holds constant.

The tank starves. Across sampled seeds, 86-97% of `survival_5k` deaths are
starvation, and the benchmark's own validity gate sits at 0.95 — close enough
that a third of sampled seeds are already invalid before anything changes. The
standing explanation was that food-seeking is broken, and the previous
measurement (`research/starvation/practice_ball_ablation.json`) ruled out the
one mechanism `CLAUDE.md` nominated without finding another.

This module measures the alternative: that starvation is not an outcome of fish
behaviour at all but a fixed point of the world configuration. Two regulators
act on the tank at once.

* `max_population` caps the fish count. Every tank benchmark sets it to 50-60.
* `FoodSpawningSystem._calculate_spawn_rate` is a closed loop on *total fish
  energy*: below `AUTO_FOOD_LOW_ENERGY_THRESHOLD` it triples the spawn rate,
  above `AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1` it slows it. Food is therefore not
  an exogenous resource; it is the actuator of a thermostat.

If both hold, energy *per fish* is a constant of the configuration, and no
amount of foraging skill can raise it — a better forager makes the thermostat
close the tap. The sweep here tests that directly by varying the food supply
across more than an order of magnitude and asking whether the steady state
moves with it.

The one quantity the thermostat does *not* see is the overflow reproduction
bank: `_calculate_spawn_rate` sums `fish.energy`, which excludes it, while
`survival_5k` scores `energy + overflow_energy_bank`. `SteadyState` keeps the
two apart for exactly that reason.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from core.entities.fish import Fish
    from core.worlds.interfaces import MultiAgentWorldBackend

# Sample often enough to see drift, rarely enough that sampling is not the cost.
DEFAULT_SAMPLE_INTERVAL = 100
# Discard the population ramp. At the stock food rate the tank reaches its
# population cap around frame 1300 of 5000; 0.4 clears that with margin at
# every rate swept so far.
DEFAULT_WARMUP_FRACTION = 0.4


def fish_of(world: MultiAgentWorldBackend) -> list[Fish]:
    """The fish in a world.

    Narrowed by type rather than by ``snapshot_type``: the benchmarks use the
    string tag to stay loosely coupled to the entity classes, but a research
    probe already depends on ``Fish`` internals, so the honest test is the class.
    """
    from core.entities.fish import Fish as FishClass

    return [e for e in world.entities_list if isinstance(e, FishClass)]


def food_count(world: MultiAgentWorldBackend) -> int:
    """Uneaten food entities present, live food included."""
    from core.entities.resources import Food

    return sum(1 for e in world.entities_list if isinstance(e, Food))


def banked_energy_of(fish: Fish) -> float:
    """Overflow energy a fish is holding for reproduction.

    Invisible to the food controller and counted by the benchmark score, which
    is why it is reported separately rather than folded into total energy.
    """
    return float(fish._reproduction_component.overflow_energy_bank)


@dataclass(frozen=True)
class SteadyState:
    """Time-averaged world state after the population ramp.

    Attributes:
        population: Mean fish count.
        raw_energy: Mean summed ``fish.energy`` — the quantity
            ``FoodSpawningSystem._calculate_spawn_rate`` reads and regulates.
        banked_energy: Mean summed overflow reproduction bank — which the
            controller does not read and the benchmark score does count.
        food_stock: Mean uneaten food entities present.
        samples: Number of samples averaged.
        drift: Fractional change in ``raw_energy`` between the first and second
            half of the averaging window. Near zero means the window really is
            a steady state rather than a slow ramp being averaged over.
    """

    population: float
    raw_energy: float
    banked_energy: float
    food_stock: float
    samples: int
    drift: float

    @property
    def raw_energy_per_fish(self) -> float:
        """Regulated energy divided by capped population."""
        return self.raw_energy / self.population if self.population else 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "population": round(self.population, 3),
            "raw_energy": round(self.raw_energy, 2),
            "raw_energy_per_fish": round(self.raw_energy_per_fish, 3),
            "banked_energy": round(self.banked_energy, 2),
            "food_stock": round(self.food_stock, 2),
            "samples": self.samples,
            "drift": round(self.drift, 5),
        }


# Named steady-state readings, in report order. An explicit map rather than
# dynamic attribute lookup so an unknown field name fails loudly here instead of
# silently reporting zero spread.
STEADY_FIELDS: dict[str, Callable[[SteadyState], float]] = {
    "population": lambda s: s.population,
    "raw_energy": lambda s: s.raw_energy,
    "raw_energy_per_fish": lambda s: s.raw_energy_per_fish,
    "banked_energy": lambda s: s.banked_energy,
    "food_stock": lambda s: s.food_stock,
}


@dataclass(frozen=True)
class RegulationPoint:
    """One (config value, seed) run of the sweep."""

    value: object
    seed: int
    steady: SteadyState

    def as_dict(self) -> dict[str, object]:
        return {"value": self.value, "seed": self.seed, **self.steady.as_dict()}


def spread_ratio(values: list[float]) -> float:
    """Largest value divided by smallest, as a plain magnitude of variation.

    A ratio rather than a variance because the question is comparative: how far
    the *output* moved against how far the *input* was moved. Returns 0.0 when
    the smallest value is zero, since an unbounded ratio would report a
    collapsed run as infinitely responsive.
    """
    if not values:
        return 0.0
    low, high = min(values), max(values)
    if low <= 0.0:
        return 0.0
    return high / low


@dataclass(frozen=True)
class RegulationSweep:
    """Steady states observed while one world-config key was varied."""

    benchmark_id: str
    key: str
    points: tuple[RegulationPoint, ...]

    def values(self) -> list[object]:
        seen: list[object] = []
        for point in self.points:
            if point.value not in seen:
                seen.append(point.value)
        return seen

    def field_spread(self, field: str) -> float:
        """Spread of one steady-state field across the whole sweep."""
        if field not in STEADY_FIELDS:
            raise ValueError(f"unknown field {field!r}; known: {sorted(STEADY_FIELDS)}")
        read = STEADY_FIELDS[field]
        return spread_ratio([read(p.steady) for p in self.points])

    def input_spread(self) -> float:
        """Spread of the swept config values themselves."""
        numeric = [float(v) for v in self.values() if isinstance(v, (int, float))]
        return spread_ratio(numeric)

    def as_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "key": self.key,
            "input_spread": round(self.input_spread(), 3),
            "spreads": {field: round(self.field_spread(field), 4) for field in STEADY_FIELDS},
            "points": [p.as_dict() for p in self.points],
        }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def measure_steady_state(
    benchmark: ModuleType,
    seed: int,
    overrides: dict[str, object] | None = None,
    *,
    frames: int | None = None,
    warmup_fraction: float = DEFAULT_WARMUP_FRACTION,
    sample_interval: int = DEFAULT_SAMPLE_INTERVAL,
) -> SteadyState:
    """Run a tank benchmark's world and average its state after the ramp.

    The world is stepped directly rather than through ``benchmark.run`` because
    the quantities that matter here — raw energy against banked energy, food
    stock — are internal state the benchmark result does not report.
    """
    from core.worlds import WorldRegistry
    from core.worlds.interfaces import FAST_STEP_ACTION

    if not 0.0 <= warmup_fraction < 1.0:
        raise ValueError(f"warmup_fraction must be in [0, 1), got {warmup_fraction}")
    if sample_interval < 1:
        raise ValueError(f"sample_interval must be positive, got {sample_interval}")

    total_frames = frames if frames is not None else int(benchmark.FRAMES)
    config = dict(benchmark.WORLD_CONFIG)
    config.update(overrides or {})

    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    warmup_frames = int(total_frames * warmup_fraction)
    populations: list[float] = []
    raw: list[float] = []
    banked: list[float] = []
    stock: list[float] = []

    for i in range(total_frames):
        world.step({FAST_STEP_ACTION: True})
        frame = i + 1
        if frame % sample_interval or frame <= warmup_frames:
            continue
        fish = fish_of(world)
        populations.append(float(len(fish)))
        raw.append(sum(float(f.energy) for f in fish))
        banked.append(sum(banked_energy_of(f) for f in fish))
        stock.append(float(food_count(world)))

    half = len(raw) // 2
    early, late = _mean(raw[:half]), _mean(raw[half:])
    drift = (late - early) / early if early else 0.0

    return SteadyState(
        population=_mean(populations),
        raw_energy=_mean(raw),
        banked_energy=_mean(banked),
        food_stock=_mean(stock),
        samples=len(raw),
        drift=drift,
    )


def sweep_world_config(
    benchmark: ModuleType,
    key: str,
    values: Sequence[object],
    seeds: Sequence[int],
    *,
    frames: int | None = None,
    warmup_fraction: float = DEFAULT_WARMUP_FRACTION,
    sample_interval: int = DEFAULT_SAMPLE_INTERVAL,
) -> RegulationSweep:
    """Measure the steady state at each value of one world-config key.

    Warns nothing and guesses nothing about keys the benchmark does not pin:
    callers that care should check ``key in benchmark.WORLD_CONFIG`` first, as
    ``tools/ablate_world_config.py`` does.
    """
    points = [
        RegulationPoint(
            value=value,
            seed=seed,
            steady=measure_steady_state(
                benchmark,
                seed,
                {key: value},
                frames=frames,
                warmup_fraction=warmup_fraction,
                sample_interval=sample_interval,
            ),
        )
        for value in values
        for seed in seeds
    ]
    return RegulationSweep(
        benchmark_id=str(benchmark.BENCHMARK_ID),
        key=key,
        points=tuple(points),
    )
