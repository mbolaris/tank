"""Simulation diagnostics and reporting.

This module handles the formatting, printing, and exporting of simulation statistics.
It separates the concerns of "running the simulation" from "reporting on the simulation".
"""

import json
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)

StatsEmitter = Callable[[str], None]


def format_simulation_stats(engine: "SimulationEngine", start_time: float) -> list[str]:
    """Format current simulation statistics as console-ready lines."""
    stats = engine.get_stats()
    elapsed_time = time.time() - start_time

    lines = [
        "-" * 80,
        f"Frame: {stats.get('frame_count', 0)} | Time: {elapsed_time:.1f}s",
        f"FPS: {engine.frame_count / elapsed_time if elapsed_time > 0 else 0:.1f}",
        "-" * 80,
    ]

    max_pop = engine.ecosystem.max_population if engine.ecosystem else "N/A"
    lines.append(f"Population:      {stats.get('total_population', 0)}/{max_pop}")
    lines.append(
        f"Fish/Food/Plant: {stats.get('fish_count', 0)} / {stats.get('food_count', 0)} / {stats.get('plant_count', 0)}"
    )

    repro = stats.get("reproduction_stats", {})
    if repro:
        lines.extend(
            [
                f"Births (Total):  {stats.get('total_births', 0)}",
                f"Mating Attempts: {repro.get('total_mating_attempts', 0)}",
                f"Success Rate:    {repro.get('success_rate_pct', 'N/A')}",
            ]
        )

    deaths = stats.get("death_causes", {})
    if deaths:
        causes_str = ", ".join(f"{k}: {v}" for k, v in deaths.items())
        lines.append(f"Deaths ({stats.get('total_deaths', 0)}): {causes_str}")

    lines.append("-" * 80)
    return lines


def print_simulation_stats(
    engine: "SimulationEngine", start_time: float, emit: StatsEmitter = print
) -> None:
    """Print current simulation statistics to console.

    Args:
        engine: The simulation engine instance
        start_time: Wall-clock time when simulation started
        emit: Output sink for each formatted line
    """
    for line in format_simulation_stats(engine, start_time):
        emit(line)


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
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        logger.info("Exported stats to %s", filename)
    except (OSError, TypeError, ValueError) as exc:
        logger.error("Failed to export stats: %s", exc)
