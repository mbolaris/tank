"""Background evaluation service for the Tank Skill Observatory.

The observatory is intentionally asynchronous with respect to HTTP requests.
Evaluating a tank can take seconds, so the API serves the last completed result
while this service refreshes worlds in the background.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_EVALUATION_INTERVAL = 300.0
MAX_LATEST_RESULTS = 64


class SkillEvaluationService:
    """Evaluate worlds outside request handlers and retain bounded latest results."""

    def __init__(
        self,
        world_manager: Any | None,
        evaluator: Callable[[str], dict[str, Any]] | None = None,
        *,
        interval_seconds: float = DEFAULT_EVALUATION_INTERVAL,
        max_results: int = MAX_LATEST_RESULTS,
        storage_path: Path | None = None,
    ) -> None:
        if max_results < 1:
            raise ValueError("max_results must be positive")
        self._world_manager = world_manager
        self._evaluator = evaluator
        self._interval_seconds = interval_seconds
        self._latest: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_results = max_results
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._in_flight: set[str] = set()
        self._storage_path = storage_path
        self._load_latest()

    def set_evaluator(self, evaluator: Callable[[str], dict[str, Any]]) -> None:
        """Set the evaluator after router construction has provided its dependencies."""
        self._evaluator = evaluator

    def get_latest(self, world_id: str) -> dict[str, Any] | None:
        """Return a copy of the latest completed result for ``world_id``."""
        result = self._latest.get(world_id)
        return deepcopy(result) if result is not None else None

    def store_result(self, world_id: str, result: dict[str, Any]) -> None:
        """Store a completed result, evicting the least-recently-updated world."""
        self._latest.pop(world_id, None)
        self._latest[world_id] = deepcopy(result)
        while len(self._latest) > self._max_results:
            self._latest.popitem(last=False)
        self._persist_latest()

    async def refresh_world(self, world_id: str) -> dict[str, Any] | None:
        """Evaluate one world in a worker thread and store its completed result."""
        if self._evaluator is None or world_id in self._in_flight:
            return self.get_latest(world_id)

        self._in_flight.add(world_id)
        try:
            result = await asyncio.to_thread(self._evaluator, world_id)
            self.store_result(world_id, result)
            return deepcopy(result)
        except Exception:
            logger.exception("Skill evaluation failed for world %s", world_id)
            return self.get_latest(world_id)
        finally:
            self._in_flight.discard(world_id)

    async def start(self) -> None:
        """Start periodic world evaluation, including an initial refresh."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="skill_evaluation")

    async def stop(self) -> None:
        """Stop periodic evaluation and wait for the task to exit."""
        self._running = False
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run_loop(self) -> None:
        try:
            while self._running:
                world_ids = self._world_ids()
                await asyncio.gather(*(self.refresh_world(world_id) for world_id in world_ids))
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
