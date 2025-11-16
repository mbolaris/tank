"""Main entry point for the fish tank simulation.

This module provides command-line options to run the simulation in either:
- Graphical mode (with pygame visualization)
- Headless mode (stats-only, faster than realtime)
"""

import argparse
import sys


def run_graphical():
    """Run the simulation with graphical visualization."""
    try:
        import pygame
        from fishtank import FishTankSimulator

        pygame.init()
        game = FishTankSimulator()
        try:
            game.run()
        finally:
            pygame.quit()
    except ImportError as e:
        print(f"Error: pygame is required for graphical mode: {e}")
        print("Install pygame with: pip install pygame")
        sys.exit(1)


def run_headless(max_frames: int, stats_interval: int):
    """Run the simulation in headless mode (no visualization).

    Args:
        max_frames: Maximum number of frames to simulate
        stats_interval: Print stats every N frames
    """
    from simulation_engine import SimulationEngine

    engine = SimulationEngine(headless=True)
    engine.run_headless(max_frames=max_frames, stats_interval=stats_interval)


def main():
    """Parse command-line arguments and run the appropriate mode."""
    parser = argparse.ArgumentParser(
        description='Fish Tank Ecosystem Simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with graphical interface
  python main.py --mode graphical

  # Run headless for 10000 frames, print stats every 500 frames
  python main.py --mode headless --max-frames 10000 --stats-interval 500

  # Quick test run (headless, 1000 frames)
  python main.py --mode headless --max-frames 1000

  # Long simulation (headless, 100000 frames = ~55 min of sim time)
  python main.py --mode headless --max-frames 100000 --stats-interval 3000
        """
    )

    parser.add_argument(
        '--mode',
        choices=['graphical', 'headless'],
        default='graphical',
        help='Simulation mode (default: graphical)'
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

    args = parser.parse_args()

    if args.mode == 'graphical':
        print("Starting graphical simulation...")
        print("Press H to toggle stats/health bars")
        print("Press P to pause/resume")
        print("Press R to generate algorithm performance report")
        print("Press SPACE to drop food")
        print("Press ESC to quit")
        print()
        run_graphical()
    else:
        print("Starting headless simulation...")
        print(f"Configuration: {args.max_frames} frames, stats every {args.stats_interval} frames")
        print()
        run_headless(args.max_frames, args.stats_interval)


if __name__ == "__main__":
    main()
