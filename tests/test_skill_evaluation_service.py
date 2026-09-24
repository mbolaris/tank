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


# --- Process-isolated evaluation -------------------------------------------
# The Observatory's evaluation is ~60 s of pure Python per world per refresh;
# in a thread it shares one GIL with every live world. These evaluators are
# module-level so a spawned worker process can import them by name.


def _report_process(snapshot: dict[str, object]) -> dict[str, object]:
    import os

    return {"status": "success", "pid": os.getpid(), "snapshot": snapshot}


def _die_in_worker_process(snapshot: dict[str, object]) -> dict[str, object]:
    import multiprocessing
    import os

    if multiprocessing.parent_process() is not None:
        os._exit(1)  # simulate the worker being killed mid-evaluation
    return {"status": "success", "pid": os.getpid(), "snapshot": snapshot}


def _report_process_slowly(snapshot: "_MarkedSnapshot") -> dict[str, object]:
    import time

    Path(snapshot.started_marker).touch()  # the worker is initialized and evaluating
    time.sleep(1.0)
    return _report_process(snapshot)  # type: ignore[arg-type]


class _Snapshot:
    """Not a dict, so the service hands it to the evaluator."""

    def __init__(self, world_id: str) -> None:
        self.world_id = world_id


class _MarkedSnapshot(_Snapshot):
    def __init__(self, world_id: str, started_marker: str) -> None:
        super().__init__(world_id)
        self.started_marker = started_marker


def _service_with(evaluator, snapshot_builder=_Snapshot) -> SkillEvaluationService:  # type: ignore[no-untyped-def]
    service = SkillEvaluationService(_WorldManager("tank-a"))
    service.set_snapshot_builder(snapshot_builder)
    service.set_evaluator(evaluator, in_subprocess=True)
    return service


@pytest.mark.asyncio
async def test_snapshot_evaluation_can_run_in_a_separate_process() -> None:
    import os

    service = _service_with(_report_process)
    try:
        result = await service.refresh_world("tank-a")
        assert result is not None
        assert result["pid"] != os.getpid()
        assert result["snapshot"].world_id == "tank-a"  # type: ignore[attr-defined]
        pool = service._process_pool
        assert pool is not None
        workers = list(pool._processes.values())  # type: ignore[attr-defined]
    finally:
        await service.stop()
    assert service._process_pool is None
    for worker in workers:
        worker.join(timeout=10)
        assert not worker.is_alive(), "stop() must not leave the worker running"


@pytest.mark.asyncio
async def test_a_dead_worker_is_replaced_at_the_next_refresh() -> None:
    import os

    service = _service_with(_die_in_worker_process)
    try:
        # The worker dies mid-evaluation: keep the last result (none yet) and
        # do not fall back to a thread, which would reintroduce the contention.
        assert await service.refresh_world("tank-a") is None
        assert service._process_pool is None

        service.set_evaluator(_report_process, in_subprocess=True)
        result = await service.refresh_world("tank-a")
        assert result is not None
        assert result["pid"] != os.getpid()
    finally:
        await service.stop()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not hasattr(__import__("signal"), "SIGINT") or __import__("os").name == "nt",
    reason="POSIX signal delivery",
)
async def test_ctrl_c_reaching_the_worker_does_not_escape_into_the_server(tmp_path: Path) -> None:
    """A terminal Ctrl+C reaches the whole process group; the worker must
    leave shutdown to the server instead of raising KeyboardInterrupt back
    through the future into the event loop."""
    import os
    import signal

    marker = tmp_path / "started"
    service = _service_with(
        _report_process_slowly, lambda world_id: _MarkedSnapshot(world_id, str(marker))
    )
    try:
        refresh = asyncio.create_task(service.refresh_world("tank-a"))
        for _ in range(400):  # wait until the evaluation is under way
            if marker.exists():
                break
            await asyncio.sleep(0.05)
        assert marker.exists(), "the worker never started the evaluation"
        workers = list(service._process_pool._processes.values())  # type: ignore[union-attr]
        os.kill(workers[0].pid, signal.SIGINT)
        result = await refresh
        assert result is not None
        assert result["pid"] == workers[0].pid
    finally:
        await service.stop()
