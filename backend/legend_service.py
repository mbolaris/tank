"""The seam that joins legend criteria to the legend store (U8b/E6).

``SimulationRunner`` owns one per world. It mirrors the story-event service:
a fixed frame cadence, replayed frames ignored, and criterion state persisted
alongside the records so a restored world neither loses its legends nor
re-crowns anybody.

Legends are evaluated far less often than story events. Nothing here is
time-critical — a legend is a fact about a whole history, not a moment — and
the sample walks the living population, so a slow cadence keeps it free.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from backend.legend_criteria import LegendCriteriaConfig, LegendCriteriaSuite, LegendSample
from backend.legends import DEFAULT_MAX_LEGENDS, SCHEMA_VERSION, LegendStore

logger = logging.getLogger(__name__)

# Every 600 frames = every 20 seconds at the default 30 FPS.
DEFAULT_EVALUATE_INTERVAL_FRAMES = 600


class LegendService:
    """Store + criteria for one world, on a frame-driven cadence."""

    def __init__(
        self,
        world_id: str | None = None,
        max_legends: int = DEFAULT_MAX_LEGENDS,
        evaluate_interval_frames: int = DEFAULT_EVALUATE_INTERVAL_FRAMES,
        config: LegendCriteriaConfig | None = None,
    ) -> None:
        self.store = LegendStore(world_id=world_id, max_legends=max_legends)
        self.criteria = LegendCriteriaSuite(config)
        self.evaluate_interval_frames = max(1, int(evaluate_interval_frames))
        self.last_evaluated_frame = 0
        self._lock = threading.Lock()

    @property
    def world_id(self) -> str:
        return self.store.world_id

    @world_id.setter
    def world_id(self, value: str) -> None:
        self.store.world_id = value

    @property
    def schema_version(self) -> int:
        return self.store.schema_version

    def is_evaluation_due(self, frame: int) -> bool:
        return frame > self.last_evaluated_frame and frame % self.evaluate_interval_frames == 0

    def observe(self, sample: LegendSample) -> list[dict[str, Any]]:
        """Run the criteria and store whatever they promote.

        Samples at or before the last evaluated frame are ignored, so replaying
        a frame cannot double-promote — and the store's dedup set catches the
        rest.
        """
        with self._lock:
            if sample.frame <= self.last_evaluated_frame:
                return []
            self.last_evaluated_frame = sample.frame
            stored = (self.store.add(legend) for legend in self.criteria.evaluate(sample))
            return [record for record in stored if record is not None]

    def recent(
        self,
        limit: int | None = None,
        since_id: int | None = None,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.store.recent(limit=limit, since_id=since_id, kind=kind)

    def clear(self) -> int:
        return self.store.clear()

    def to_payload(self) -> dict[str, Any]:
        payload = self.store.to_payload()
        payload["evaluate_interval_frames"] = self.evaluate_interval_frames
        payload["last_evaluated_frame"] = self.last_evaluated_frame
        payload["criteria"] = self.criteria.to_payload()
        return payload

    def load(self, payload: dict[str, Any] | None) -> None:
        """Restore legends and criterion state, or stay empty if unreadable."""
        if not self.store.load(payload):
            return
        assert payload is not None  # store.load only returns True for a real dict
        try:
            self.evaluate_interval_frames = max(
                1, int(payload.get("evaluate_interval_frames", self.evaluate_interval_frames))
            )
            self.last_evaluated_frame = int(payload.get("last_evaluated_frame", 0) or 0)
            self.criteria.load(payload.get("criteria"))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "LegendService: failed to restore criterion state (%s); "
                "criteria start fresh but stored legends are kept.",
                exc,
            )


__all__ = ["DEFAULT_EVALUATE_INTERVAL_FRAMES", "SCHEMA_VERSION", "LegendService"]
