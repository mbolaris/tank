"""Simulation diagnostics and reporting.

This module handles the formatting, printing, and exporting of simulation statistics.
It separates the concerns of "running the simulation" from "reporting on the simulation".
"""

import json
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


def print_simulation_stats(engine: "SimulationEngine", start_time: float) -> None:
    """Print current simulation statistics to console.

    Args:
        engine: The simulation engine instance
        start_time: Wall-clock time when simulation started
    """
    stats = engine.get_stats()
    # We can't access config.display easily without engine type, but engine.config should work if typed as Any
    # or we can just key off stats keys.

    elapsed_time = time.time() - start_time

    print("-" * 80)
    print(f"Frame: {stats.get('frame_count', 0)} | Time: {elapsed_time:.1f}s")
    print(f"FPS: {engine.frame_count / elapsed_time if elapsed_time > 0 else 0:.1f}")
    print("-" * 80)

    # Population
    max_pop = engine.ecosystem.max_population if engine.ecosystem else "N/A"
    print(f"Population:      {stats.get('total_population', 0)}/{max_pop}")
    print(
        f"Fish/Food/Plant: {stats.get('fish_count', 0)} / {stats.get('food_count', 0)} / {stats.get('plant_count', 0)}"
    )

    # Reproduction Stats
    repro = stats.get("reproduction_stats", {})
    if repro:
        print(f"Births (Total):  {stats.get('total_births', 0)}")
        print(f"Mating Attempts: {repro.get('total_mating_attempts', 0)}")
        print(f"Success Rate:    {repro.get('success_rate_pct', 'N/A')}")

    # Deaths
    deaths = stats.get("death_causes", {})
    if deaths:
        causes_str = ", ".join(f"{k}: {v}" for k, v in deaths.items())
        print(f"Deaths ({stats.get('total_deaths', 0)}): {causes_str}")

    print("-" * 80)


def export_stats_json(engine: "SimulationEngine", filename: str, start_time: float) -> None:
    """Export comprehensive simulation statistics to JSON file.

    Args:
        engine: The simulation engine instance
        filename: Output filename
        start_time: Wall-clock time when simulation started
    """
    stats = engine.get_stats()
    stats["elapsed_time"] = time.time() - start_time

    try:
        with open(filename, "w") as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Exported stats to {filename}")
    except Exception as e:
        logger.error(f"Failed to export stats: {e}")
