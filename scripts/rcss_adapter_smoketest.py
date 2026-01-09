"""Smoke test for rcssserver adapter and protocol layer.

This script demonstrates the protocol layer functionality and adapter usage
without requiring the actual rcssserver binary.

NOTE: This script is currently DEPRECATED because the legacy soccer world
stack (core/worlds/soccer/) was removed in the RCSS-Lite consolidation.

The new RCSS-Lite engine is in core/minigames/soccer/engine.py

To test the new stack, use:
    python -m pytest tests/test_soccer_world.py tests/test_rcss_conformance.py -v
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> int:
    """Run smoke tests using new RCSS-Lite stack."""
    print("\n" + "=" * 70)
    print("  RCSS-Lite Engine Smoke Test")
    print("=" * 70)

    print("\n[INFO] The legacy RCSS adapter was removed in the soccer consolidation.")
    print("[INFO] Using new RCSS-Lite engine from core.minigames.soccer\n")

    try:
        from core.minigames.soccer import (
            DEFAULT_RCSS_PARAMS,
            RCSSCommand,
            RCSSLiteEngine,
            RCSSVector,
            SoccerMatchRunner,
        )

        print("[OK] RCSS-Lite imports successful")

        # Test engine
        print("\n[OK] Creating RCSS-Lite Engine:")
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(-20, 0), body_angle=0.0)
        engine.add_player("right_1", "right", RCSSVector(20, 0), body_angle=3.14)
        print(f"  Cycle: {engine.cycle}")
        print(f"  Players: left_1  ={engine.get_player('left_1').position.x:.1f}")
        print(f"           right_1 = {engine.get_player('right_1').position.x:.1f}")

        # Test stepping
        print("\n[OK] Stepping with commands:")
        for i in range(10):
            engine.queue_command("left_1", RCSSCommand.dash(100, 0))
            engine.queue_command("right_1", RCSSCommand.dash(100, 0))
            engine.step_cycle()

        print("  After 10 steps:")
        print(f"  left_1.x  = {engine.get_player('left_1').position.x:.2f}")
        print(f"  right_1.x = {engine.get_player('right_1').position.x:.2f}")

        # Test match runner
        print("\n[OK] Testing SoccerMatchRunner:")
        import random

        from core.genetics import Genome

        runner = SoccerMatchRunner(team_size=2)
        rng = random.Random(42)
        population = [Genome.random(use_algorithm=False, rng=rng) for _ in range(4)]

        episode_result, agent_results = runner.run_episode(
            genomes=population,
            seed=42,
            frames=100,
        )

        print(f"  Episode frames: {episode_result.frames}")
        print(f"  Score: {episode_result.score_left}-{episode_result.score_right}")
        print(f"  Agent results: {len(agent_results)}")

        # Test params
        print("\n[OK] Default RCSS Params:")
        print(f"  cycle_ms: {DEFAULT_RCSS_PARAMS.cycle_ms}")
        print(f"  player_speed_max: {DEFAULT_RCSS_PARAMS.player_speed_max}")
        print(f"  ball_decay: {DEFAULT_RCSS_PARAMS.ball_decay}")

        print("\n" + "=" * 70)
        print("[PASS] All RCSS-Lite smoke tests passed!")
        print("=" * 70 + "\n")

        return 0

    except Exception as e:
        print(f"\n[FAIL] Smoke test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
