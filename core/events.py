"""Event system for decoupling simulation components.

This module implements a simple publish-subscribe (pub/sub) event system.
It allows components to communicate without direct dependencies.

Why Events?
-----------
Before: Fish directly calls ecosystem methods
    if self.ecosystem is not None:
        self.ecosystem.record_energy_burn("movement", cost)

After: Fish emits an event, ecosystem subscribes to it
    emit(EnergyBurnedEvent("movement", cost, self.fish_id))

Benefits:
- Fish doesn't need to know about EcosystemManager
- Easy to add new subscribers (logging, UI, tests)
- Easier to test components in isolation
- Clear separation of concerns

Usage:
------
# Define an event type (or use existing ones)
@dataclass
class FishDiedEvent:
    fish_id: int
    cause: str
    frame: int

# Subscribe to events
def on_fish_died(event: FishDiedEvent) -> None:
    print(f"Fish {event.fish_id} died from {event.cause}")

event_bus.subscribe(FishDiedEvent, on_fish_died)

# Emit events
event_bus.emit(FishDiedEvent(fish_id=42, cause="starvation", frame=1000))

Thread Safety:
--------------
This implementation is NOT thread-safe. For multi-threaded simulations,
wrap emit() and subscribe() with locks.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

# Type variable for event types
E = TypeVar("E")


@dataclass
class Event:
    """Base class for all events.

    All events should inherit from this class for type safety.
    Use @dataclass for convenient event definition.
    """

    frame: int = 0  # Frame when event occurred (0 if not set)


# ============================================================================
# Core Simulation Events
# ============================================================================


@dataclass
class EnergyChangedEvent(Event):
    """Emitted when an entity's energy changes."""

    entity_id: int = 0
    entity_type: str = "fish"  # "fish", "plant", "food"
    source: str = ""  # "metabolism", "movement", "eating", "poker", etc.
    amount: float = 0.0  # Positive = gained, negative = lost
    new_total: float = 0.0


@dataclass
class EntityDiedEvent(Event):
    """Emitted when an entity dies."""

    entity_id: int = 0
    entity_type: str = "fish"
    cause: str = "unknown"
    age: int = 0
    generation: int = 0


@dataclass
class EntityBornEvent(Event):
    """Emitted when a new entity is created."""

    entity_id: int = 0
    entity_type: str = "fish"
    parent_id: Optional[int] = None
    generation: int = 0
    position: tuple = (0.0, 0.0)


@dataclass
class CollisionEvent(Event):
    """Emitted when two entities collide."""

    entity1_id: int = 0
    entity1_type: str = ""
    entity2_id: int = 0
    entity2_type: str = ""
    collision_type: str = ""  # "eating", "mating", "poker", "predation"


@dataclass
class PokerGameEvent(Event):
    """Emitted when a poker game completes."""

    winner_id: int = 0
    loser_ids: List[int] = None  # type: ignore[assignment]
    winner_type: str = "fish"  # "fish" or "plant"
    loser_types: List[str] = None  # type: ignore[assignment]
    energy_transferred: float = 0.0
    winner_hand: str = ""
    loser_hands: List[str] = None  # type: ignore[assignment]
    is_tie: bool = False
    house_cut: float = 0.0

    def __post_init__(self) -> None:
        # Normalize list defaults
        if self.loser_ids is None:
            self.loser_ids = []
        if self.loser_types is None:
            self.loser_types = []
        if self.loser_hands is None:
            self.loser_hands = []


@dataclass
class ReproductionEvent(Event):
    """Emitted when reproduction occurs."""

    parent_id: int = 0
    offspring_id: int = 0
    is_asexual: bool = True
    energy_transferred: float = 0.0
    generation: int = 0


@dataclass
class SystemStateEvent(Event):
    """Emitted for system state changes (day/night, etc.)."""

    system: str = ""  # "time", "weather", etc.
    state: str = ""  # "day", "night", etc.
    value: float = 0.0  # Optional numeric value


