"""The seam that joins story detectors to the story-event store.

``SimulationRunner`` owns one of these per world. The runner hands it a
:class:`~backend.story_detectors.StorySample` on a fixed frame cadence; the
service runs the detectors, numbers whatever they emit, and keeps the whole
thing (events *and* detector latches) in a single persistable payload so a
restored world neither loses its history nor re-announces it.

Detection cadence is a frame count, never wall-clock time or client activity, so
the same run always produces the same events regardless of how many browsers
happen to be watching.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from backend.story_detectors import StoryDetectorConfig, StoryDetectorSuite, StorySample
from backend.story_events import DEFAULT_MAX_EVENTS, SCHEMA_VERSION, StoryEventStore

logger = logging.getLogger(__name__)

# Every 120 frames = every 4 seconds at the default 30 FPS. Frequent enough that
# a collapsing population is announced while it still reads as news, cheap
# enough that the per-sample scan is invisible next to a simulation step.
DEFAULT_DETECT_INTERVAL_FRAMES = 120


class StoryEventService:
    """Store + detectors for one world, with a frame-driven detection cadence."""

    def __init__(
        self,
        world_id: str | None = None,
        max_events: int = DEFAULT_MAX_EVENTS,
        detect_interval_frames: int = DEFAULT_DETECT_INTERVAL_FRAMES,
        config: StoryDetectorConfig | None = None,
    ) -> None:
        self.store = StoryEventStore(world_id=world_id, max_events=max_events)
        self.detectors = StoryDetectorSuite(config)
        self.detect_interval_frames = max(1, int(detect_interval_frames))
        self.last_observed_frame = 0
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

    def is_detection_due(self, frame: int) -> bool:
        """Whether ``frame`` lands on a detection boundary and is new."""
        return frame > self.last_observed_frame and frame % self.detect_interval_frames == 0

    def observe(self, sample: StorySample) -> list[dict[str, Any]]:
        """Run the detectors on ``sample`` and store whatever they emit.

        Samples at or before the last observed frame are ignored, so replaying a
        frame — on a restore, a resync, or a duplicated call — cannot duplicate
        events.
        """
        with self._lock:
            if sample.frame <= self.last_observed_frame:
                return []
            self.last_observed_frame = sample.frame
            emitted = self.detectors.observe(sample)
            return [self.store.add(event) for event in emitted]

    def recent(
        self,
        limit: int | None = None,
        since_id: int | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.store.recent(limit=limit, since_id=since_id, event_type=event_type)

    def clear(self) -> int:
        return self.store.clear()

    def to_payload(self) -> dict[str, Any]:
        payload = self.store.to_payload()
        payload["detect_interval_frames"] = self.detect_interval_frames
        payload["last_observed_frame"] = self.last_observed_frame
        payload["detectors"] = self.detectors.to_payload()
        return payload

    def load(self, payload: dict[str, Any] | None) -> None:
        """Restore events and detector latches, or stay empty if unreadable.

        The store decides whether the payload is readable; when it refuses (an
        unknown ``schema_version``) the detector latches are left untouched too,
        so the service starts genuinely fresh rather than half-restored.
        """
        if not self.store.load(payload):
            return
        assert payload is not None  # store.load only returns True for a real dict
        try:
            self.detect_interval_frames = max(
                1, int(payload.get("detect_interval_frames", self.detect_interval_frames))
            )
            self.last_observed_frame = int(payload.get("last_observed_frame", 0) or 0)
            self.detectors.load(payload.get("detectors"))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "StoryEventService: failed to restore detector state (%s); "
                "detectors start fresh but stored events are kept.",
                exc,
            )


__all__ = [
    "DEFAULT_DETECT_INTERVAL_FRAMES",
    "SCHEMA_VERSION",
    "StoryEventService",
]
