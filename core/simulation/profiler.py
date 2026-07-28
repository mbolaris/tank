"""Phase profiler for measuring simulation update phases."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager


def is_profiling(engine: object) -> bool:
    """Check if profiling is enabled on the engine, screening out mock objects."""
    if engine is None:
        return False
    val = getattr(engine, "profile_phases", False)
    return isinstance(val, bool) and val


class PhaseProfiler:
    """Profiler for accumulating wall time spent in different simulation phases."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self.times: dict[str, float] = {
            "perception": 0.0,
            "decision": 0.0,
            "action": 0.0,
            "resolution": 0.0,
            "stats collection": 0.0,
            "spatial grid": 0.0,
            "poker": 0.0,
            "soccer": 0.0,
            "reproduction": 0.0,
        }

        # Context stack
        self._context_stack: list[str] = []
        self._current_context: str | None = None

        # Overlaps / components tracked per-frame to subtract from parent phases
        self._frame_perception_in_decision: float = 0.0
        self._frame_perception_in_collision: float = 0.0
        self._frame_perception_in_entity_act: float = 0.0
        self._frame_decision_in_entity_act: float = 0.0
        self._frame_rebuild_grid_in_frame_end: float = 0.0

    @contextmanager
    def context(self, name: str) -> Iterator[None]:
        """Context manager to push and pop profiling contexts."""
        if not self.enabled:
            yield
            return

        prev = self._current_context
        self._current_context = name
        self._context_stack.append(name)
        try:
            yield
        finally:
            self._context_stack.pop()
            self._current_context = prev

    def record_query(self, duration: float) -> None:
        """Record time spent in a spatial grid query."""
        if not self.enabled:
            return
        self.times["perception"] += duration
        if "decision" in self._context_stack:
            self._frame_perception_in_decision += duration
        if "collision" in self._context_stack:
            self._frame_perception_in_collision += duration
        if "entity_act" in self._context_stack:
            self._frame_perception_in_entity_act += duration

    def record_decide(self, duration: float) -> None:
        """Record decision time."""
        if not self.enabled:
            return
        self._frame_decision_in_entity_act += duration
        self.times["decision"] += duration

    def record_rebuild_grid(self, duration: float) -> None:
        """Record rebuild grid time."""
        if not self.enabled:
            return
        self._frame_rebuild_grid_in_frame_end += duration
        self.times["spatial grid"] += duration

    def start_frame(self) -> None:
        """Reset per-frame accumulators at the start of a frame."""
        self._frame_perception_in_decision = 0.0
        self._frame_perception_in_collision = 0.0
        self._frame_perception_in_entity_act = 0.0
        self._frame_decision_in_entity_act = 0.0
        self._frame_rebuild_grid_in_frame_end = 0.0

    def end_frame(self) -> None:
        """Subtract overlaps at the end of a frame to keep categories mutually exclusive."""
        if not self.enabled:
            return
        # 1. Adjust decision: subtract queries nested inside decision
        self.times["decision"] -= self._frame_perception_in_decision
        if self.times["decision"] < 0:
            self.times["decision"] = 0.0

        # 2. Adjust resolution (collision): subtract queries nested inside collision
        self.times["resolution"] -= self._frame_perception_in_collision
        if self.times["resolution"] < 0:
            self.times["resolution"] = 0.0

        # 3. Adjust stats collection (frame_end): subtract grid rebuilds nested inside frame_end
        self.times["stats collection"] -= self._frame_rebuild_grid_in_frame_end
        if self.times["stats collection"] < 0:
            self.times["stats collection"] = 0.0

    def record_entity_act(self, duration: float) -> None:
        """Record time spent in entity_act phase, resolving net action time."""
        if not self.enabled:
            return
        non_decide_queries = (
            self._frame_perception_in_entity_act - self._frame_perception_in_decision
        )
        net_action = duration - self._frame_decision_in_entity_act - max(0.0, non_decide_queries)
        self.times["action"] += max(0.0, net_action)

    def record_collision(self, duration: float) -> None:
        """Record time spent in collision phase."""
        if not self.enabled:
            return
        self.times["resolution"] += duration

    def record_reproduction(self, duration: float) -> None:
        """Record time spent in reproduction phase."""
        if not self.enabled:
            return
        self.times["reproduction"] += duration

    def record_poker(self, duration: float) -> None:
        """Record time spent in poker phase (interaction)."""
        if not self.enabled:
            return
        self.times["poker"] += duration

    def record_soccer(self, duration: float) -> None:
        """Record time spent in soccer update."""
        if not self.enabled:
            return
        self.times["soccer"] += duration

    def record_spatial_grid_update(self, duration: float) -> None:
        """Record time spent updating positions in the spatial grid."""
        if not self.enabled:
            return
        self.times["spatial grid"] += duration

    def record_frame_end(self, duration: float) -> None:
        """Record time spent in frame_end phase."""
        if not self.enabled:
            return
        self.times["stats collection"] += duration
