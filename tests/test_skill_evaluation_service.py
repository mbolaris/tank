"""Tests for the asynchronous observatory evaluation boundary."""

import asyncio
from pathlib import Path

import pytest

from backend.skill_evaluation_service import SkillEvaluationService


class _World:
    def __init__(self, world_id: str) -> None:
        self.world_id = world_id


class _WorldManager:
    def __init__(self, *world_ids: str) -> None:
        self._worlds = [_World(world_id) for world_id in world_ids]

    def list_worlds(self) -> list[_World]:
        return list(self._worlds)


@pytest.mark.asyncio
async def test_refresh_world_evaluates_outside_request_and_copies_result() -> None:
    calls: list[tuple[str, str]] = []

    def evaluator(world_id: str) -> dict[str, object]:
        calls.append((world_id, threading_name()))
        return {"status": "success", "world_id": world_id, "values": [1]}

    service = SkillEvaluationService(_WorldManager("tank-a"), evaluator)
    result = await service.refresh_world("tank-a")

    assert result is not None
    assert result["world_id"] == "tank-a"
    assert calls[0][0] == "tank-a"
    assert calls[0][1] != "MainThread"

    result["values"].append(2)  # type: ignore[union-attr]
    assert service.get_latest("tank-a")["values"] == [1]  # type: ignore[index]


def threading_name() -> str:
    import threading

    return threading.current_thread().name


@pytest.mark.asyncio
async def test_service_refreshes_all_worlds_and_bounds_latest_results() -> None:
    service = SkillEvaluationService(
        _WorldManager("tank-a", "tank-b"),
        lambda world_id: {"status": "success", "world_id": world_id},
        max_results=1,
    )

    await service.start()
    await asyncio.sleep(0.02)
    await service.stop()

    assert service.get_latest("tank-a") is None
    assert service.get_latest("tank-b")["world_id"] == "tank-b"  # type: ignore[index]


@pytest.mark.asyncio
async def test_get_latest_is_empty_until_background_evaluation_completes() -> None:
    service = SkillEvaluationService(
        _WorldManager("tank-a"),
        lambda world_id: {"status": "success", "world_id": world_id},
    )

    assert service.get_latest("tank-a") is None
    await service.refresh_world("tank-a")
    assert service.get_latest("tank-a")["status"] == "success"  # type: ignore[index]


def test_latest_result_can_be_reloaded_from_storage(tmp_path: Path) -> None:
    storage_path = tmp_path / "latest.json"
    result = {"status": "success", "world_id": "tank-a", "evaluated_at_frame": 10}

    writer = SkillEvaluationService(None, storage_path=storage_path)
    writer.store_result("tank-a", result)

    reader = SkillEvaluationService(None, storage_path=storage_path)
    assert reader.get_latest("tank-a") == result


@pytest.mark.asyncio
async def test_snapshot_builder_short_circuit_never_spawns_a_worker_thread() -> None:
    """When the snapshot builder itself returns a status dict (e.g. the world
    isn't ready to evaluate), that dict is the final result - the evaluator
    must never run, so no worker thread is spawned for it."""
    evaluator_calls: list[str] = []

    def snapshot_builder(world_id: str) -> dict[str, object]:
        return {"status": "no_data", "world_id": world_id, "message": "not ready"}

    def evaluator(snapshot: object) -> dict[str, object]:
        evaluator_calls.append("called")
        return {"status": "success"}

    service = SkillEvaluationService(
        _WorldManager("tank-a"), evaluator, snapshot_builder=snapshot_builder
    )
    result = await service.refresh_world("tank-a")

    assert result == {"status": "no_data", "world_id": "tank-a", "message": "not ready"}
    assert evaluator_calls == []


@pytest.mark.asyncio
async def test_snapshot_builder_passes_its_snapshot_to_evaluator_on_worker_thread() -> None:
    """A non-dict snapshot builder result is handed to the evaluator, which
    still runs outside the caller's own thread."""
    received: list[tuple[object, str]] = []

    class _Snapshot:
        world_id = "tank-a"

    snapshot = _Snapshot()

    def snapshot_builder(world_id: str) -> _Snapshot:
        assert world_id == "tank-a"
        return snapshot

    def evaluator(snap: object) -> dict[str, object]:
        received.append((snap, threading_name()))
        return {"status": "success", "world_id": snap.world_id}  # type: ignore[attr-defined]

    service = SkillEvaluationService(
        _WorldManager("tank-a"), evaluator, snapshot_builder=snapshot_builder
    )
    result = await service.refresh_world("tank-a")

    assert result == {"status": "success", "world_id": "tank-a"}
    assert received[0][0] is snapshot
    assert received[0][1] != "MainThread"


@pytest.mark.asyncio
async def test_run_loop_refreshes_worlds_sequentially_not_concurrently() -> None:
    """Evaluators may share process-wide mutable state (e.g. the Observatory's
    genome-fingerprint cache), so the periodic loop must never have two
    worlds' evaluators running at the same time."""
    concurrent_count = 0
    max_concurrent = 0

    def evaluator(world_id: str) -> dict[str, object]:
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        try:
            import time

            time.sleep(0.01)
            return {"status": "success", "world_id": world_id}
        finally:
            concurrent_count -= 1

    service = SkillEvaluationService(
        _WorldManager("tank-a", "tank-b", "tank-c"), evaluator, interval_seconds=10.0
    )

    await service.start()
    await asyncio.sleep(0.2)
    await service.stop()

    assert max_concurrent == 1
    assert service.get_latest("tank-a") is not None
    assert service.get_latest("tank-b") is not None
    assert service.get_latest("tank-c") is not None
