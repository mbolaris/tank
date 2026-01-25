from core.minigames.soccer.eval import SoccerEpisodeConfig, run_soccer_episode


def test_soccer_eval_deterministic_same_seed():
    """Run twice with same config and assert results are identical (including episode_hash)."""
    config = SoccerEpisodeConfig(
        seed=42, max_cycles=200, initial_players={"A": [(200, 300)], "B": [(600, 300)]}
    )

    result1 = run_soccer_episode(config)
    result2 = run_soccer_episode(config)

    assert result1.episode_hash == result2.episode_hash
    assert result1.score == result2.score
    assert result1.touches == result2.touches
    assert result1.possession_cycles == result2.possession_cycles


def test_soccer_eval_diff_seed_changes_hash():
    """Same setup but different seed => episode_hash differs."""
    config1 = SoccerEpisodeConfig(
        seed=42, max_cycles=200, initial_players={"A": [(200, 300)], "B": [(600, 300)]}
    )

    config2 = SoccerEpisodeConfig(
        seed=43, max_cycles=200, initial_players={"A": [(200, 300)], "B": [(600, 300)]}
    )

    # result1 = run_soccer_episode(config1)
    # result2 = run_soccer_episode(config2)
    # Commented out to avoid unused variable error until we use them if needed
    pass

    # Episode hash should differ due to different seed (e.g. ball bounce or noise if enabled)
    # Even if score is same, a different seed should ideally lead to different trajectories
    # if there is ANY randomness involved (like SoccerSystem's kick direction bias or noise).
    # NOTE: SoccerSystem._process_auto_kicks doesn't use RNG currently, but it might in future.
    # However, the ball bounce or other factors might be affected if we use NOISY_RCSS_PARAMS.

    # If currently no randomness is used in auto-kicks or ball physics without noise,
    # the hash might be same. Let's force noise to be sure seeds matter if possible.
    from core.minigames.soccer.params import RCSSParams

    config1.params = RCSSParams(noise_enabled=True, noise_seed=42, kick_rand=0.1)
    config2.params = RCSSParams(noise_enabled=True, noise_seed=43, kick_rand=0.1)

    result1_noisy = run_soccer_episode(config1)
    result2_noisy = run_soccer_episode(config2)

    assert result1_noisy.episode_hash != result2_noisy.episode_hash


def test_soccer_eval_goal_scoring():
    """Verify that a goal is actually scored and logged in a simple scenario."""
    # Place ball very close to goal and player behind it
    # Field is 800x600. Goal is at (750, 300) with radius 40.
    config = SoccerEpisodeConfig(
        seed=42, max_cycles=100, initial_ball=(730, 300), initial_players={"B": [(710, 300)]}
    )
    result = run_soccer_episode(config)

    # Check if any goal was scored
    assert result.score["B"] > 0
