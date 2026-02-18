"""Synchronous event bus for domain event dispatch.

The EventBus provides a lightweight, synchronous pub/sub mechanism for
decoupling domain logic from telemetry and statistics recording.

Design goals:
- Zero overhead when no subscribers (single dict lookup)
- Synchronous for determinism and fast in simulation hot paths
- Type-safe dispatch via event type
"""

from __future__ import annotations

from collections import defaultdict
from typing import TypeVar
from collections.abc import Callable

T = TypeVar("T")


class EventBus:
    """Synchronous event bus for domain events.

    Events are dispatched immediately to all registered handlers.
    With no subscribers, emit() is essentially a no-op (dict lookup only).

    Example:
        bus = EventBus()
        bus.subscribe(EntityDiedEvent, handle_death)
        bus.emit(EntityDiedEvent(entity_id=42, reason="starvation", frame=100))
    """

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._handlers: dict[type, list[Callable]] = defaultdict(list)
        self._pending: list[object] = []

    def emit(self, event: object) -> None:
        """Emit an event to all registered handlers.

        Handlers are called synchronously in registration order.
        If no handlers are registered for this event type, this is a no-op.

        Args:
            event: The domain event to dispatch
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type)
        if handlers:
            for handler in handlers:
                handler(event)

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Register a handler for a specific event type.

        Handlers are called in registration order when events of this
        type are emitted.

        Args:
            event_type: The event class to subscribe to
            handler: Callable that receives the event instance
        """
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[T], handler: Callable[[T], None]) -> bool:
        """Remove a handler for a specific event type.

        Args:
            event_type: The event class to unsubscribe from
            handler: The handler to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)
            return True
        return False

    def clear_subscribers(self) -> None:
        """Remove all registered handlers.

        Useful for testing or resetting the bus between simulations.
        """
        self._handlers.clear()

    def has_subscribers(self, event_type: type) -> bool:
        """Check if any handlers are registered for an event type.

        Args:
            event_type: The event class to check

        Returns:
            True if at least one handler is registered
        """
        return bool(self._handlers.get(event_type))

    def subscriber_count(self, event_type: type) -> int:
        """Get the number of handlers registered for an event type.

        Args:
            event_type: The event class to check

        Returns:
            Number of registered handlers
        """
        return len(self._handlers.get(event_type, []))
