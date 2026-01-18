"""Performance tracking for the simulation runner."""

import time
from typing import Dict, TypedDict


class PerfStats(TypedDict):
    count: int
    total_ms: float
    max_ms: float
    last_log: float


class PerfTracker:
    """Tracks performance statistics for named operations."""

    def __init__(self, enable_logging: bool = True):
        self._enable_logging = enable_logging
        self._stats: Dict[str, PerfStats] = {}
        self._starts: Dict[str, float] = {}

    def start(self, name: str) -> None:
        """Start timing an operation."""
        if not self._enable_logging:
            return
        self._starts[name] = time.perf_counter()

    def stop(self, name: str) -> float:
        """Stop timing an operation and record stats.

        Returns:
            Duration in milliseconds
        """
        if not self._enable_logging:
            return 0.0

        start_time = self._starts.pop(name, None)
        if start_time is None:
            return 0.0

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if name not in self._stats:
            self._stats[name] = {"count": 0, "total_ms": 0.0, "max_ms": 0.0, "last_log": 0.0}

        stat = self._stats[name]
        stat["count"] += 1
        stat["total_ms"] += duration_ms
        if duration_ms > stat["max_ms"]:
            stat["max_ms"] = duration_ms

        return duration_ms

    def get_summary_and_reset(self) -> str:
        """Get a loggable summary string of all stats and reset them."""
        if not self._enable_logging:
            return ""

        parts = []
        for name, stat in self._stats.items():
            if stat["count"] > 0:
                avg_ms = stat["total_ms"] / stat["count"]
                parts.append(f"{name}={avg_ms:.1f}ms(max {stat['max_ms']:.1f})")

                # Reset
                stat["count"] = 0
                stat["total_ms"] = 0.0
                stat["max_ms"] = 0.0

        if not parts:
            return ""

        return " | " + " ".join(parts)

    def stats_for(self, name: str) -> Dict[str, float]:
        """Get current raw stats for a specific operation (peek)."""
        if name not in self._stats:
            return {"count": 0, "total_ms": 0.0, "max_ms": 0.0}
        stat = self._stats[name]
        return {
            "count": float(stat["count"]),
            "total_ms": stat["total_ms"],
            "max_ms": stat["max_ms"],
        }
