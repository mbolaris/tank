"""Smoke test for soccer animation: autopolicy produces movement across steps.

Uses the RCSS-Lite minigame engine.
"""

from core.minigames.soccer import RCSSCommand, RCSSLiteEngine, RCSSVector, SoccerMatchRunner


class TestSoccerAnimation:
    """Verify soccer autopolicy generates movement for watchable mode."""

    def test_autopolicy_produces_movement(self) -> None:
        """Players should move when stepping with autopolicy."""
        import random

        from core.genetics import Genome

        runner = SoccerMatchRunner(team_size=2)

        rng = random.Random(42)
        population = [Genome.random(use_algorithm=False, rng=rng) for _ in range(4)]

        # Run episode for enough frames to get some activity
        episode_result, agent_results = runner.run_episode(
            genomes=population,
            seed=42,
            frames=100,  # Increased from 50
        )

        # Check that kicks occurred (indicates movement near ball + autopolicy working)
        total_kicks = sum(stats.kicks for stats in episode_result.player_stats.values())

        # At least some kicks should have occurred
        assert (
            total_kicks > 0
        ), f"Players should have kicked the ball during the match (kicks={total_kicks})"

    def test_engine_player_movement(self) -> None:
        """Test direct engine player movement."""
        engine = RCSSLiteEngine(seed=42)
        engine.add_player("left_1", "left", RCSSVector(-20, 0), body_angle=0.0)
        engine.add_player("right_1", "right", RCSSVector(20, 0), body_angle=3.14159)

        initial_left_x = engine.get_player("left_1").position.x
        initial_right_x = engine.get_player("right_1").position.x

        # Step with dash commands
        for _ in range(20):
            engine.queue_command("left_1", RCSSCommand.dash(100, 0))
            engine.queue_command("right_1", RCSSCommand.dash(100, 0))
            engine.step_cycle()

        final_left_x = engine.get_player("left_1").position.x
        final_right_x = engine.get_player("right_1").position.x

        # Both players should have moved
        assert final_left_x != initial_left_x, "Left player should move with dash"
        assert final_right_x != initial_right_x, "Right player should move with dash"

    def test_match_runner_determinism(self) -> None:
        """Same seed produces identical results."""
        import random

        from core.genetics import Genome

        def run_match(seed):
            runner = SoccerMatchRunner(team_size=2)
            rng = random.Random(seed)
            population = [Genome.random(use_algorithm=False, rng=rng) for _ in range(4)]

            episode_result, _ = runner.run_episode(
                genomes=population,
                seed=seed,
                frames=100,
            )
            return episode_result.score_left, episode_result.score_right

        result1 = run_match(42)
        result2 = run_match(42)

        assert result1 == result2, "Same seed should produce identical scores"
