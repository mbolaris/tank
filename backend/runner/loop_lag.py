"""Event-loop lag probe and lock-wait timing for the live server.

The broadcast loop's ``SLOW`` warnings could not say *why* a broadcast was
slow: time spent waiting for the event loop, for the executor, or for the
simulation lock all landed in the same ``get``/``send`` numbers. These helpers
separate them (IMPROVEMENT_PROPOSALS.md 13.1).

``LoopLagMonitor`` is a task that sleeps a fixed interval and records how late
it wakes up. Anything that blocks the event loop - synchronous work inside a
coroutine, or the loop thread starving for the GIL - shows up as lag here,
independently of any particular broadcast. On Windows the selector loop's
timer resolution is ~15.6 ms, so a p50 of several milliseconds is the platform
floor; the max is the number that matters.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.runner.perf_tracker import PerfTracker

PROBE_INTERVAL_S = 0.02
WINDOW_S = 5.0


class LoopLagMonitor:
    """Record how late an event loop wakes from a fixed-interval sleep."""

    def __init__(self, interval_s: float = PROBE_INTERVAL_S, window_s: float = WINDOW_S):
        self._interval_s = interval_s
        self._window_s = window_s
        self._samples: deque[tuple[float, float]] = deque()
        self._lock = threading.Lock()
        self._task: asyncio.Task | None = None

    def record(self, lag_ms: float, now: float | None = None) -> None:
        """Record one lag sample (thread-safe) and drop samples outside the window."""
        now = time.perf_counter() if now is None else now
        with self._lock:
            self._samples.append((now, lag_ms))
            cutoff = now - self._window_s
            while self._samples and self._samples[0][0] < cutoff:
                self._samples.popleft()

    def percentiles(self, now: float | None = None) -> tuple[float, float, float] | None:
        """Return (p50, p99, max) lag in ms over the window, or None if no samples."""
        now = time.perf_counter() if now is None else now
        cutoff = now - self._window_s
        with self._lock:
            lags = sorted(lag for t, lag in self._samples if t >= cutoff)
        if not lags:
            return None
        return (
            lags[len(lags) // 2],
            lags[min(len(lags) - 1, int(len(lags) * 0.99))],
            lags[-1],
        )

    def summary(self) -> str:
        """Status-line fragment, e.g. `` loop_lag=p50 5.1 p99 14.8 max 96.2ms``."""
        stats = self.percentiles()
        if stats is None:
            return ""
        p50, p99, worst = stats
        return f" loop_lag=p50 {p50:.1f} p99 {p99:.1f} max {worst:.1f}ms"

    async def run(self) -> None:
        """Probe forever; cancel the task to stop."""
        while True:
            start = time.perf_counter()
            await asyncio.sleep(self._interval_s)
            now = time.perf_counter()
            self.record(max(0.0, (now - start - self._interval_s) * 1000.0), now)

    def ensure_running(self) -> None:
        """Start the probe on the running loop once; later calls are no-ops.

        Disabled with ``TANK_LOOP_LAG_PROBE=0``.
        """
        if os.getenv("TANK_LOOP_LAG_PROBE", "1").strip().lower() in ("0", "false", "off"):
            return
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.get_running_loop().create_task(self.run(), name="loop_lag_probe")


LOOP_LAG = LoopLagMonitor()


@contextmanager
def timed_lock(lock: threading.Lock, tracker: PerfTracker, name: str) -> Iterator[None]:
    """Acquire ``lock``, recording the wait under ``name`` in ``tracker``."""
    start = time.perf_counter()
    with lock:
        tracker.record(name, (time.perf_counter() - start) * 1000.0)
        yield
