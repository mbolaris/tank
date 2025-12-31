"""Tests for the EventBus domain event dispatch system."""

import pytest

from core.events import EventBus
from core.events.domain_events import (
    EntityAteFoodEvent,
    EntityDiedEvent,
    EnergyTransferredEvent,
)


class TestEventBus:
    """Test suite for EventBus functionality."""

    def test_emit_reaches_subscriber(self) -> None:
        """Verify events are delivered to subscribed handlers."""
        bus = EventBus()
        received_events: list = []

        def handler(event: EntityAteFoodEvent) -> None:
            received_events.append(event)

        bus.subscribe(EntityAteFoodEvent, handler)

        event = EntityAteFoodEvent(
            entity_id=42,
            food_type="nectar",
            energy_gained=10.0,
            algorithm_id=1,
            frame=100,
        )
        bus.emit(event)

        assert len(received_events) == 1
        assert received_events[0] is event
        assert received_events[0].entity_id == 42

    def test_no_subscribers_no_crash(self) -> None:
        """Verify emitting with no subscribers is safe and has minimal overhead."""
        bus = EventBus()

        # Should not raise any exception
        event = EntityAteFoodEvent(
            entity_id=1,
            food_type="falling_food",
            energy_gained=5.0,
            algorithm_id=0,
            frame=50,
        )
        bus.emit(event)  # No subscribers - should be a no-op

        # Verify the bus remains in a valid state
        assert bus.subscriber_count(EntityAteFoodEvent) == 0

    def test_multiple_handlers_same_type(self) -> None:
        """Verify multiple handlers for the same event type all receive it."""
        bus = EventBus()
        results: list = []

        def handler1(event: EntityDiedEvent) -> None:
            results.append(("h1", event.entity_id))

        def handler2(event: EntityDiedEvent) -> None:
            results.append(("h2", event.entity_id))

        bus.subscribe(EntityDiedEvent, handler1)
        bus.subscribe(EntityDiedEvent, handler2)

        event = EntityDiedEvent(
            entity_id=99,
            generation=5,
            age=100,
            reason="starvation",
            algorithm_id=10,
            remaining_energy=0.0,
            frame=200,
        )
        bus.emit(event)

        assert len(results) == 2
        assert ("h1", 99) in results
        assert ("h2", 99) in results

    def test_handler_receives_correct_type_only(self) -> None:
        """Verify handlers only receive events of their subscribed type."""
        bus = EventBus()
        ate_food_events: list = []
        died_events: list = []

        def food_handler(event: EntityAteFoodEvent) -> None:
            ate_food_events.append(event)

        def death_handler(event: EntityDiedEvent) -> None:
            died_events.append(event)

        bus.subscribe(EntityAteFoodEvent, food_handler)
        bus.subscribe(EntityDiedEvent, death_handler)

        # Emit a food event
        food_event = EntityAteFoodEvent(
            entity_id=1,
            food_type="live_food",
            energy_gained=15.0,
            algorithm_id=5,
            frame=10,
        )
        bus.emit(food_event)

        # Emit a death event
        death_event = EntityDiedEvent(
            entity_id=2,
            generation=3,
            age=50,
            reason="old_age",
            algorithm_id=7,
            remaining_energy=5.0,
            frame=20,
        )
        bus.emit(death_event)

        # Food handler should only have food events
        assert len(ate_food_events) == 1
        assert ate_food_events[0].entity_id == 1

        # Death handler should only have death events
        assert len(died_events) == 1
        assert died_events[0].entity_id == 2

    def test_unsubscribe_removes_handler(self) -> None:
        """Verify unsubscribe removes the handler from receiving events."""
        bus = EventBus()
        received: list = []

        def handler(event: EntityAteFoodEvent) -> None:
            received.append(event)

        bus.subscribe(EntityAteFoodEvent, handler)

        # Emit first event - should be received
        event1 = EntityAteFoodEvent(
            entity_id=1, food_type="nectar", energy_gained=5.0, algorithm_id=0, frame=1
        )
        bus.emit(event1)
        assert len(received) == 1

        # Unsubscribe
        removed = bus.unsubscribe(EntityAteFoodEvent, handler)
        assert removed is True

        # Emit second event - should NOT be received
        event2 = EntityAteFoodEvent(
            entity_id=2, food_type="nectar", energy_gained=5.0, algorithm_id=0, frame=2
        )
        bus.emit(event2)
        assert len(received) == 1  # Still only 1

    def test_clear_subscribers(self) -> None:
        """Verify clear_subscribers removes all handlers."""
        bus = EventBus()
        received: list = []

        bus.subscribe(EntityAteFoodEvent, lambda e: received.append(e))
        bus.subscribe(EntityDiedEvent, lambda e: received.append(e))

        assert bus.has_subscribers(EntityAteFoodEvent)
        assert bus.has_subscribers(EntityDiedEvent)

        bus.clear_subscribers()

        assert not bus.has_subscribers(EntityAteFoodEvent)
        assert not bus.has_subscribers(EntityDiedEvent)

    def test_has_subscribers(self) -> None:
        """Verify has_subscribers reports correctly."""
        bus = EventBus()

        assert not bus.has_subscribers(EntityAteFoodEvent)

        bus.subscribe(EntityAteFoodEvent, lambda e: None)

        assert bus.has_subscribers(EntityAteFoodEvent)
        assert not bus.has_subscribers(EntityDiedEvent)


class TestEventBusIntegration:
    """Integration tests for EventBus with EcosystemManager."""

    def test_ecosystem_receives_events_via_bus(self) -> None:
        """Verify EcosystemManager receives events through EventBus subscription."""
        from core.ecosystem import EcosystemManager
        from core.telemetry.events import FoodEatenEvent

        bus = EventBus()
        ecosystem = EcosystemManager(max_population=50, event_bus=bus)

        # Emit a food eaten event through the bus
        event = FoodEatenEvent(
            food_type="nectar",
            algorithm_id=1,
            energy_gained=10.0,
        )
        bus.emit(event)

        # Verify ecosystem recorded the energy gain
        assert ecosystem.energy_sources.get("nectar", 0.0) >= 10.0

    def test_ecosystem_works_without_bus(self) -> None:
        """Verify EcosystemManager works correctly without EventBus (backward compat)."""
        from core.ecosystem import EcosystemManager

        ecosystem = EcosystemManager(max_population=50)  # No event_bus

        # Direct method calls should still work
        ecosystem.record_energy_gain("nectar", 5.0)

        assert ecosystem.energy_sources.get("nectar", 0.0) >= 5.0
