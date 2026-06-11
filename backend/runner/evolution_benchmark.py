"""Evolution benchmark scheduling and API data access.

Extracted from SimulationRunner verbatim. The runner keeps thin facades
(``_run_evolution_benchmark_if_needed``, ``get_evolution_benchmark_data``,
``get_full_evaluation_history``) that delegate here, so test monkeypatch
points and the public API are unchanged.

The benchmark itself runs in a background thread; reads of the fish
population and reward application happen under ``runner.lock``.
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


def run_evolution_benchmark_if_needed(runner: SimulationRunner) -> None:
    """Run evolution benchmark if interval has passed.

    The benchmark runs in a background thread to avoid blocking the main loop.
    Results are used to track poker skill evolution over generations.
    """
    tracker = getattr(runner, "evolution_benchmark_tracker", None)
    if tracker is None:
        return
    current_frame = runner.world.frame_count

    paused_only = os.getenv("TANK_EVOLUTION_BENCHMARK_PAUSED_ONLY", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if paused_only and not getattr(runner.world, "paused", False):
        return

    interval_seconds = float(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_SECONDS", "900"))
    now = time.time()
    last_completed = float(getattr(runner, "_evolution_benchmark_last_completed_time", 0.0) or 0.0)
    if now - last_completed < interval_seconds:
        return

    guard = getattr(runner, "_evolution_benchmark_guard", None)
    if guard is None:
        return

    if guard.acquire(blocking=False):
        # Run benchmark in background thread to avoid blocking
        import threading

        def run_benchmark():
            try:
                with runner.lock:
                    # Use snapshot_type for generic entity classification
                    fish_list = [
                        e
                        for e in runner.world.entities_list
                        if getattr(e, "snapshot_type", None) == "fish"
                    ]

                def apply_reward(fish, amount: float) -> None:
                    with runner.lock:
                        # Ensure fish is still valid/alive in the simulation
                        if fish in runner.world.entities_list:
                            actual_gain = fish.modify_energy(amount)
                            if actual_gain > 0 and fish.ecosystem is not None:
                                # We reuse the auto_eval metric for tracking
                                fish.ecosystem.record_auto_eval_energy_gain(actual_gain)
                            logger.info(
                                f"Benchmark Reward: Fish #{fish.fish_id} ({getattr(fish, 'generation', 0)}) gained {actual_gain:.1f} energy"
                            )

                tracker.run_and_record(
                    fish_population=fish_list,
                    current_frame=current_frame,
                    force=True,
                    reward_callback=apply_reward,
                )
            except Exception as e:
                logger.error(f"Evolution benchmark failed: {e}", exc_info=True)
            finally:
                runner._evolution_benchmark_last_completed_time = time.time()
                try:
                    guard.release()
                except Exception:
                    pass

        thread = threading.Thread(
            target=run_benchmark,
            name="evolution_benchmark_thread",
            daemon=True,
        )
        thread.start()


def get_full_evaluation_history(runner: SimulationRunner) -> list[dict[str, Any]]:
    """Return the full auto-evaluation history."""
    # Delegates to world hooks or manager if available
    tracker = getattr(runner.world_hooks, "evolution_benchmark_tracker", None)
    if tracker:
        history = getattr(tracker, "history", None)
        if isinstance(history, list):
            return cast(list[dict[str, Any]], history)
    return []


def get_evolution_benchmark_data(runner: SimulationRunner) -> dict[str, Any]:
    """Return the evolution benchmark tracking data.

    Returns:
        Dictionary with benchmark history, improvement metrics, and latest snapshot.
        Returns empty dict with status if tracker not available.
    """
    tracker = getattr(runner.world_hooks, "evolution_benchmark_tracker", None)
    if tracker is not None:
        data = tracker.get_api_data()
        if isinstance(data, dict):
            return cast(dict[str, Any], data)
        return {}

    status = "disabled"
    # Check if it was meant to be enabled
    if os.getenv("TANK_EVOLUTION_BENCHMARK_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        status = "initializing_or_failed"

    return {"status": status}
