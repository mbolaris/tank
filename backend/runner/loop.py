"""Background simulation run loop.

Extracted from SimulationRunner._run_loop() verbatim. The runner keeps a thin
``_run_loop()`` facade that delegates here so the thread target and test
monkeypatch points are unchanged.

The pause gate and lock discipline are load-bearing: all stepping happens
under ``runner.lock``, and a paused world must not advance (API-driven
stepping works because SimulationRunner.step() temporarily unpauses under
the same lock).
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from core.worlds.interfaces import FAST_STEP_ACTION

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


def run_simulation_loop(runner: SimulationRunner) -> None:
    """Main simulation loop."""
    logger.info("Simulation loop: Starting")
    loop_iteration_count = 0

    # Drift correction: Track when the next frame *should* start
    next_frame_start_time = time.time()
    was_fast_forward = runner.fast_forward

    try:
        while runner.running:
            try:
                # Advance target time by one frame duration
                next_frame_start_time += runner.frame_time
                loop_iteration_count += 1

                stepped = False
                with runner.lock:
                    # Pause gate: a paused world must not advance. API-driven
                    # stepping still works because SimulationRunner.step()
                    # temporarily unpauses under this same lock.
                    if not runner.world.is_paused:
                        try:
                            runner.perf_tracker.start("update")
                            if getattr(runner.world, "supports_fast_step", False):
                                runner.world.step({FAST_STEP_ACTION: True})
                            else:
                                runner.world.step()
                            runner.perf_tracker.stop("update")
                            stepped = True
                        except Exception as e:
                            logger.error(
                                f"Simulation loop: Error updating world at frame {loop_iteration_count}: {e}",
                                exc_info=True,
                            )
                            # Continue running even if update fails

                runner._start_auto_evaluation_if_needed()

                # Yield to keep the main server thread/event loop responsive
                # (important for Ctrl+C handling under heavy simulation load).
                time.sleep(0)

                # FPS Calculation
                if stepped:
                    runner.fps_frame_count += 1
                current_time = time.time()
                if current_time - runner.last_fps_time >= 5.0:
                    runner.current_actual_fps = runner.fps_frame_count / (
                        current_time - runner.last_fps_time
                    )
                    runner.fps_frame_count = 0
                    runner.last_fps_time = current_time
                    _log_status(runner)

                # Check for mode switch that happened during step() or async
                # If we switched from Fast Forward -> Normal, we must reset the clock
                # to "now" to avoid sleeping for the accumulated drift.
                if was_fast_forward and not runner.fast_forward:
                    logger.info("Simulation loop: Fast forward disabled, resetting clock sync")
                    next_frame_start_time = time.time()

                was_fast_forward = runner.fast_forward

                # Maintain frame rate with drift correction
                if not runner.fast_forward:
                    now = time.time()
                    sleep_time = next_frame_start_time - now

                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    elif sleep_time < -0.1:  # Lagging by > 100ms
                        # We are falling too far behind, reset target to avoid "spiral of death"
                        # where we try to execute 0-delay frames forever to catch up
                        next_frame_start_time = now
                else:
                    # Even in fast-forward mode, yield occasionally so signals/shutdown remain responsive.
                    time.sleep(0)

            except Exception as e:
                logger.error(
                    f"Simulation loop: Unexpected error at frame {loop_iteration_count}: {e}",
                    exc_info=True,
                )
                # Use simple sleep on error to prevent tight loops
                time.sleep(runner.frame_time)
                # Reset timing target after error recovery
                next_frame_start_time = time.time()

    except Exception as e:
        logger.error(f"Simulation loop: Fatal error, loop exiting: {e}", exc_info=True)
    finally:
        logger.info(f"Simulation loop: Ended after {loop_iteration_count} frames")


def _log_status(runner: SimulationRunner) -> None:
    """Log the periodic simulation status line (FPS, counts, migrations, poker)."""
    # Log stats periodically
    stats = runner.world.get_stats(include_distributions=False)

    # Format perf stats if enabled
    perf_log = runner.perf_tracker.get_summary_and_reset()

    world_label = runner.world_name or runner.world_id or "Unknown World"

    # Get migration counts since last report
    from backend.transfer_history import get_and_reset_migration_counts

    migrations_in, migrations_out = get_and_reset_migration_counts(runner.world_id)
    migration_str = ""
    if migrations_in > 0 or migrations_out > 0:
        migration_str = f", Migrations=+{migrations_in}/-{migrations_out}"

    # Get poker skill snapshot; show Elo + vs-expert bb/100 to avoid saturated 99% confidence
    poker_str = ""
    if runner.evolution_benchmark_tracker is not None:
        latest = runner.evolution_benchmark_tracker.get_latest_snapshot()
        if latest is not None:
            mean_elo = getattr(latest, "pop_mean_elo", None)
            best_elo = getattr(latest, "best_elo", None)
            vs_expert_bb = getattr(latest, "pop_bb_vs_expert", None)

            if mean_elo is not None and best_elo is not None:
                poker_str = f", Poker(Elo)={mean_elo:.0f}/{best_elo:.0f}"
            if vs_expert_bb is not None:
                poker_str += f", vsExp={vs_expert_bb:.1f}bb/100"

    logger.info(
        f"{world_label} Simulation Status "
        f"FPS={runner.current_actual_fps:.1f}, "
        f"Fish={stats.get('fish_count', 0)}, "
        f"Plants={stats.get('plant_count', 0)}, "
        f"Gen={stats.get('max_generation', 0)}, "
        f"Energy={stats.get('total_energy', 0.0):.0f}"
        f"{migration_str}{poker_str}{perf_log}"
    )
