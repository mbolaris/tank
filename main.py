"""Main entry point for the fish tank simulation.

This module provides command-line options to run the simulation:
- Web mode (default): React UI with FastAPI backend
- Headless mode: Stats-only, faster than realtime for testing
"""

import argparse
import sys


def run_web_server():
    """Run the web server with React UI backend."""
    try:
        import uvicorn
        from backend.main import app

        print("=" * 60)
        print("FISH TANK SIMULATION - WEB SERVER")
        print("=" * 60)
        print()
        print("Starting FastAPI backend server...")
        print("Open http://localhost:3000 in your browser")
        print("API docs available at http://localhost:8000/docs")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        print()

        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError as e:
        print(f"Error: Required dependencies not installed: {e}")
        print("Install with: pip install -e .[backend]")
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
        print(f"Using random seed: {seed}")

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
        print("Starting headless simulation...")
        print(f"Configuration: {args.max_frames} frames, stats every {args.stats_interval} frames")
        print()
        run_headless(args.max_frames, args.stats_interval, seed=args.seed)
    else:
        run_web_server()


if __name__ == "__main__":
    main()
