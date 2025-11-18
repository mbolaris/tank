"""Main entry point for the fish tank simulation.

This module provides command-line options to run the simulation:
- Web mode (default): React UI with FastAPI backend
- Headless mode: Stats-only, faster than realtime for testing
"""

import argparse
import sys
import logging

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


def run_headless(max_frames: int, stats_interval: int, seed=None):
    """Run the simulation in headless mode (no visualization).

    Args:
        max_frames: Maximum number of frames to simulate
        stats_interval: Print stats every N frames
        seed: Optional random seed for deterministic behavior
    """
    import random
    from simulation_engine import SimulationEngine

    if seed is not None:
        random.seed(seed)
        logger.info("Using random seed: %d", seed)

    engine = SimulationEngine(headless=True)
    engine.run_headless(max_frames=max_frames, stats_interval=stats_interval)


def main():
    """Parse command-line arguments and run the appropriate mode."""
    parser = argparse.ArgumentParser(
        description='Fish Tank Ecosystem Simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run web server (default)
  python main.py

  # Run headless for testing/benchmarking
  python main.py --headless --max-frames 10000 --stats-interval 500

  # Quick test run (headless, 1000 frames)
  python main.py --headless --max-frames 1000

  # Long simulation with seed for reproducibility
  python main.py --headless --max-frames 100000 --seed 42
        """
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (no UI, stats only)'
    )

    parser.add_argument(
        '--max-frames',
        type=int,
        default=10000,
        help='Maximum frames to simulate in headless mode (default: 10000)'
    )

    parser.add_argument(
        '--stats-interval',
        type=int,
        default=300,
        help='Print stats every N frames in headless mode (default: 300)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for deterministic behavior (optional)'
    )

    args = parser.parse_args()

    if args.headless:
        logger.info("Starting headless simulation...")
        logger.info("Configuration: %d frames, stats every %d frames", args.max_frames, args.stats_interval)
        logger.info("")
        run_headless(args.max_frames, args.stats_interval, seed=args.seed)
    else:
        run_web_server()


if __name__ == "__main__":
    main()
