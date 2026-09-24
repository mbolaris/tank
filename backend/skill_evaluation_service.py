"""Background evaluation service for the Tank Skill Observatory.

The observatory is intentionally asynchronous with respect to HTTP requests.
Evaluating a tank can take seconds, so the API serves the last completed result
while this service refreshes worlds in the background.
"""

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing
import signal
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from copy import deepcopy
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_EVALUATION_INTERVAL = 300.0
MAX_LATEST_RESULTS = 64


def _ignore_interrupts() -> None:
    """Worker-process initializer: leave Ctrl+C to the server.

    A terminal Ctrl+C reaches the whole process group. A worker that raised
    KeyboardInterrupt mid-evaluation would hand it back through the future and
    into the server's event loop, cutting its graceful shutdown (and the world
    saves in it) short. The server stops the worker itself in ``stop()``.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)


class SkillEvaluationService:
    """Evaluate worlds outside request handlers and retain bounded latest results."""

    def __init__(
        self,
        world_manager: Any | None,
        evaluator: Callable[[Any], dict[str, Any]] | None = None,
        *,
        snapshot_builder: Callable[[str], Any] | None = None,
        interval_seconds: float = DEFAULT_EVALUATION_INTERVAL,
        max_results: int = MAX_LATEST_RESULTS,
        storage_path: Path | None = None,
    ) -> None:
        if max_results < 1:
            raise ValueError("max_results must be positive")
        self._world_manager = world_manager
        self._evaluator = evaluator
        self._snapshot_builder = snapshot_builder
        self._interval_seconds = interval_seconds
        self._latest: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_results = max_results
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._in_flight: set[str] = set()
        self._storage_path = storage_path
        self._result_observer: Callable[[str, dict[str, Any]], None] | None = None
        self._evaluate_in_subprocess = False
        self._process_pool: ProcessPoolExecutor | None = None
        self._load_latest()

    def set_evaluator(
        self, evaluator: Callable[[Any], dict[str, Any]], *, in_subprocess: bool = False
    ) -> None:
        """Set the evaluator after router construction has provided its dependencies.

        ``in_subprocess`` runs snapshot evaluations in a separate worker process
        instead of a thread. The Observatory's evaluation is ~60 s of pure
        Python per world every refresh (the whole population turns over between
        refreshes, so its cache rarely hits), and in a thread it shares the one
        GIL with every live world and the broadcaster: world fps fell and
        broadcasts stalled for minutes at a time. The evaluator must then be a
        picklable, module-level function, and the snapshot picklable.

        When a snapshot builder is also set (see ``set_snapshot_builder``), the
        evaluator receives that builder's snapshot object instead of a world_id
        string, and runs in a worker (thread or process) only after the snapshot has already
        been captured synchronously - it must not read live simulation state.
        """
        self._evaluator = evaluator
        self._evaluate_in_subprocess = in_subprocess

    def set_snapshot_builder(self, snapshot_builder: Callable[[str], Any]) -> None:
        """Set a synchronous, world_id -> snapshot builder run before evaluation.

        Runs on the caller's own thread (never inside the background worker),
        so every live read of simulation state happens at one consistent
        instant. It may itself return a status ``dict`` (e.g. ``{"status":
        "no_data", ...}``) to short-circuit evaluation entirely - the returned
        object is only handed to the evaluator when it is not a ``dict``.
        """
        self._snapshot_builder = snapshot_builder

    def get_latest(self, world_id: str) -> dict[str, Any] | None:
        """Return a copy of the latest completed result for ``world_id``."""
        result = self._latest.get(world_id)
        return deepcopy(result) if result is not None else None

    def set_result_observer(self, observer: Callable[[str, dict[str, Any]], None] | None) -> None:
        """Register a callback notified of every completed result.

        This service keeps only the *latest* result per world, which is all the
        observatory panel needs but is not enough to say whether foraging is
        improving. The observer is the seam where something that wants a series
        can retain one, without this class growing a second responsibility.
        """
        self._result_observer = observer

    def store_result(self, world_id: str, result: dict[str, Any]) -> None:
        """Store a completed result, evicting the least-recently-updated world."""
        self._latest.pop(world_id, None)
        self._latest[world_id] = deepcopy(result)
        while len(self._latest) > self._max_results:
            self._latest.popitem(last=False)
        self._persist_latest()
        if self._result_observer is not None:
            # A misbehaving observer must not lose the stored result or stop
            # the evaluation loop that called this.
            try:
                self._result_observer(world_id, deepcopy(result))
            except Exception:  # pragma: no cover - defensive
                logger.warning("Skill result observer failed", exc_info=True)

    async def refresh_world(self, world_id: str) -> dict[str, Any] | None:
        """Evaluate one world off the event loop and store its completed result.

        When a snapshot builder is configured, it runs synchronously first, on
        this coroutine's own thread, so the worker thread never reads live
        simulation state - only the immutable snapshot it was handed.
        """
        if self._evaluator is None or world_id in self._in_flight:
            return self.get_latest(world_id)

        self._in_flight.add(world_id)
        try:
            if self._snapshot_builder is not None:
                snapshot = self._snapshot_builder(world_id)
                if isinstance(snapshot, dict):
                    result = snapshot
                else:
                    result = await self._evaluate_snapshot(snapshot)
            else:
                result = await asyncio.to_thread(self._evaluator, world_id)
            self.store_result(world_id, result)
            return deepcopy(result)
        except BrokenProcessPool:
            # The worker died (e.g. Ctrl+C reaches the whole process group).
            # Keep the last result; the next refresh starts a fresh worker.
            # Not falling back to a thread is deliberate: that is the GIL
            # contention the worker exists to avoid, and at shutdown it would
            # hold the process open for the length of an evaluation.
            self._shutdown_process_pool()
            if self._running:
                logger.warning("Skill evaluation worker died while evaluating %s", world_id)
            return self.get_latest(world_id)
        except Exception:
            logger.exception("Skill evaluation failed for world %s", world_id)
            return self.get_latest(world_id)
        finally:
            self._in_flight.discard(world_id)

    async def _evaluate_snapshot(self, snapshot: Any) -> dict[str, Any]:
        assert self._evaluator is not None
        if self._evaluate_in_subprocess:
            pool = self._get_process_pool()
            if pool is not None:
                loop = asyncio.get_running_loop()
                result: dict[str, Any] = await loop.run_in_executor(pool, self._evaluator, snapshot)
                return result
        return await asyncio.to_thread(self._evaluator, snapshot)

    def _get_process_pool(self) -> ProcessPoolExecutor | None:
        if self._process_pool is None:
            try:
                # spawn, never fork: forking copies whatever locks the live
                # simulation threads hold at that instant (logging's included).
                self._process_pool = ProcessPoolExecutor(
                    max_workers=1,
                    mp_context=multiprocessing.get_context("spawn"),
                    initializer=_ignore_interrupts,
                )
            except (OSError, ValueError, NotImplementedError):
                logger.warning(
                    "Could not start a skill evaluation process; using threads",
                    exc_info=True,
                )
                self._evaluate_in_subprocess = False
        return self._process_pool

    def _shutdown_process_pool(self) -> None:
        pool, self._process_pool = self._process_pool, None
        if pool is None:
            return
        # A worker can be minutes into an evaluation; don't make shutdown wait.
        processes = list(getattr(pool, "_processes", {}).values())
        pool.shutdown(wait=False, cancel_futures=True)
        for process in processes:
            if process.is_alive():
                process.terminate()

    async def start(self) -> None:
        """Start periodic world evaluation, including an initial refresh."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="skill_evaluation")

    async def stop(self) -> None:
        """Stop periodic evaluation and wait for the task to exit."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._shutdown_process_pool()

    async def _run_loop(self) -> None:
        try:
            while self._running:
                # Refresh worlds one at a time rather than via asyncio.gather:
                # each refresh_world call spawns a worker thread, and evaluators
                # (e.g. the Observatory's genome-fingerprint cache) may share
                # process-wide mutable state that isn't safe to touch from
                # multiple worker threads at once. Evaluation already runs on
                # a slow, periodic interval, so sequential refreshes cost
                # little while fully avoiding that concurrency hazard.
                for world_id in self._world_ids():
                    await self.refresh_world(world_id)
                await asyncio.sleep(self._interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Skill evaluation loop stopped unexpectedly")

    def _world_ids(self) -> list[str]:
        if self._world_manager is None:
            return []
        return [instance.world_id for instance in self._world_manager.list_worlds()]

    def _load_latest(self) -> None:
        if self._storage_path is None or not self._storage_path.is_file():
            return
        try:
            saved = json.loads(self._storage_path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                for world_id, result in saved.items():
                    if isinstance(world_id, str) and isinstance(result, dict):
                        self._latest[world_id] = result
                while len(self._latest) > self._max_results:
                    self._latest.popitem(last=False)
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not load skill evaluation results from %s", self._storage_path)

    def _persist_latest(self) -> None:
        if self._storage_path is None:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self._storage_path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(self._latest, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            temporary_path.replace(self._storage_path)
        except OSError:
            logger.warning("Could not persist skill evaluation results to %s", self._storage_path)
