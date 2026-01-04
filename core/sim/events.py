"""Canonical simulation event definitions.

This module defines the standard events emitted by entities during simulation.
All events inherit from SimEvent and include a `frame` field for temporal tracking.

Event Hierarchy:
    SimEvent (base)
    ├── AteFood - Entity consumed food
    ├── Moved - Entity moved (with distance/speed)
    ├── EnergyBurned - Energy consumed (metabolism, movement, etc.)
    └── PokerGamePlayed - Poker game outcome

Usage:
    Events are emitted by entities via `entity._emit_event(event)` and recorded
    by EcosystemManager.record_event() for statistics tracking.

    Example:
        from core.sim.events import AteFood
        fish._emit_event(AteFood(
            entity_id=fish.fish_id,
            food_id=food.food_id,
            food_type="nectar",
            energy_gained=10.0,
            frame=frame_count,
        ))

Design Note:
    This module replaces the legacy `core.telemetry.events` module which
    lacked entity_id and frame tracking.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SimEvent:
    """Base class for all simulation events."""

    frame: int = field(default=0)


@dataclass(frozen=True)
class AteFood(SimEvent):
    entity_id: int = field(default=0)
    food_id: int = field(default=0)
    food_type: str = field(default="")
    energy_gained: float = field(default=0.0)
    nutritional_value: float = 1.0
    algorithm_id: Optional[int] = None


@dataclass(frozen=True)
class Moved(SimEvent):
    entity_id: int = field(default=0)
    distance: float = field(default=0.0)
    energy_cost: float = field(default=0.0)
    speed: float = 0.0


@dataclass(frozen=True)
class EnergyBurned(SimEvent):
    entity_id: int = field(default=0)
    amount: float = field(default=0.0)
    reason: str = field(default="")
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class PokerGamePlayed(SimEvent):
    entity_id: int = field(default=0)  # The fish
    energy_change: float = field(default=0.0)
    opponent_type: str = field(default="")  # "fish" or "plant"
    won: bool = field(default=False)
    hand_rank: str = ""
