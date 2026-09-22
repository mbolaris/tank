"""On-disk state survives crashes and stops pointing at worlds that are gone.

Both failures were read off a real server log:

- ``Failed to read snapshot snapshot_...json: Expecting property name ... line
  120714`` - a snapshot cut off mid-write, because saves truncated the file
  and then filled it in. It was re-read and re-warned about on every start.
- ``Migration failed: world not found`` every couple of seconds - a connection
  between two deleted worlds, reloaded from ``connections.json`` at each start
  because deleting a world only forgot its connections in memory.

The autouse ``mock_data_dir`` fixture points every file here at a temp dir.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.connection_persistence as cp
import backend.world_persistence as wp
from backend.atomic_json import CORRUPT_PREFIX, quarantine_if_corrupt, write_json_atomic
from backend.connection_manager import ConnectionManager, TankConnection
from backend.connection_persistence import (
    load_connections,
    prune_stale_connections,
    save_connections,
)
from backend.world_manager import WorldManager


class _Unserializable:
    """Makes ``json.dump`` fail partway through, after it has written output."""


def _snapshot(frame: int) -> dict:
    return {"world_id": "w", "frame": frame, "entities": [{"type": "food"}] * 3}


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------


def test_atomic_write_round_trips_and_leaves_no_temp_file(tmp_path: Path) -> None:
    target = tmp_path / "atomic" / "state.json"
    target.parent.mkdir()
    write_json_atomic(target, {"a": 1})
    assert json.loads(target.read_text()) == {"a": 1}
    assert list(target.parent.iterdir()) == [target]


def test_failed_write_keeps_the_previous_file_intact(tmp_path: Path) -> None:
    # This is the crash the server log shows: json.dump dies after it has
    # already streamed most of the document out.
    target = tmp_path / "atomic" / "state.json"
    target.parent.mkdir()
    write_json_atomic(target, {"good": True})

    with pytest.raises(TypeError):
        write_json_atomic(target, {"big": list(range(1000)), "bad": _Unserializable()})

    assert json.loads(target.read_text()) == {"good": True}
    assert list(target.parent.iterdir()) == [target], "the temp file must be cleaned up"


def test_snapshot_save_interrupted_mid_write_keeps_the_last_good_snapshot() -> None:
    first = wp.save_snapshot_data("w", {**_snapshot(100), "saved_at": "2026-09-19T15:40:00"})
    assert first is not None

    broken = {**_snapshot(200), "saved_at": "2026-09-19T15:41:18", "x": _Unserializable()}
    assert wp.save_snapshot_data("w", broken) is None

    listed = wp.list_world_snapshots("w")
    assert [s["frame"] for s in listed] == [100]
    assert wp.get_latest_snapshot("w") == first
    snapshot_dir = Path(first).parent
    assert not list(snapshot_dir.glob("*.tmp"))
    # The failed save never produced a file the next start could trip over.
    assert not (snapshot_dir / "snapshot_20260919_154118.json").exists()


def test_connections_save_is_atomic() -> None:
    manager = ConnectionManager()
    manager.add_connection(TankConnection("a->b", "a", "b", 25))
    assert save_connections(manager)
    assert json.loads(cp.CONNECTIONS_FILE.read_text())["connections"][0]["id"] == "a->b"
    assert not list(cp.CONNECTIONS_FILE.parent.glob("*.tmp"))


# ---------------------------------------------------------------------------
# Corrupt snapshot quarantine
# ---------------------------------------------------------------------------


def test_truncated_snapshot_is_quarantined_and_the_older_one_restores() -> None:
    older = wp.save_snapshot_data("w", {**_snapshot(100), "saved_at": "2026-09-19T15:30:00"})
    assert older is not None
    snapshot_dir = Path(older).parent
    truncated = snapshot_dir / "snapshot_20260919_154118.json"
    full = json.dumps(_snapshot(200), indent=2)
    truncated.write_text(full[: len(full) // 2])

    assert wp.get_latest_snapshot("w") == older
    assert not truncated.exists()
    assert (snapshot_dir / f"{CORRUPT_PREFIX}{truncated.name}").exists(), "kept for inspection"

    # The next start no longer sees it at all, so it stops warning.
    assert [s["frame"] for s in wp.list_world_snapshots("w")] == [100]


def test_quarantine_ignores_io_errors(tmp_path: Path) -> None:
    # A file briefly locked by another process says nothing about its contents.
    path = tmp_path / "snapshot_1.json"
    path.write_text("{}")
    assert quarantine_if_corrupt(path, PermissionError("locked")) is None
    assert path.exists()


def test_quarantine_renames_parse_failures(tmp_path: Path) -> None:
    path = tmp_path / "snapshot_1.json"
    path.write_text("{")
    moved = quarantine_if_corrupt(path, json.JSONDecodeError("x", "{", 1))
    assert moved == tmp_path / f"{CORRUPT_PREFIX}snapshot_1.json"
    assert moved.exists() and not path.exists()


# ---------------------------------------------------------------------------
# Stale connections
# ---------------------------------------------------------------------------


def _world_manager_holding(*world_ids: str) -> list[SimpleNamespace]:
    """Anything iterable over objects with ``world_id`` stands in for WorldManager."""
    return [SimpleNamespace(world_id=world_id) for world_id in world_ids]


def _write_connections(*connections: TankConnection) -> None:
    manager = ConnectionManager()
    for connection in connections:
        manager.add_connection(connection)
    assert save_connections(manager)


def _saved_ids() -> set[str]:
    return {c["id"] for c in json.loads(cp.CONNECTIONS_FILE.read_text())["connections"]}


def test_startup_prunes_connections_between_deleted_worlds_and_rewrites_the_file() -> None:
    # The pair from the log: both ends deleted, both directions saved.
    _write_connections(
        TankConnection("dead-r", "e3f153cb", "54f8d29c", 25, "right"),
        TankConnection("dead-l", "54f8d29c", "e3f153cb", 25, "left"),
        TankConnection("live", "959876b1", "a3220f7c", 25, "right"),
    )

    manager = ConnectionManager()
    restored = load_connections(manager, _world_manager_holding("959876b1", "a3220f7c"))

    assert restored == 1
    assert [c.id for c in manager.list_connections()] == ["live"]
    assert _saved_ids() == {"live"}, "pruning must persist or it returns on every start"


def test_startup_keeps_connections_that_reach_another_server() -> None:
    _write_connections(
        TankConnection(
            "remote",
            "959876b1",
            "elsewhere",
            25,
            source_server_id="local-server",
            destination_server_id="other-server",
        ),
    )

    manager = ConnectionManager()
    restored = load_connections(manager, _world_manager_holding("959876b1"), "local-server")

    assert restored == 1
    assert _saved_ids() == {"remote"}


def test_startup_treats_connections_stamped_with_this_server_as_local() -> None:
    _write_connections(
        TankConnection(
            "stamped",
            "gone-a",
            "gone-b",
            25,
            source_server_id="local-server",
            destination_server_id="local-server",
        ),
    )

    manager = ConnectionManager()
    assert load_connections(manager, _world_manager_holding(), "local-server") == 0
    assert _saved_ids() == set()


def test_load_without_a_world_manager_does_not_prune() -> None:
    # Pruning before worlds are restored would delete every live link.
    _write_connections(TankConnection("x", "a", "b", 25))
    manager = ConnectionManager()
    assert load_connections(manager) == 1
    assert _saved_ids() == {"x"}


def test_prune_with_nothing_stale_does_not_touch_the_file() -> None:
    manager = ConnectionManager()
    manager.add_connection(TankConnection("x", "a", "b", 25))
    assert prune_stale_connections(manager, ["a", "b"]) == 0
    assert not cp.CONNECTIONS_FILE.exists()


def test_prune_tolerates_no_connection_manager() -> None:
    assert prune_stale_connections(None, []) == 0


def test_deleting_a_world_persists_the_connection_removal() -> None:
    connections = ConnectionManager()
    world_manager = WorldManager()
    world_manager.set_connection_manager(connections)
    tank_a = world_manager.create_world(name="Tank A", world_type="tank", persistent=False)
    tank_b = world_manager.create_world(name="Tank B", world_type="tank", persistent=False)
    try:
        connections.add_connection(TankConnection("a->b", tank_a.world_id, tank_b.world_id, 25))
        connections.add_connection(TankConnection("b->a", tank_b.world_id, tank_a.world_id, 25))
        assert save_connections(connections)

        assert world_manager.delete_world(tank_a.world_id)

        assert connections.list_connections() == []
        assert _saved_ids() == set(), "a restart must not bring the deleted world's links back"
    finally:
        world_manager.delete_world(tank_b.world_id)
