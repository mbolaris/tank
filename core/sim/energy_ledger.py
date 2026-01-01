from typing import List, Optional
from dataclasses import dataclass, field
from core.sim.events import SimEvent, AteFood, Moved, EnergyBurned, PokerGamePlayed

@dataclass(frozen=True)
class EnergyDelta:
    entity_id: int
    delta: float
    reason: str
    metadata: Optional[dict] = field(default_factory=dict)

class EnergyLedger:
    """
    Central authority for applying energy changes based on domain events.
    Deterministic and functional.
    """
    
    def apply(self, event: SimEvent) -> List[EnergyDelta]:
        """
        Process an event and return a list of energy deltas to be applied.
        """
        if isinstance(event, AteFood):
            return [EnergyDelta(
                entity_id=event.entity_id,
                delta=event.energy_gained,
                reason="ate_food",
                metadata={
                    "food_type": event.food_type,
                    "food_id": event.food_id,
                    "algorithm_id": event.algorithm_id
                }
            )]
        
        elif isinstance(event, Moved):
            # In this model, the event carrier has already calculated the cost.
            # In a more advanced model, the Ledger could calculate it given Physics params.
            return [EnergyDelta(
                entity_id=event.entity_id,
                delta=-abs(event.energy_cost),
                reason="movement",
                metadata={"distance": event.distance, "speed": event.speed}
            )]

        elif isinstance(event, EnergyBurned):
            # NOTE: EnergyBurned events are emitted for telemetry purposes only.
            # The actual energy reduction is handled directly by EnergyComponent.consume_energy().
            # Returning an empty list prevents double-consumption.
            return []
            
        elif isinstance(event, PokerGamePlayed):
            return [EnergyDelta(
                entity_id=event.entity_id,
                delta=event.energy_change,
                reason="poker_game",
                metadata={
                    "opponent_type": event.opponent_type,
                    "won": event.won,
                    "hand_rank": event.hand_rank
                }
            )]

        return []
