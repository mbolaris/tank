"""Run simulation until a specific generation is reached.

This script runs the fish tank simulation in headless mode until
the ecosystem reaches a target generation number.
"""

import argparse
import random
import time
from simulation_engine import SimulationEngine


def run_until_generation(target_generation: int, stats_interval: int = 300, seed=None, max_frames: int = 1000000):
    """Run the simulation until target generation is reached.

    Args:
        target_generation: Target generation to reach
        stats_interval: Print stats every N frames
        seed: Optional random seed for deterministic behavior
        max_frames: Maximum frames to prevent infinite loops
    """
    if seed is not None:
        random.seed(seed)
        print(f"Using random seed: {seed}")

    print("=" * 80)
    print("FISH TANK SIMULATION - RUNNING UNTIL GENERATION", target_generation)
    print("=" * 80)
    print(f"Stats will be printed every {stats_interval} frames")
    print(f"Maximum frames: {max_frames}")
    print("=" * 80)
    print()

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
            print("\n" + "=" * 80)
            print(f"TARGET GENERATION {target_generation} REACHED!")
            print("=" * 80)
            break

    # Print final stats
    print("\n" + "=" * 80)
    print("SIMULATION COMPLETE - Final Statistics")
    print("=" * 80)
    engine.print_stats()

    # Print detailed generation breakdown
    if engine.ecosystem:
        print("\n" + "=" * 80)
        print("GENERATION BREAKDOWN")
        print("=" * 80)
        for gen in sorted(engine.ecosystem.generation_stats.keys()):
            stats = engine.ecosystem.generation_stats[gen]
            print(f"\nGeneration {gen}:")
            print(f"  Population: {stats.population}")
            print(f"  Births: {stats.births}")
            print(f"  Deaths: {stats.deaths}")
            print(f"  Avg Age at Death: {stats.avg_age:.1f} frames")
            print(f"  Avg Speed: {stats.avg_speed:.2f}")
            print(f"  Avg Size: {stats.avg_size:.2f}")
            print(f"  Avg Energy: {stats.avg_energy:.2f}")

    # Generate algorithm performance report
    if engine.ecosystem:
        print("\n" + "=" * 80)
        print("ALGORITHM PERFORMANCE REPORT")
        print("=" * 80)
        report = engine.ecosystem.get_algorithm_performance_report()
        print(report)

        # Save to file
        filename = f'generation_{target_generation}_report.txt'
        with open(filename, 'w') as f:
            f.write(f"Simulation Report - Generation {target_generation}\n")
            f.write(f"Total Frames: {frame}\n")
            f.write(f"Real Time: {time.time() - start_time:.1f}s\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("FINAL STATISTICS\n")
            f.write("=" * 80 + "\n\n")

            stats = engine.get_stats()
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("GENERATION BREAKDOWN\n")
            f.write("=" * 80 + "\n\n")

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

        print(f"\nReport saved to: {filename}")

    elapsed = time.time() - start_time
    print(f"\nTotal simulation time: {elapsed:.1f}s ({frame} frames)")
    print(f"Simulation speed: {frame / (30 * elapsed):.2f}x realtime")


def main():
    """Parse arguments and run simulation."""
    parser = argparse.ArgumentParser(
        description='Run fish tank simulation until target generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run until generation 10
  python run_until_generation.py --generation 10

  # Run with custom stats interval
  python run_until_generation.py --generation 10 --stats-interval 500

  # Run with random seed for reproducibility
  python run_until_generation.py --generation 10 --seed 42
        """
    )

    parser.add_argument(
        '--generation',
        type=int,
        default=10,
        help='Target generation to reach (default: 10)'
    )

    parser.add_argument(
        '--stats-interval',
        type=int,
        default=300,
        help='Print stats every N frames (default: 300)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for deterministic behavior (optional)'
    )

    parser.add_argument(
        '--max-frames',
        type=int,
        default=1000000,
        help='Maximum frames to prevent infinite loops (default: 1000000)'
    )

    args = parser.parse_args()

    run_until_generation(
        target_generation=args.generation,
        stats_interval=args.stats_interval,
        seed=args.seed,
        max_frames=args.max_frames
    )


if __name__ == "__main__":
    main()
