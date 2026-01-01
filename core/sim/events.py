from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass(frozen=True, kw_only=True)
class SimEvent:
    """Base class for all simulation events."""
    frame: int = 0

@dataclass(frozen=True, kw_only=True)
class AteFood(SimEvent):
    entity_id: int
    food_id: int
    food_type: str
    energy_gained: float
    nutritional_value: float = 1.0
    algorithm_id: Optional[int] = None

@dataclass(frozen=True, kw_only=True)
class Moved(SimEvent):
    entity_id: int
    distance: float
    energy_cost: float
    speed: float = 0.0

@dataclass(frozen=True, kw_only=True)
class EnergyBurned(SimEvent):
    entity_id: int
    amount: float
    reason: str
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

@dataclass(frozen=True, kw_only=True)
class PokerGamePlayed(SimEvent):
    entity_id: int  # The fish
    energy_change: float
    opponent_type: str # "fish" or "plant"
    won: bool
    hand_rank: str = ""
