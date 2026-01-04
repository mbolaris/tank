"""Telemetry event definitions for simulation stats recording.

.. deprecated::
    This module is deprecated. Use `core.sim.events` instead, which provides
    events with frame tracking and entity_id fields.

    Migration guide:
    - EnergyBurnEvent -> EnergyBurned (add entity_id, frame)
    - EnergyGainEvent -> (use AteFood or emit via entity._emit_event)
    - FoodEatenEvent -> AteFood
    - BirthEvent -> (handled by Fish.register_birth, emits BirthEvent internally)
    - ReproductionEvent -> (handled by reproduction system)

    The telemetry events here are still functional for backward compatibility,
    but new code should use core.sim.events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence, Union

if TYPE_CHECKING:
    from core.genetics import Genome


@dataclass(frozen=True)
class EnergyBurnEvent:
    """Energy spent, recorded by source and scope."""

    source: str
    amount: float
    scope: str = "fish"  # "fish" or "plant"


@dataclass(frozen=True)
class EnergyGainEvent:
    """Energy gained, recorded by source and scope."""

    source: str
    amount: float
    scope: str = "fish"  # "fish" or "plant"


@dataclass(frozen=True)
class FoodEatenEvent:
    """Food consumption event for telemetry."""

    food_type: str  # "nectar", "live_food", "falling_food"
    algorithm_id: int
    energy_gained: float
    genome: Genome | None = None
    generation: int | None = None


@dataclass(frozen=True)
class BirthEvent:
    """Birth event for lineage and energy accounting."""

    fish_id: int
    generation: int
    parent_ids: Sequence[int] | None
    algorithm_id: int | None
    color_hex: str
    energy: float
    is_soup_spawn: bool
    algorithm_name: str | None = None  # Direct algorithm name (avoids lookup)
    tank_name: str | None = None  # Tank where fish was born


@dataclass(frozen=True)
class ReproductionEvent:
    """Reproduction event for stats."""

    algorithm_id: int
    is_asexual: bool = False


TelemetryEvent = Union[
    EnergyBurnEvent,
    EnergyGainEvent,
    FoodEatenEvent,
    BirthEvent,
    ReproductionEvent,
]
