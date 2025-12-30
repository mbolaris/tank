"""Telemetry event definitions for simulation stats recording."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Union, TYPE_CHECKING

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
    genome: Optional["Genome"] = None
    generation: Optional[int] = None


@dataclass(frozen=True)
class BirthEvent:
    """Birth event for lineage and energy accounting."""

    fish_id: int
    generation: int
    parent_ids: Optional[Sequence[int]]
    algorithm_id: Optional[int]
    color_hex: str
    energy: float
    is_soup_spawn: bool
    algorithm_name: Optional[str] = None  # Direct algorithm name (avoids lookup)
    tank_name: Optional[str] = None  # Tank where fish was born


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
