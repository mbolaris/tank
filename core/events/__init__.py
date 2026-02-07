"""Events module for domain event dispatch.

This module provides the EventBus for decoupling domain logic from
telemetry/statistics recording, plus typed domain event definitions.
"""

from core.events.domain_events import (
    EnergyBurnedEvent,
    EnergyGainedEvent,
    EnergyTransferredEvent,
    EntityAteFoodEvent,
    EntityDiedEvent,
    EntitySpawnedEvent,
    PokerHandResolvedEvent,
    ReproductionOccurredEvent,
)
from core.events.event_bus import EventBus

__all__ = [
    "EnergyBurnedEvent",
    "EnergyGainedEvent",
    "EnergyTransferredEvent",
    "EntityAteFoodEvent",
    "EntityDiedEvent",
    "EntitySpawnedEvent",
    "EventBus",
    "PokerHandResolvedEvent",
    "ReproductionOccurredEvent",
]
