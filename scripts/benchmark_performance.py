#!/usr/bin/env python3
"""Performance benchmarking script for the fish tank simulation.

Runs the simulation in headless mode and measures frame timing statistics.

Usage:
    python scripts/benchmark_performance.py [--frames N] [--warmup N] [--profile]

Example:
    python scripts/benchmark_performance.py --frames 1000 --warmup 100
"""

import argparse
import cProfile
import pstats
import statistics
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_benchmark(num_frames: int = 1000, warmup_frames: int = 100) -> dict:
    """Run benchmark and return timing statistics.

    Args:
        num_frames: Number of frames to benchmark
        warmup_frames: Number of warmup frames before measuring

    Returns:
        Dictionary with timing statistics
    """
    from core.tank_world import TankWorld, TankWorldConfig

    # Create headless simulation
    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=42)  # Fixed seed for reproducibility
    world.setup()

    frame_times = []

    print(f"Warming up for {warmup_frames} frames...")
    for _ in range(warmup_frames):
        world.update()

    print(f"Benchmarking {num_frames} frames...")
    for i in range(num_frames):
        start = time.perf_counter()
        world.update()
        elapsed = time.perf_counter() - start
        frame_times.append(elapsed * 1000)  # Convert to ms

        if (i + 1) % 200 == 0:
            print(f"  Frame {i + 1}/{num_frames}...")

    # Calculate statistics
    stats = {
        "total_frames": num_frames,
        "total_time_ms": sum(frame_times),
        "avg_frame_ms": statistics.mean(frame_times),
        "median_frame_ms": statistics.median(frame_times),
        "min_frame_ms": min(frame_times),
        "max_frame_ms": max(frame_times),
        "std_dev_ms": statistics.stdev(frame_times) if len(frame_times) > 1 else 0,
        "p95_frame_ms": sorted(frame_times)[int(len(frame_times) * 0.95)],
        "p99_frame_ms": sorted(frame_times)[int(len(frame_times) * 0.99)],
        "fps_avg": 1000.0 / statistics.mean(frame_times),
        "entity_count": len(world.entities_list),
        "fish_count": len([e for e in world.entities_list if hasattr(e, "genome")]),
    }

    return stats


def run_profiled_benchmark(num_frames: int = 500) -> None:
    """Run benchmark with cProfile profiling.

    Args:
        num_frames: Number of frames to profile
    """
    from core.tank_world import TankWorld, TankWorldConfig

    # Create headless simulation
    config = TankWorldConfig(headless=True)
    world = TankWorld(config=config, seed=42)
    world.setup()

    # Warmup
    for _ in range(50):
        world.update()

    # Profile
    profiler = cProfile.Profile()
    print(f"Profiling {num_frames} frames...")

    profiler.enable()
    for _ in range(num_frames):
        world.update()
    profiler.disable()

    # Print stats
    print("\n" + "=" * 80)
    print("PROFILING RESULTS (top 30 functions by cumulative time)")
    print("=" * 80)

    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(30)

    print("\n" + "=" * 80)
    print("TOP 20 FUNCTIONS BY TOTAL TIME (self time only)")
    print("=" * 80)
    stats.sort_stats("tottime")
    stats.print_stats(20)


def main():
    parser = argparse.ArgumentParser(description="Benchmark fish tank simulation performance")
    parser.add_argument(
        "--frames", type=int, default=1000, help="Number of frames to benchmark (default: 1000)"
    )
    parser.add_argument(
        "--warmup", type=int, default=100, help="Number of warmup frames (default: 100)"
    )
    parser.add_argument("--profile", action="store_true", help="Run with cProfile profiling")
    args = parser.parse_args()

    print("=" * 60)
    print("FISH TANK PERFORMANCE BENCHMARK")
    print("=" * 60)

    if args.profile:
        run_profiled_benchmark(args.frames)
    else:
        stats = run_benchmark(args.frames, args.warmup)

        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)
        print(f"Total frames:     {stats['total_frames']}")
        print(f"Total time:       {stats['total_time_ms']:.2f} ms")
        print(f"Entity count:     {stats['entity_count']}")
        print(f"Fish count:       {stats['fish_count']}")
        print()
        print("Frame Timing Statistics:")
        print(f"  Average:        {stats['avg_frame_ms']:.3f} ms")
        print(f"  Median:         {stats['median_frame_ms']:.3f} ms")
        print(f"  Min:            {stats['min_frame_ms']:.3f} ms")
        print(f"  Max:            {stats['max_frame_ms']:.3f} ms")
        print(f"  Std Dev:        {stats['std_dev_ms']:.3f} ms")
        print(f"  95th percentile: {stats['p95_frame_ms']:.3f} ms")
        print(f"  99th percentile: {stats['p99_frame_ms']:.3f} ms")
        print()
        print(f"Average FPS:      {stats['fps_avg']:.1f}")
        print()

        # Performance assessment
        if stats["avg_frame_ms"] < 1.0:
            print("Performance: EXCELLENT (< 1ms per frame)")
        elif stats["avg_frame_ms"] < 5.0:
            print("Performance: GOOD (< 5ms per frame)")
        elif stats["avg_frame_ms"] < 16.67:
            print("Performance: ACCEPTABLE (< 16.67ms, can run at 60fps)")
        elif stats["avg_frame_ms"] < 33.33:
            print("Performance: ADEQUATE (< 33.33ms, can run at 30fps)")
        else:
            print("Performance: NEEDS IMPROVEMENT (> 33.33ms per frame)")


if __name__ == "__main__":
    main()
