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
