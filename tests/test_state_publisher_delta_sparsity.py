"""Tests for sparse websocket delta construction and publisher telemetry."""

from __future__ import annotations

from unittest.mock import Mock

from backend.runner.state_publisher import StatePublisher
from backend.state_payloads import EntitySnapshot


def _publisher() -> StatePublisher:
    return StatePublisher(Mock(), websocket_update_interval=1, delta_sync_interval=100)


def _runner() -> Mock:
    runner = Mock()
    runner.world_hooks.build_world_extras.return_value = {}
    runner.metrics_history = None
    return runner


def test_delta_contains_only_entities_with_changed_delta_fields():
    publisher = _publisher()
    unchanged = EntitySnapshot(1, "fish", 10.0, 20.0, 4.0, 4.0)
    moved = EntitySnapshot(2, "fish", 10.0, 20.0, 4.0, 4.0)
    publisher._last_entities = {1: unchanged, 2: moved}

    state = publisher._build_delta_state(
        _runner(),
        frame=2,
        elapsed_time=66,
        stats={},
        entities=[unchanged, EntitySnapshot(2, "fish", 11.0, 20.0, 4.0, 4.0)],
    )

    assert state.added == []
    assert state.removed == []
    assert [update["id"] for update in state.updates] == [2]
    assert publisher.delta_metrics() == {
        "frames": 1,
        "entities_total": 2,
        "entities_changed": 1,
        "entities_added": 0,
        "entities_removed": 0,
        "bytes": 0,
    }


def test_duplicate_wire_ids_are_reported_once_per_id(caplog):
    """A colliding id silently drops an entity from the delta - say so loudly."""
    publisher = _publisher()
    reef = EntitySnapshot(5_000_001, "algae_reef", 217.6, 452.9, 148.0, 106.0)
    ball = EntitySnapshot(5_000_001, "ball", 347.6, 303.0, 20.0, 20.0)
    publisher._last_entities = {5_000_001: reef}

    for frame in (2, 3):
        with caplog.at_level("ERROR", logger="backend.runner.state_publisher"):
            publisher._build_delta_state(
                _runner(), frame=frame, elapsed_time=66, stats={}, entities=[reef, ball]
            )

    duplicate_logs = [rec for rec in caplog.records if "Duplicate entity wire id" in rec.message]
    assert len(duplicate_logs) == 1
    assert "algae_reef, ball" in duplicate_logs[0].getMessage()


def test_added_entities_use_full_payload_without_duplicate_delta_update():
    publisher = _publisher()
    existing = EntitySnapshot(1, "fish", 10.0, 20.0, 4.0, 4.0)
    publisher._last_entities = {1: existing}

    state = publisher._build_delta_state(
        _runner(),
        frame=2,
        elapsed_time=66,
        stats={},
        entities=[existing, EntitySnapshot(2, "food", 3.0, 4.0, 2.0, 2.0)],
    )

    assert [entity["id"] for entity in state.added] == [2]
    assert state.updates == []
    assert publisher.delta_metrics()["entities_added"] == 1
