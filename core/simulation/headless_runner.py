"""Headless run loop - drives the engine without visualization.

Extracted from SimulationEngine.run_headless() verbatim. The engine keeps a
thin ``run_headless()`` facade that delegates here.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


def run_headless(
    engine: SimulationEngine,
    max_frames: int = 10000,
    stats_interval: int = 300,
    export_json: str | None = None,
) -> None:
    """Run the simulation in headless mode without visualization."""
    sep = engine.config.display.separator_width
    logger.info("=" * sep)
    logger.info("HEADLESS FISH TANK SIMULATION")
    logger.info("=" * sep)
    logger.info(
        f"Running for {max_frames} frames ({max_frames / engine.config.display.frame_rate:.1f} seconds of sim time)"
    )
    logger.info(f"Stats will be printed every {stats_interval} frames")
    if export_json:
        logger.info(f"Stats will be exported to: {export_json}")
    logger.info("=" * sep)

    engine.setup()

    for frame in range(max_frames):
        engine.update()

        if frame > 0 and frame % stats_interval == 0:
            engine.print_stats()

    logger.info("")
    logger.info("=" * sep)
    logger.info("SIMULATION COMPLETE - Final Statistics")
    logger.info("=" * sep)
    engine.print_stats()

    if engine.ecosystem is not None:
        logger.info("")
        logger.info("=" * sep)
        logger.info("GENERATING ALGORITHM PERFORMANCE REPORT...")
        logger.info("=" * sep)
        report = engine.ecosystem.get_algorithm_performance_report()
        logger.info(f"{report}")

        os.makedirs("logs", exist_ok=True)
        report_path = os.path.join("logs", "algorithm_performance_report.txt")
        with open(report_path, "w") as f:
            f.write(report)
        logger.info("")
        logger.info(f"Report saved to: {report_path}")

        if export_json:
            logger.info("")
            logger.info("=" * sep)
            logger.info("EXPORTING JSON STATISTICS FOR LLM ANALYSIS...")
            logger.info("=" * sep)
            engine.export_stats_json(export_json)
