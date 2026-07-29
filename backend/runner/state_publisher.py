"""State publisher for simulation runner."""

import logging
from typing import Any

import orjson

from backend.runner.perf_tracker import PerfTracker
from backend.state_payloads import DeltaStatePayload, EntitySnapshot, FullStatePayload

logger = logging.getLogger(__name__)


class StatePublisher:
    """Handles state caching, throttling, and serialization."""

    def __init__(
        self,
        perf_tracker: PerfTracker,
        websocket_update_interval: int = 1,
        delta_sync_interval: int = 90,
    ):
        self.perf_tracker = perf_tracker
        self.websocket_update_interval = websocket_update_interval
        self.delta_sync_interval = delta_sync_interval

        # Cache state
        self._cached_state: FullStatePayload | DeltaStatePayload | None = None
        self._cached_state_frame: int | None = None
        self._frames_since_update = 0

        # Delta sync state
        self._last_full_frame: int | None = None
        self._last_entities: dict[int, EntitySnapshot] = {}
        # Cache of last frame's to_delta_dict() output, keyed by entity id, so
        # _build_delta_state doesn't have to re-derive it from the stored
        # EntitySnapshot every frame - see _build_delta_state's comment.
        self._last_delta_dicts: dict[int, dict[str, Any]] = {}
        # Wire ids already reported as colliding, so the warning fires once per
        # id rather than on every delta frame.
        self._reported_duplicate_ids: set[int] = set()
        self._delta_metrics = {
            "frames": 0,
            "entities_total": 0,
            "entities_changed": 0,
            "entities_added": 0,
            "entities_removed": 0,
            "bytes": 0,
        }

    def invalidate_cache(self) -> None:
        """Invalidate the current cache to force a rebuild."""
        self._cached_state = None
        self._cached_state_frame = None
        self._frames_since_update = 0
        self._last_full_frame = None
        self._last_entities.clear()
        self._last_delta_dicts.clear()
        self._reported_duplicate_ids.clear()
        for key in self._delta_metrics:
            self._delta_metrics[key] = 0

    def delta_metrics(self) -> dict[str, int]:
        """Return wire-level counters for the most recently published deltas."""
        return dict(self._delta_metrics)

    def get_state(
        self, runner: Any, force_full: bool = False, allow_delta: bool = True
    ) -> FullStatePayload | DeltaStatePayload:
        """Get the current state payload, utilizing caching and delta compression."""

        current_frame = runner.world.frame_count

        # 1. Fast path: Return cached frame if we have it.
        #
        # A caller that asked for full state must never be handed a cached
        # *delta*. Newly connected clients take this path (websocket.py sends
        # force_full=True, allow_delta=False on connect), and a delta is
        # meaningless to a client with no prior state: it carries only changed
        # positions, with no entity types, sizes or render hints. Serving one
        # left the tank rendered but inert - nothing could be hit-tested or
        # selected - and only when the connect happened to land on a frame
        # whose cached payload was a delta, which made it look intermittent.
        # GET /api/worlds/{id}/snapshot was silently broken the same way.
        cached = self._cached_state
        wants_full = force_full or not allow_delta
        if (
            cached is not None
            and current_frame == self._cached_state_frame
            and not (wants_full and isinstance(cached, DeltaStatePayload))
        ):
            return cached

        # 2. Throttling: Skip updates if not enough time passed (unless forced or stopped)
        self._frames_since_update += 1
        should_rebuild = (
            wants_full
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

        state: FullStatePayload | DeltaStatePayload
        if is_full_update:
            state = self._build_full_state(
                runner,
                current_frame,
                elapsed_time,
                stats,
                entity_snapshots,
                include_metrics_history=force_full or not allow_delta,
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

    def serialize_state(self, state: FullStatePayload | DeltaStatePayload) -> bytes:
        """Serialize state to bytes."""
        self.perf_tracker.start("serialize")

        payload = state.to_dict() if hasattr(state, "to_dict") else state
        serialized = orjson.dumps(payload)

        duration_ms = self.perf_tracker.stop("serialize")

        if isinstance(state, DeltaStatePayload):
            self._delta_metrics["bytes"] = len(serialized)
            logger.debug(
                "delta frame=%s entities=%d changed=%d added=%d removed=%d bytes=%d",
                state.frame,
                self._delta_metrics["entities_total"],
                self._delta_metrics["entities_changed"],
                self._delta_metrics["entities_added"],
                self._delta_metrics["entities_removed"],
                len(serialized),
            )

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
        self,
        runner: Any,
        frame: int,
        elapsed_time: Any,
        stats: Any,
        entities: list[EntitySnapshot],
        include_metrics_history: bool = True,
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
        soccer_league_live = extras.get("soccer_league_live")
        poker_leaderboard = extras.get("poker_leaderboard", [])
        auto_eval = extras.get("auto_evaluation")

        # Get tank soccer enabled state from config
        tank_soccer_enabled = self._get_tank_soccer_enabled(runner)

        # Build metrics history payload if available
        metrics_history_payload = None
        if (
            include_metrics_history
            and hasattr(runner, "metrics_history")
            and runner.metrics_history is not None
        ):
            from backend.state_payloads import (
                MetricsHistoryPayload,
                MetricsPokerSamplePayload,
                MetricsSamplePayload,
                MetricsSoccerSamplePayload,
            )

            samples = []
            for s in runner.metrics_history.samples:
                samples.append(
                    MetricsSamplePayload(
                        frame=s["frame"],
                        max_generation=s["max_generation"],
                        population=s["population"],
                        births_total=s["births_total"],
                        deaths_total=s["deaths_total"],
                        fish_energy=s["fish_energy"],
                        poker=MetricsPokerSamplePayload(**s["poker"]),
                        soccer=MetricsSoccerSamplePayload(**s["soccer"]),
                        diversity_score=s.get("diversity_score", 0.0),
                        traits=s.get("traits", {}),
                    )
                )

            metrics_history_payload = MetricsHistoryPayload(
                schema_version=runner.metrics_history.schema_version,
                world_id=runner.metrics_history.world_id,
                sample_interval_frames=runner.metrics_history.sample_interval_frames,
                max_samples=runner.metrics_history.max_samples,
                samples=samples,
                selection_quality=runner.metrics_history.to_payload().get("selection_quality"),
            )

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
            tank_soccer_enabled=tank_soccer_enabled,
            metrics_history=metrics_history_payload,
        )

    def _report_duplicate_entity_ids(self, entities: list[EntitySnapshot]) -> None:
        """Log wire ids claimed by more than one entity, once per id."""
        by_id: dict[int, list[str]] = {}
        for entity in entities:
            by_id.setdefault(entity.id, []).append(entity.type)
        for entity_id, types in by_id.items():
            if len(types) < 2 or entity_id in self._reported_duplicate_ids:
                continue
            self._reported_duplicate_ids.add(entity_id)
            logger.error(
                "Duplicate entity wire id %s shared by %s - deltas will be wrong "
                "for all but one of them",
                entity_id,
                ", ".join(sorted(types)),
            )

    def _build_delta_state(
        self, runner: Any, frame: int, elapsed_time: Any, stats: Any, entities: list[EntitySnapshot]
    ) -> DeltaStatePayload:
        """Construct a DeltaStatePayload."""

        current_entities_map = {e.id: e for e in entities}
        if len(current_entities_map) != len(entities):
            # Two entities claiming one wire id is always an identity-provider
            # bug. The map silently keeps whichever came last, so the loser
            # stops receiving deltas while the client - which applies updates
            # by id alone - drags it onto the winner's position.
            self._report_duplicate_entity_ids(entities)

        added = [
            entity.to_full_dict()
            for eid, entity in current_entities_map.items()
            if eid not in self._last_entities
        ]

        removed = [eid for eid in self._last_entities if eid not in current_entities_map]

        # Compare the fields that are actually present in a delta payload.
        # Comparing complete snapshots would make unrelated backend changes
        # (for example energy updates) defeat wire-level sparsity.
        #
        # previous_delta normally comes from _last_delta_dicts (this frame's
        # dicts, cached below, become next frame's "previous" for free) so
        # to_delta_dict() runs once per entity per frame instead of twice. The
        # to_delta_dict() fallback only fires the first delta frame after a
        # full-state frame (which doesn't populate this cache) or when a
        # caller has set _last_entities without going through get_state().
        new_delta_dicts: dict[int, dict[str, Any]] = {}
        updates = []
        for eid, entity in current_entities_map.items():
            current_delta = entity.to_delta_dict()
            new_delta_dicts[eid] = current_delta
            previous = self._last_entities.get(eid)
            if previous is None:
                continue
            previous_delta = self._last_delta_dicts.get(eid)
            if previous_delta is None:
                previous_delta = previous.to_delta_dict()
            if current_delta != previous_delta:
                updates.append(current_delta)
        self._last_delta_dicts = new_delta_dicts

        self._delta_metrics["frames"] += 1
        self._delta_metrics["entities_total"] = len(current_entities_map)
        self._delta_metrics["entities_changed"] = len(updates)
        self._delta_metrics["entities_added"] = len(added)
        self._delta_metrics["entities_removed"] = len(removed)

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

        soccer_league_live = extras.get("soccer_league_live")

        # Get tank soccer enabled state from config
        tank_soccer_enabled = self._get_tank_soccer_enabled(runner)

        # Build new metrics sample if taken on this frame
        new_metrics_sample_payload = None
        if hasattr(runner, "metrics_history") and runner.metrics_history is not None:
            if (
                runner.metrics_history.samples
                and runner.metrics_history.samples[-1]["frame"] == frame
            ):
                from backend.state_payloads import (
                    MetricsPokerSamplePayload,
                    MetricsSamplePayload,
                    MetricsSoccerSamplePayload,
                )

                s = runner.metrics_history.samples[-1]
                new_metrics_sample_payload = MetricsSamplePayload(
                    frame=s["frame"],
                    max_generation=s["max_generation"],
                    population=s["population"],
                    births_total=s["births_total"],
                    deaths_total=s["deaths_total"],
                    fish_energy=s["fish_energy"],
                    poker=MetricsPokerSamplePayload(**s["poker"]),
                    soccer=MetricsSoccerSamplePayload(**s["soccer"]),
                    diversity_score=s.get("diversity_score", 0.0),
                    traits=s.get("traits", {}),
                    death_causes=s.get("death_causes", {}),
                )

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
            tank_soccer_enabled=tank_soccer_enabled,
            new_metrics_sample=new_metrics_sample_payload,
        )

    def _get_tank_soccer_enabled(self, runner: Any) -> bool | None:
        """Get the tank_practice_enabled state from the soccer config."""
        try:
            engine = getattr(runner.world, "engine", None)
            if engine is None:
                return None
            config = getattr(engine, "config", None)
            if config is None:
                return None
            soccer_cfg = getattr(config, "soccer", None)
            if soccer_cfg is None:
                return None
            value = getattr(soccer_cfg, "tank_practice_enabled", None)
            return value if isinstance(value, bool) else None
        except Exception:
            return None
