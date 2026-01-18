"""State publisher for simulation runner."""

import logging
from typing import Any, Dict, List, Optional, Union

import orjson

from backend.runner.perf_tracker import PerfTracker
from backend.state_payloads import DeltaStatePayload, EntitySnapshot, FullStatePayload

logger = logging.getLogger(__name__)


class StatePublisher:
    """Handles state caching, throttling, and serialization."""

    def __init__(
        self,
        perf_tracker: PerfTracker,
        websocket_update_interval: int = 2,
        delta_sync_interval: int = 90,
    ):
        self.perf_tracker = perf_tracker
        self.websocket_update_interval = websocket_update_interval
        self.delta_sync_interval = delta_sync_interval

        # Cache state
        self._cached_state: Optional[Union[FullStatePayload, DeltaStatePayload]] = None
        self._cached_state_frame: Optional[int] = None
        self._frames_since_update = 0

        # Delta sync state
        self._last_full_frame: Optional[int] = None
        self._last_entities: Dict[int, EntitySnapshot] = {}

    def invalidate_cache(self) -> None:
        """Invalidate the current cache to force a rebuild."""
        self._cached_state = None
        self._cached_state_frame = None
        self._frames_since_update = 0
        self._last_full_frame = None
        self._last_entities.clear()

    def get_state(
        self, runner: Any, force_full: bool = False, allow_delta: bool = True
    ) -> Union[FullStatePayload, DeltaStatePayload]:
        """Get the current state payload, utilizing caching and delta compression."""

        current_frame = runner.world.frame_count

        # 1. Fast path: Return cached frame if we have it
        if self._cached_state is not None and current_frame == self._cached_state_frame:
            return self._cached_state

        # 2. Throttling: Skip updates if not enough time passed (unless forced or stopped)
        self._frames_since_update += 1
        should_rebuild = (
            force_full
            or not runner.running
            or self._frames_since_update >= self.websocket_update_interval
        )

        if not should_rebuild and self._cached_state is not None:
            return self._cached_state

        self._frames_since_update = 0

        # 3. Build new state
        # Decide if we need a full update
        is_full_update = (
            force_full
            or not allow_delta
            or self._last_full_frame is None
            or (current_frame - self._last_full_frame) >= self.delta_sync_interval
        )

        # Collect data
        # Note: We rely on runner providing these methods.
        # Ideally these would be extracted too, but one step at a time.

        # Calculate derived elapsed time if needed
        elapsed_time = current_frame * 33  # fallback
        engine = getattr(runner.world, "engine", None)
        if engine and hasattr(engine, "elapsed_time"):
            elapsed_time = engine.elapsed_time
        elif hasattr(runner.world, "world") and hasattr(runner.world.world, "engine"):
            # TankWorldBackendAdapter -> world -> engine
            if hasattr(runner.world.world.engine, "elapsed_time"):
                elapsed_time = runner.world.world.engine.elapsed_time

        # Stats
        self.perf_tracker.start("stats")
        stats = runner._collect_stats(current_frame, include_distributions=is_full_update)
        self.perf_tracker.stop("stats")

        # Entities
        self.perf_tracker.start("snapshot")
        entity_snapshots = runner._collect_entities()
        self.perf_tracker.stop("snapshot")

        if is_full_update:
            state = self._build_full_state(
                runner, current_frame, elapsed_time, stats, entity_snapshots
            )
            self._last_full_frame = current_frame
            self._last_entities = {e.id: e for e in entity_snapshots}
        else:
            state = self._build_delta_state(
                runner, current_frame, elapsed_time, stats, entity_snapshots
            )
            # Update entity usage tracking for next delta
            self._last_entities = {e.id: e for e in entity_snapshots}

        # Cache it
        self._cached_state = state
        self._cached_state_frame = current_frame

        return state

    def serialize_state(self, state: Union[FullStatePayload, DeltaStatePayload]) -> bytes:
        """Serialize state to bytes."""
        self.perf_tracker.start("serialize")

        payload = state.to_dict() if hasattr(state, "to_dict") else state
        serialized = orjson.dumps(payload)

        duration_ms = self.perf_tracker.stop("serialize")

        if duration_ms > 50:
            frame = getattr(state, "frame", "unknown")
            logger.warning(
                "serialize_state: Frame %s slow serialization: %.2f ms, Size: %d bytes",
                frame,
                duration_ms,
                len(serialized),
            )

        return serialized

    def _build_full_state(
        self, runner: Any, frame: int, elapsed_time: Any, stats: Any, entities: List[EntitySnapshot]
    ) -> FullStatePayload:
        """Construct a FullStatePayload."""

        # Gather extras from hooks
        try:
            extras = runner.world_hooks.build_world_extras(runner)
        except Exception as e:
            logger.warning(f"Error building world extras from hooks: {e}")
            extras = {}

        # Default extras if missing
        poker_events = extras.get("poker_events", [])
        soccer_events = extras.get("soccer_events", [])
        soccer_league_live = extras.get("soccer_league_live", None)
        poker_leaderboard = extras.get("poker_leaderboard", [])
        auto_eval = extras.get("auto_evaluation", None)

        return FullStatePayload(
            frame=frame,
            elapsed_time=elapsed_time,
            entities=entities,
            stats=stats,
            poker_events=poker_events,
            soccer_events=soccer_events,
            soccer_league_live=soccer_league_live,
            auto_evaluation=auto_eval,
            world_id=runner.world_id,
            poker_leaderboard=poker_leaderboard,
            mode_id=runner.mode_id,
            world_type=runner.world_type,
            view_mode=runner.view_mode,
        )

    def _build_delta_state(
        self, runner: Any, frame: int, elapsed_time: Any, stats: Any, entities: List[EntitySnapshot]
    ) -> DeltaStatePayload:
        """Construct a DeltaStatePayload."""

        current_entities_map = {e.id: e for e in entities}

        added = [
            entity.to_full_dict()
            for eid, entity in current_entities_map.items()
            if eid not in self._last_entities
        ]

        removed = [eid for eid in self._last_entities if eid not in current_entities_map]

        updates = [e.to_delta_dict() for e in entities]

        # Extras from hooks (lean version)
        # We might want to skip building expensive extras for deltas
        # Currently runner logic was: "soccer_league_live" is included in delta,
        # but poker_events/soccer_events are NOT.

        try:
            # Optimization: We could ask hooks for "delta extras" specifically
            # For now, we'll manually pull what we know we need if we want to mimic exact behavior
            # The existing logic was:
            # soccer_league_live = self._collect_soccer_league_live()
            # everything else skipped

            # But calling build_world_extras might be expensive?
            # Let's trust build_world_extras is fast enough or refactor later.
            # Wait, existing logic explicitly excluded events from delta to save bandwidth.
            # We should replicate that.

            # If we call build_world_extras(), we get everything.
            # We can just pick what we want.

            extras = runner.world_hooks.build_world_extras(runner)
        except Exception:
            extras = {}

        soccer_league_live = extras.get("soccer_league_live", None)

        return DeltaStatePayload(
            frame=frame,
            elapsed_time=elapsed_time,
            updates=updates,
            added=added,
            removed=removed,
            stats=stats,
            # Explicitly omitted events as per original logic
            soccer_league_live=soccer_league_live,
            world_id=runner.world_id,
            mode_id=runner.mode_id,
            world_type=runner.world_type,
            view_mode=runner.view_mode,
        )
