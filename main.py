"""Main entry point for the fish tank simulation.

This module provides command-line options to run the simulation:
- Web mode (default): React UI with FastAPI backend
- Headless mode: Stats-only, faster than realtime for testing
"""

import argparse
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=os.getenv("TANK_LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s:%(name)s:%(message)s",
)

logger = logging.getLogger(__name__)


def _request_shutdown_best_effort() -> None:
    try:
        from core.auto_evaluate_poker import request_shutdown

        request_shutdown()
    except Exception:
        pass


def run_web_server():
    """Run the web server with React UI backend."""
    from core.config.display import SEPARATOR_WIDTH
    from core.config.server import DEFAULT_API_PORT

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

        # Disable Uvicorn access logs to reduce verbosity in stdout
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
        uvicorn.run(app, host="0.0.0.0", port=DEFAULT_API_PORT, access_log=False)
    except ImportError as e:
        logger.error("Error: Required dependencies not installed: %s", e)
        logger.error("Install with: pip install -e .[backend]")
        sys.exit(1)


def run_headless(
    max_frames: int, stats_interval: int, seed=None, export_stats=None, trace_output=None
):
    """Run the simulation in headless mode (no visualization).

    Args:
        max_frames: Maximum number of frames to simulate
        stats_interval: Print stats every N frames
        seed: Optional random seed for deterministic behavior
        export_stats: Optional filename to export JSON stats for LLM analysis
        trace_output: Optional filename to export debug trace data (currently unused)
    """
    import json

    from core.worlds import WorldRegistry

    # Create world via the canonical WorldRegistry path
    world = WorldRegistry.create_world("tank", seed=seed, headless=True)
    world.reset(seed=seed)

    # Run simulation loop
    for frame in range(max_frames):
        world.step()

        if stats_interval and (frame + 1) % stats_interval == 0:
            stats = world.get_current_metrics(include_distributions=False)
            pop = stats.get("population", len(world.get_entities_for_snapshot()))
            logger.info(f"Frame {frame + 1}/{max_frames}: population={pop}")

    # Export stats if requested
    if export_stats:
        stats = world.get_current_metrics(include_distributions=True)
        stats["frame"] = max_frames
        with open(export_stats, "w") as f:
            json.dump(stats, f, indent=2, default=str)
        logger.info(f"Stats exported to: {export_stats}")


def main():
    """Parse command-line arguments and run the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Tank World Simulation",
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

  # Record deterministic fingerprints (JSONL)
  python main.py --headless --max-frames 500 --seed 42 --record out.replay.jsonl

  # Replay a recording (verifies fingerprints match)
  python main.py --headless --replay out.replay.jsonl
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

    parser.add_argument(
        "--trace-json",
        type=str,
        default=None,
        metavar="TRACEFILE",
        help="Dump debug traces to JSON for offline analysis",
    )

    parser.add_argument(
        "--record",
        type=str,
        default=None,
        metavar="REPLAYFILE",
        help="Record a replay file with per-step fingerprints (JSONL)",
    )

    parser.add_argument(
        "--switch",
        action="append",
        default=None,
        metavar="FRAME:MODE",
        help="During --record, schedule a mode switch at a frame (e.g., 200:petri). May repeat.",
    )

    parser.add_argument(
        "--record-every",
        type=int,
        default=1,
        metavar="N",
        help="Record a fingerprint every N steps when using --record (default: 1)",
    )

    parser.add_argument(
        "--replay",
        type=str,
        default=None,
        metavar="REPLAYFILE",
        help="Replay a recorded file and verify fingerprints match",
    )

    args = parser.parse_args()

    if args.record and args.replay:
        logger.error("Cannot use --record and --replay together")
        sys.exit(2)

    if args.headless:
        logger.info("Starting headless simulation...")
        logger.info(
            "Configuration: %d frames, stats every %d frames", args.max_frames, args.stats_interval
        )
        if args.export_stats:
            logger.info("Stats will be exported to: %s", args.export_stats)
        if args.trace_json:
            logger.info("Trace output will be saved to: %s", args.trace_json)
        logger.info("")

        if args.replay:
            from backend.replay import replay_file

            replay_file(args.replay)
            logger.info("Replay verified: %s", args.replay)
            return

        if args.record:
            from backend.replay import ReplayPlan, record_file

            if args.seed is None:
                logger.error("--record requires --seed for deterministic replay")
                sys.exit(2)

            switch_at = {}
            for item in args.switch or []:
                try:
                    frame_s, mode_id = item.split(":", 1)
                    frame_i = int(frame_s)
                except Exception:
                    logger.error("Invalid --switch value: %r (expected FRAME:MODE)", item)
                    sys.exit(2)
                if frame_i < 0:
                    logger.error("Invalid --switch frame: %s (must be >= 0)", frame_i)
                    sys.exit(2)
                switch_at[frame_i] = mode_id

            record_file(
                args.record,
                seed=args.seed,
                initial_mode="tank",
                steps=args.max_frames,
                record_every=args.record_every,
                plan=ReplayPlan(switch_at),
            )
            logger.info("Replay recorded: %s", args.record)
            return

        run_headless(
            args.max_frames,
            args.stats_interval,
            seed=args.seed,
            export_stats=args.export_stats,
            trace_output=args.trace_json,
        )
    else:
        if args.record or args.replay:
            logger.error("--record/--replay require --headless")
            sys.exit(2)
        run_web_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down...")
        _request_shutdown_best_effort()
        sys.exit(0)
