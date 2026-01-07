#!/usr/bin/env python3
"""Headless world runner using the canonical WorldRegistry path.

This is the single canonical way to run any world type in headless mode.
All scripts and tools should use this module instead of instantiating
TankWorld or other world types directly.

Usage:
    python -m tools.run_headless --mode tank --steps 1000 --seed 42
    python -m tools.run_headless --mode petri --steps 500
    python -m tools.run_headless --mode soccer --steps 100 --team-size 3
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any

from core.worlds import WorldRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


def run_headless_world(
    mode_id: str,
    *,
    seed: int | None = None,
    steps: int = 1000,
    config: dict[str, Any] | None = None,
    stats_interval: int = 0,
    quiet: bool = False,
) -> dict[str, Any]:
    """Run a world headless via the canonical WorldRegistry path.

    Args:
        mode_id: World mode to run (e.g., "tank", "petri", "soccer")
        seed: Optional random seed for deterministic runs
        steps: Number of simulation steps to run
        config: Optional config overrides dict
        stats_interval: Print stats every N frames (0 = never)
        quiet: Suppress progress output

    Returns:
        Final metrics dictionary from the world
    """
    effective_config = dict(config or {})
    effective_config.setdefault("headless", True)

    world = WorldRegistry.create_world(mode_id, seed=seed, config=effective_config)
    world.reset(seed=seed, config=effective_config)

    start_time = time.time()

    for i in range(steps):
        world.step()

        if stats_interval and (i + 1) % stats_interval == 0 and not quiet:
            elapsed = time.time() - start_time
            fps = (i + 1) / elapsed if elapsed > 0 else 0
            logger.info(f"Frame {i + 1}/{steps} ({fps:.1f} fps)")

    runtime = time.time() - start_time

    metrics = world.get_current_metrics(include_distributions=False)
    metrics["runtime_seconds"] = runtime
    metrics["frames"] = steps

    if not quiet:
        logger.info(f"Completed {steps} frames in {runtime:.2f}s ({steps / runtime:.1f} fps)")

    return metrics


def main() -> None:
    """CLI entry point for headless world runner."""
    parser = argparse.ArgumentParser(
        description="Run a world simulation in headless mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.run_headless --mode tank --steps 1000 --seed 42
  python -m tools.run_headless --mode petri --steps 500 --stats-interval 100
  python -m tools.run_headless --mode soccer --steps 100 --team-size 3
        """,
    )

    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        default="tank",
        help="World mode to run (default: tank)",
    )
    parser.add_argument(
        "--steps",
        "-s",
        type=int,
        default=1000,
        help="Number of simulation steps (default: 1000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic behavior",
    )
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=100,
        help="Print stats every N frames (default: 100, 0 = off)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )
    # Mode-specific args
    parser.add_argument(
        "--team-size",
        type=int,
        default=None,
        help="Team size for soccer mode",
    )
    parser.add_argument(
        "--screen-width",
        type=int,
        default=None,
        help="Override screen width",
    )
    parser.add_argument(
        "--screen-height",
        type=int,
        default=None,
        help="Override screen height",
    )

    args = parser.parse_args()

    # Build config from CLI args
    config: dict[str, Any] = {}
    if args.team_size is not None:
        config["team_size"] = args.team_size
    if args.screen_width is not None:
        config["screen_width"] = args.screen_width
    if args.screen_height is not None:
        config["screen_height"] = args.screen_height

    # List available modes if requested mode is invalid
    available_modes = list(WorldRegistry.list_mode_packs().keys())
    if args.mode not in available_modes:
        logger.error(f"Unknown mode '{args.mode}'. Available: {available_modes}")
        sys.exit(1)

    if not args.quiet:
        logger.info(f"Running {args.mode} world for {args.steps} steps (seed={args.seed})")

    try:
        metrics = run_headless_world(
            args.mode,
            seed=args.seed,
            steps=args.steps,
            config=config if config else None,
            stats_interval=args.stats_interval,
            quiet=args.quiet,
        )

        if not args.quiet:
            logger.info(f"Final metrics: entities={metrics.get('population', 'N/A')}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
