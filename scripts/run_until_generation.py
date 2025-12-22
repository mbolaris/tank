"""Run simulation until a specific generation is reached.

This script runs the fish tank simulation in headless mode until
the ecosystem reaches a target generation number.
"""

import argparse
import logging
import random
import time

from core.config.display import FRAME_RATE
from core.simulation_engine import SimulationEngine

logger = logging.getLogger(__name__)

# Wider separator for detailed reports
REPORT_SEPARATOR_WIDTH = 80


def run_until_generation(
    target_generation: int, stats_interval: int = 300, seed=None, max_frames: int = 1000000
):
    """Run the simulation until target generation is reached.

    Args:
        target_generation: Target generation to reach
        stats_interval: Print stats every N frames
        seed: Optional random seed for deterministic behavior
        max_frames: Maximum frames to prevent infinite loops
    """
    if seed is not None:
        random.seed(seed)
        logger.info("Using random seed: %d", seed)

    logger.info("=" * REPORT_SEPARATOR_WIDTH)
    logger.info("FISH TANK SIMULATION - RUNNING UNTIL GENERATION %d", target_generation)
    logger.info("=" * REPORT_SEPARATOR_WIDTH)
    logger.info("Stats will be printed every %d frames", stats_interval)
    logger.info("Maximum frames: %d", max_frames)
    logger.info("=" * REPORT_SEPARATOR_WIDTH)
    logger.info("")

    engine = SimulationEngine(headless=True)
    engine.setup()

    start_time = time.time()
    frame = 0

    while frame < max_frames:
        engine.update()
        frame += 1

        # Print stats periodically
        if frame > 0 and frame % stats_interval == 0:
            engine.print_stats()

        # Check if we've reached target generation
        if engine.ecosystem and engine.ecosystem.current_generation >= target_generation:
            logger.info("")
            logger.info("=" * REPORT_SEPARATOR_WIDTH)
            logger.info("TARGET GENERATION %d REACHED!", target_generation)
            logger.info("=" * REPORT_SEPARATOR_WIDTH)
            break

    # Print final stats
    logger.info("")
    logger.info("=" * REPORT_SEPARATOR_WIDTH)
    logger.info("SIMULATION COMPLETE - Final Statistics")
    logger.info("=" * REPORT_SEPARATOR_WIDTH)
    engine.print_stats()

    # Print detailed generation breakdown
    if engine.ecosystem:
        logger.info("")
        logger.info("=" * REPORT_SEPARATOR_WIDTH)
        logger.info("GENERATION BREAKDOWN")
        logger.info("=" * REPORT_SEPARATOR_WIDTH)
        for gen in sorted(engine.ecosystem.generation_stats.keys()):
            stats = engine.ecosystem.generation_stats[gen]
            logger.info("")
            logger.info("Generation %d:", gen)
            logger.info("  Population: %d", stats.population)
            logger.info("  Births: %d", stats.births)
            logger.info("  Deaths: %d", stats.deaths)
            logger.info("  Avg Age at Death: %.1f frames", stats.avg_age)
            logger.info("  Avg Speed: %.2f", stats.avg_speed)
            logger.info("  Avg Size: %.2f", stats.avg_size)
            logger.info("  Avg Energy: %.2f", stats.avg_energy)

    # Generate algorithm performance report
    if engine.ecosystem:
        logger.info("")
        logger.info("=" * REPORT_SEPARATOR_WIDTH)
        logger.info("ALGORITHM PERFORMANCE REPORT")
        logger.info("=" * REPORT_SEPARATOR_WIDTH)
        report = engine.ecosystem.get_algorithm_performance_report()
        logger.info("%s", report)

        # Save to file
        filename = f"generation_{target_generation}_report.txt"
        with open(filename, "w") as f:
            f.write(f"Simulation Report - Generation {target_generation}\n")
            f.write(f"Total Frames: {frame}\n")
            f.write(f"Real Time: {time.time() - start_time:.1f}s\n")
            f.write("\n" + "=" * REPORT_SEPARATOR_WIDTH + "\n")
            f.write("FINAL STATISTICS\n")
            f.write("=" * REPORT_SEPARATOR_WIDTH + "\n\n")

            stats = engine.get_stats()
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")

            f.write("\n" + "=" * REPORT_SEPARATOR_WIDTH + "\n")
            f.write("GENERATION BREAKDOWN\n")
            f.write("=" * REPORT_SEPARATOR_WIDTH + "\n\n")

            for gen in sorted(engine.ecosystem.generation_stats.keys()):
                gen_stats = engine.ecosystem.generation_stats[gen]
                f.write(f"Generation {gen}:\n")
                f.write(f"  Population: {gen_stats.population}\n")
                f.write(f"  Births: {gen_stats.births}\n")
                f.write(f"  Deaths: {gen_stats.deaths}\n")
                f.write(f"  Avg Age at Death: {gen_stats.avg_age:.1f} frames\n")
                f.write(f"  Avg Speed: {gen_stats.avg_speed:.2f}\n")
                f.write(f"  Avg Size: {gen_stats.avg_size:.2f}\n")
                f.write(f"  Avg Energy: {gen_stats.avg_energy:.2f}\n\n")

            f.write("\n" + report)

        logger.info("")
        logger.info("Report saved to: %s", filename)

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("Total simulation time: %.1fs (%d frames)", elapsed, frame)
    logger.info("Simulation speed: %.2fx realtime", frame / (FRAME_RATE * elapsed))


def main():
    """Parse arguments and run simulation."""
    parser = argparse.ArgumentParser(
        description="Run fish tank simulation until target generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run until generation 10
  python run_until_generation.py --generation 10

  # Run with custom stats interval
  python run_until_generation.py --generation 10 --stats-interval 500

  # Run with random seed for reproducibility
  python run_until_generation.py --generation 10 --seed 42
        """,
    )

    parser.add_argument(
        "--generation", type=int, default=10, help="Target generation to reach (default: 10)"
    )

    parser.add_argument(
        "--stats-interval", type=int, default=300, help="Print stats every N frames (default: 300)"
    )

    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for deterministic behavior (optional)"
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=1000000,
        help="Maximum frames to prevent infinite loops (default: 1000000)",
    )

    args = parser.parse_args()

    run_until_generation(
        target_generation=args.generation,
        stats_interval=args.stats_interval,
        seed=args.seed,
        max_frames=args.max_frames,
    )


if __name__ == "__main__":
    main()
