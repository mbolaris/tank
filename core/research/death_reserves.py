"""Record what each fish was still holding at the moment it died.

`survival_5k` reports a death *mix* - so many starvations, so many old ages -
and nothing about the balance sheet behind it. That gap hid the tank's actual
failure for a long time. A fish banks everything it gains above `max_energy`
into an overflow reproduction bank, and before `_draw_on_reserves` existed that
bank could be spent on offspring and on nothing else. Measured at the death
site rather than inferred from the mix, 51% of seed 42's `survival_5k`
starvation deaths were fish at exactly zero energy holding a mean of 147 banked
units, and 29-32% on seeds 2 and 999 - 36,823 energy destroyed across the three,
with seed 42's 12,233 alone exceeding twice the tank's entire standing energy.

The distinction this module exists to preserve is between `fish.energy`, which
hits zero and kills the fish, and `overflow_energy_bank`, which does not and
used to die with it. `record_death` flattens the two into a single
`remaining_energy` sum, so nothing downstream of it can tell a fish that
starved empty from one that starved rich.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from core.entities.fish import Fish

# Banks below this are rounding, not savings: a fish that died holding a
# fraction of an energy unit was not meaningfully solvent.
SOLVENT_BANK_THRESHOLD = 0.5


@dataclass(frozen=True)
class DeathRecord:
    """One fish's balance sheet at the instant its death was recorded."""

    fish_id: int
    cause: str
    energy: float
    bank: float
    max_energy: float
    age: int
    generation: int

    @property
    def solvent(self) -> bool:
        """Died holding reserves it was not permitted to spend on surviving."""
        return self.bank > SOLVENT_BANK_THRESHOLD

    def as_dict(self) -> dict[str, object]:
        return {
            "fish_id": self.fish_id,
            "cause": self.cause,
            "energy": round(self.energy, 4),
            "bank": round(self.bank, 4),
            "max_energy": round(self.max_energy, 4),
            "age": self.age,
            "generation": self.generation,
        }


@dataclass(frozen=True)
class CauseSummary:
    """Aggregate balance sheet for every death sharing one cause."""

    cause: str
    deaths: int
    solvent_deaths: int
    mean_energy: float
    mean_bank: float
    median_bank: float
    max_bank: float
    total_bank_destroyed: float

    @property
    def solvent_share(self) -> float:
        return self.solvent_deaths / self.deaths if self.deaths else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "cause": self.cause,
            "deaths": self.deaths,
            "solvent_deaths": self.solvent_deaths,
            "solvent_share": round(self.solvent_share, 4),
            "mean_energy": round(self.mean_energy, 3),
            "mean_bank": round(self.mean_bank, 3),
            "median_bank": round(self.median_bank, 3),
            "max_bank": round(self.max_bank, 3),
            "total_bank_destroyed": round(self.total_bank_destroyed, 1),
        }


def summarize(records: list[DeathRecord]) -> list[CauseSummary]:
    """One summary per cause, ordered by how many deaths it accounts for."""
    causes: dict[str, list[DeathRecord]] = {}
    for record in records:
        causes.setdefault(record.cause, []).append(record)

    summaries = [
        CauseSummary(
            cause=cause,
            deaths=len(group),
            solvent_deaths=sum(1 for r in group if r.solvent),
            mean_energy=mean(r.energy for r in group),
            mean_bank=mean(r.bank for r in group),
            median_bank=median(r.bank for r in group),
            max_bank=max(r.bank for r in group),
            total_bank_destroyed=sum(r.bank for r in group),
        )
        for cause, group in causes.items()
    ]
    return sorted(summaries, key=lambda s: (-s.deaths, s.cause))


def record_deaths(
    benchmark: ModuleType,
    seed: int,
    *,
    frames: int | None = None,
) -> list[DeathRecord]:
    """Run a tank benchmark, capturing each fish's state as its death is booked.

    The capture wraps ``EntityLifecycleSystem.record_fish_death`` because that
    is the last point at which the fish object still holds both numbers; by the
    time ``PopulationTracker.record_death`` sees them they have been added
    together. It is called repeatedly for a fish that is already dead, so only
    the first sighting of each ``fish_id`` is kept.
    """
    from core.simulation.engine import SimulationEngine
    from core.systems.entity_lifecycle import EntityLifecycleSystem
    from core.worlds import WorldRegistry
    from core.worlds.interfaces import FAST_STEP_ACTION
    from core.worlds.tank.backend import TankWorldBackendAdapter

    total_frames = frames if frames is not None else int(benchmark.FRAMES)
    config = dict(benchmark.WORLD_CONFIG)
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    # The death site is tank engine internals that the world-backend protocol
    # does not expose, so narrow to the concrete types rather than reach through
    # them dynamically.
    if not isinstance(world, TankWorldBackendAdapter):  # pragma: no cover
        raise RuntimeError(f"expected a tank world backend, got {type(world).__name__}")
    environment = world.world
    if environment is None:  # pragma: no cover
        raise RuntimeError("tank world was not reset before observation")
    engine = environment.engine
    if not isinstance(engine, SimulationEngine):  # pragma: no cover
        raise RuntimeError("tank world has no simulation engine to observe")
    lifecycle = next(
        (s for s in engine.get_systems() if isinstance(s, EntityLifecycleSystem)),
        None,
    )
    if lifecycle is None:  # pragma: no cover - the tank world always has one
        raise RuntimeError("tank world has no EntityLifecycleSystem to observe")

    records: list[DeathRecord] = []
    seen: set[int] = set()
    original = lifecycle.record_fish_death

    def capture(fish: Fish, cause: str | None = None, *args: object, **kwargs: object) -> None:
        if fish.fish_id not in seen:
            seen.add(fish.fish_id)
            records.append(
                DeathRecord(
                    fish_id=int(fish.fish_id),
                    cause=str(cause or fish.get_death_cause()),
                    energy=float(fish.energy),
                    bank=float(fish._reproduction_component.overflow_energy_bank),
                    max_energy=float(fish.max_energy),
                    age=int(fish.age or 0),
                    generation=int(fish.generation),
                )
            )
        original(fish, cause, *args, **kwargs)

    lifecycle.record_fish_death = capture  # type: ignore[method-assign]
    try:
        for _ in range(total_frames):
            world.step({FAST_STEP_ACTION: True})
    finally:
        lifecycle.record_fish_death = original  # type: ignore[method-assign]

    return records