@dataclass
class PhaseTransitionEvent(Event):
    """Emitted at the start and end of each simulation phase."""

    phase: str = ""
    status: str = "start"  # "start" or "end"


# ============================================================================
# Event Bus Implementation
# ============================================================================


class EventBus:
    """Central hub for event publication and subscription.

    The EventBus implements the publish-subscribe pattern, allowing
    components to communicate without direct dependencies.

    Example:
        bus = EventBus()

        # Subscribe
        bus.subscribe(FishDiedEvent, lambda e: print(f"Fish {e.fish_id} died"))

        # Emit
        bus.emit(FishDiedEvent(fish_id=1, cause="starvation", frame=100))
    """

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        # Maps event type -> list of subscriber callbacks
        self._subscribers: Dict[Type[Event], List[Callable[[Any], None]]] = {}
        # Count of events emitted (for debugging)
        self._emit_count: int = 0
        # Whether to log events (useful for debugging)
        self._debug_logging: bool = False

    def subscribe(
        self,
        event_type: Type[E],
        callback: Callable[[E], None],
    ) -> Callable[[], None]:
        """Subscribe to events of a specific type.

        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when event is emitted

        Returns:
            Unsubscribe function - call it to remove the subscription

        Example:
            def on_death(event: EntityDiedEvent) -> None:
                log_death(event)

            unsubscribe = bus.subscribe(EntityDiedEvent, on_death)
            # Later...
            unsubscribe()  # Stop receiving events
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)

        # Return unsubscribe function
        def unsubscribe() -> None:
            if callback in self._subscribers.get(event_type, []):
                self._subscribers[event_type].remove(callback)

        return unsubscribe

    def emit(self, event: Event) -> None:
        """Emit an event to all subscribers.

        Args:
            event: The event to emit

        Note:
            Subscribers are called synchronously in subscription order.
            If a subscriber raises an exception, it's logged and other
            subscribers still receive the event.
        """
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])

        if self._debug_logging and subscribers:
            logger.debug(f"Emitting {event_type.__name__} to {len(subscribers)} subscribers")

        self._emit_count += 1

        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"Error in event subscriber for {event_type.__name__}: {e}",
                    exc_info=True,
                )

    def emit_many(self, events: List[Event]) -> None:
        """Emit multiple events efficiently.

        Args:
            events: List of events to emit
        """
        for event in events:
            self.emit(event)

    def clear(self) -> None:
        """Remove all subscribers. Useful for testing."""
        self._subscribers.clear()

    def subscriber_count(self, event_type: Type[Event]) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))

    @property
    def total_emit_count(self) -> int:
        """Total number of events emitted."""
        return self._emit_count

    def enable_debug_logging(self, enabled: bool = True) -> None:
        """Enable or disable debug logging of events."""
        self._debug_logging = enabled

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the event bus."""
        return {
            "total_emits": self._emit_count,
            "event_types": len(self._subscribers),
            "total_subscribers": sum(
                len(subs) for subs in self._subscribers.values()
            ),
            "subscribers_by_type": {
                event_type.__name__: len(subs)
                for event_type, subs in self._subscribers.items()
            },
        }


# ============================================================================
# Global Event Bus Instance
# ============================================================================

# The global event bus is a convenience for simple use cases.
# For testing or complex scenarios, create your own EventBus instance.
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance.

    Creates one if it doesn't exist. Use this for production code.
    For tests, create a fresh EventBus instance instead.

    Returns:
        The global EventBus instance
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """Reset the global event bus. Primarily for testing."""
    global _global_event_bus
    if _global_event_bus is not None:
        _global_event_bus.clear()
    _global_event_bus = None


# Convenience functions for the global bus
def emit(event: Event) -> None:
    """Emit an event to the global event bus."""
    get_event_bus().emit(event)


def subscribe(
    event_type: Type[E],
    callback: Callable[[E], None],
) -> Callable[[], None]:
    """Subscribe to events on the global event bus."""
    return get_event_bus().subscribe(event_type, callback)
