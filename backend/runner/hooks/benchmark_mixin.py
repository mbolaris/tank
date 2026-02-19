"""Benchmark functionality mixin for world hooks.

This module provides a mixin class that adds evolution benchmark tracking
functionality to world hooks.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkMixin:
    """Mixin that provides evolution benchmark tracking functionality.

    Add this mixin to any hooks class that needs to support
    evolution benchmark tracking.

    Attributes:
        evolution_benchmark_tracker: The benchmark tracker instance.
        _evolution_benchmark_guard: Thread lock for benchmark operations.
        _evolution_benchmark_last_completed_time: Last benchmark completion timestamp.
    """

    evolution_benchmark_tracker: Any | None = None
    _evolution_benchmark_guard: threading.Lock | None = None
    _evolution_benchmark_last_completed_time: float = 0.0

    def setup_benchmark_tracker(self, runner: Any) -> None:
        """Setup evolution benchmark tracker if enabled.

        Args:
            runner: The SimulationRunner instance
        """
        if os.getenv("TANK_EVOLUTION_BENCHMARK_ENABLED", "1").strip().lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            return

        try:
            from core.poker.evaluation.evolution_benchmark_tracker import EvolutionBenchmarkTracker

            # Write to shared benchmarks directory
            export_path = (
                Path("data") / "benchmarks" / f"poker_evolution_{runner.world_id[:8]}.json"
            )
            self.evolution_benchmark_tracker = EvolutionBenchmarkTracker(
                eval_interval_frames=int(
                    os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_FRAMES", "27000")
                ),
                export_path=export_path,
                use_quick_benchmark=True,
            )
            self._evolution_benchmark_guard = threading.Lock()

            initial_delay = 60.0
            interval = float(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_SECONDS", "900"))
            self._evolution_benchmark_last_completed_time = time.time() - interval + initial_delay
            logger.info(f"Evolution benchmark tracker initialized for world {runner.world_id[:8]}")
        except Exception as e:
            logger.warning(f"Failed to initialize evolution benchmark tracker: {e}")
            self.evolution_benchmark_tracker = None
            self._evolution_benchmark_guard = None

    def update_benchmark_tracker_path(self, runner: Any) -> None:
        """Update benchmark tracker export path when tank identity changes.

        Args:
            runner: The SimulationRunner instance
        """
        if self.evolution_benchmark_tracker is not None:
            export_path = (
                Path("data") / "benchmarks" / f"poker_evolution_{runner.world_id[:8]}.json"
            )
            self.evolution_benchmark_tracker.export_path = export_path

    def cleanup_benchmark_tracker(self) -> None:
        """Clean up benchmark tracker resources."""
        self.evolution_benchmark_tracker = None
        self._evolution_benchmark_guard = None
