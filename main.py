"""Main entry point for the fish tank simulation.

This module provides command-line options to run the simulation:
- Web mode (default): React UI with FastAPI backend
- Headless mode: Stats-only, faster than realtime for testing
"""

import argparse
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

logger = logging.getLogger(__name__)


def run_web_server():
    """Run the web server with React UI backend."""
    from core.constants import DEFAULT_API_PORT, SEPARATOR_WIDTH

    try:
        import uvicorn

        from backend.main import app

        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("FISH TANK SIMULATION - WEB SERVER")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("")
        logger.info("Starting FastAPI backend server...")
        logger.info("Open http://localhost:3000 in your browser")
        logger.info("API docs available at http://localhost:%d/docs", DEFAULT_API_PORT)
        logger.info("")
        logger.info("Press Ctrl+C to stop the server")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("")

        uvicorn.run(app, host="0.0.0.0", port=DEFAULT_API_PORT)
    except ImportError as e:
        logger.error("Error: Required dependencies not installed: %s", e)
        logger.error("Install with: pip install -e .[backend]")
        sys.exit(1)


def run_headless(max_frames: int, stats_interval: int, seed=None, export_stats=None):
    """Run the simulation in headless mode (no visualization).

    Args:
        max_frames: Maximum number of frames to simulate
        stats_interval: Print stats every N frames
        seed: Optional random seed for deterministic behavior
        export_stats: Optional filename to export JSON stats for LLM analysis
    """
    from tank_world import TankWorld, TankWorldConfig

    # Create configuration for headless mode
    config = TankWorldConfig(headless=True)

    # Create TankWorld with optional seed
    world = TankWorld(config=config, seed=seed)
    # Note: run_headless() calls setup() internally
    world.run_headless(
        max_frames=max_frames, stats_interval=stats_interval, export_json=export_stats
    )


def main():
    """Parse command-line arguments and run the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Fish Tank Ecosystem Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run web server (default)
  python main.py

  # Run headless for testing/benchmarking
  python main.py --headless --max-frames 10000 --stats-interval 500

  # Quick test run (headless, 1000 frames)
  python main.py --headless --max-frames 1000

  # Export stats for LLM analysis and behavior improvement
  python main.py --headless --max-frames 10000 --export-stats results.json

  # Long simulation with seed for reproducibility
  python main.py --headless --max-frames 100000 --seed 42 --export-stats evolution_run.json
        """,
    )

    parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode (no UI, stats only)"
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=10000,
        help="Maximum frames to simulate in headless mode (default: 10000)",
    )

    parser.add_argument(
        "--stats-interval",
        type=int,
        default=300,
        help="Print stats every N frames in headless mode (default: 300)",
    )

    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for deterministic behavior (optional)"
    )

    parser.add_argument(
        "--export-stats",
        type=str,
        default=None,
        metavar="FILENAME",
        help="Export comprehensive stats to JSON file for LLM analysis (e.g., results.json)",
    )

    args = parser.parse_args()

    if args.headless:
        logger.info("Starting headless simulation...")
        logger.info(
            "Configuration: %d frames, stats every %d frames", args.max_frames, args.stats_interval
        )
        if args.export_stats:
            logger.info("Stats will be exported to: %s", args.export_stats)
        logger.info("")
        run_headless(
            args.max_frames, args.stats_interval, seed=args.seed, export_stats=args.export_stats
        )
    else:
        run_web_server()


if __name__ == "__main__":
    main()
