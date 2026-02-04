from __future__ import annotations

from dataclasses import dataclass

from backend.connection_manager import ConnectionManager, TankConnection
from backend.migration_handler import MigrationHandler
from backend.world_manager import WorldManager


@dataclass
class DummyEntity:
    entity_id: int

    def get_entity_id(self) -> int:
        return self.entity_id


def _make_connections() -> list[TankConnection]:
    return [
        TankConnection(
            id="conn-a",
            source_world_id="world-src",
            destination_world_id="world-b",
            probability=25,
            direction="left",
        ),
        TankConnection(
            id="conn-b",
            source_world_id="world-src",
            destination_world_id="world-a",
            probability=25,
            direction="left",
        ),
        TankConnection(
            id="conn-c",
            source_world_id="world-src",
            destination_world_id="world-c",
            probability=25,
            direction="left",
        ),
    ]


def _make_handler() -> MigrationHandler:
    return MigrationHandler(connection_manager=ConnectionManager(), world_manager=WorldManager())


def test_migration_selection_stable_for_seed_and_entity() -> None:
    handler = _make_handler()
    entity = DummyEntity(entity_id=7)
    connections = _make_connections()

    first = handler._select_connection(connections, entity, "world-src", "left", 12345)
    shuffled = list(reversed(connections))
    second = handler._select_connection(shuffled, entity, "world-src", "left", 12345)

    assert first.id == second.id


def test_migration_selection_changes_with_seed() -> None:
    handler = _make_handler()
    entity = DummyEntity(entity_id=7)
    connections = _make_connections()

    seed_1 = handler._select_connection(connections, entity, "world-src", "left", 11)
    seed_2 = handler._select_connection(connections, entity, "world-src", "left", 99)

    assert seed_1.id != seed_2.id
