"""Regression tests for the live-server broadcast stall (IMPROVEMENT_PROPOSALS 13.1).

The stall: ``AppContext.get_server_info`` called ``psutil.Process().cpu_percent
(interval=0.1)``, which sleeps 100 ms, from coroutines on the event loop (the
2 s discovery heartbeat and ``GET /api/servers/local``). Every WebSocket
broadcast in flight froze for that long.
"""

import asyncio
import sys
import threading
import time
import types

import pytest

from backend.app_factory import AppContext
from backend.runner.loop_lag import LoopLagMonitor, timed_lock
from backend.runner.perf_tracker import PerfTracker
from backend.world_broadcast_adapter import WorldSnapshotAdapter


class _FakeProcess:
    instances = 0

    def __init__(self):
        type(self).instances += 1
        self.intervals: list[float | None] = []

    def cpu_percent(self, interval=None):
        self.intervals.append(interval)
        if interval:
            time.sleep(interval)
        return 12.5

    def memory_info(self):
        return types.SimpleNamespace(rss=64 * 1024 * 1024)


@pytest.fixture
def fake_psutil(monkeypatch):
    _FakeProcess.instances = 0
    module = types.SimpleNamespace(Process=_FakeProcess, cpu_count=lambda logical=True: 4)
    monkeypatch.setitem(sys.modules, "psutil", module)
    return module


def test_get_server_info_never_blocks_on_cpu_sampling(fake_psutil):
    ctx = AppContext()

    for _ in range(3):
        info = ctx.get_server_info()

    assert info.cpu_percent == 12.5
    # One Process object reused, so interval=None measures since the last call.
    assert _FakeProcess.instances == 1
    assert ctx._process.intervals == [None, None, None, None]  # prime + 3 reads


def test_loop_lag_monitor_sees_a_blocked_loop():
    monitor = LoopLagMonitor(interval_s=0.005, window_s=10.0)

    async def scenario():
        task = asyncio.create_task(monitor.run())
        await asyncio.sleep(0.03)
        time.sleep(0.12)  # block the loop, as the psutil call did
        await asyncio.sleep(0.03)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    stats = monitor.percentiles()
    assert stats is not None
    assert stats[2] >= 80.0
    assert "loop_lag=" in monitor.summary()


def test_loop_lag_monitor_window_drops_old_samples():
    monitor = LoopLagMonitor(window_s=5.0)
    monitor.record(500.0, now=100.0)
    monitor.record(1.0, now=106.0)
    assert monitor.percentiles(now=106.0) == (1.0, 1.0, 1.0)
    assert LoopLagMonitor().summary() == ""


def test_timed_lock_records_wait():
    tracker = PerfTracker()
    lock = threading.Lock()
    lock.acquire()
    threading.Timer(0.05, lock.release).start()

    with timed_lock(lock, tracker, "lock_wait"):
        pass

    stats = tracker.stats_for("lock_wait")
    assert stats["count"] == 1
    assert stats["max_ms"] >= 40.0
    assert "lock_wait=" in tracker.get_summary_and_reset()


def test_timed_fetch_splits_work_from_wait():
    class _Runner:
        def get_state(self, force_full=False, allow_delta=True):
            time.sleep(0.03)
            return {"force_full": force_full}

    adapter = WorldSnapshotAdapter(
        "w", _Runner(), world_type="tank", mode_id="tank", view_mode="side", step_on_access=False
    )

    state, fetch = asyncio.run(adapter.get_state_timed_async(force_full=True, allow_delta=False))

    assert state == {"force_full": True}
    assert fetch.work_ms >= 25.0
    assert fetch.queue_ms >= 0.0 and fetch.resume_ms >= 0.0
