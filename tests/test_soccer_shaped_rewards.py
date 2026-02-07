"""Tests for shaped reward mode in soccer matches.

Verifies that reward_mode="shaped_pot" actually applies shaped bonuses
based on telemetry (touches, ball progress, shots) even in matches with
no goals scored.
"""

from unittest.mock import Mock

import pytest

from core.minigames.soccer.evaluator import (
    create_soccer_match_from_participants, finalize_soccer_match)


def create_mock_fish(fish_id: int, initial_energy: float = 100.0):
    """Create a mock fish with energy tracking for testing rewards."""
    fish = Mock()
    fish.fish_id = fish_id
    fish.energy = initial_energy
    fish.max_energy = 200.0
    fish.genome_ref = Mock()

    # Track energy modifications
    energy_log = []

    def modify_energy(amount: float, source: str = "unknown") -> float:
        """Mock energy modification that tracks deltas."""
        fish.energy += amount
        entry = {"amount": amount, "source": source}
        energy_log.append(entry)
        return amount

    fish.modify_energy = modify_energy
    fish._energy_log = energy_log
    return fish


def test_shaped_pot_applies_bonuses_without_goals():
    """Verify shaped_pot applies bonuses even in a 0-0 draw with ball activity.

    This is the critical test: shaped rewards should give learning signals
    even when no goals are scored.
    """
    # Create mock fish for a small match (2v2)
    fish_left_1 = create_mock_fish(1, 100.0)
    fish_left_2 = create_mock_fish(2, 100.0)
    fish_right_1 = create_mock_fish(3, 100.0)
    fish_right_2 = create_mock_fish(4, 100.0)

    participants = [fish_left_1, fish_left_2, fish_right_1, fish_right_2]

    # Create match (short duration to avoid actual goals)
    setup = create_soccer_match_from_participants(
        participants,
        duration_frames=100,  # Short match
        seed=42,
        entry_fee_energy=10.0,
    )

    match = setup.match

    # Run match
    while not match.game_over:
        match.step(num_steps=5)

    # Finalize with shaped_pot reward mode
    outcome = finalize_soccer_match(
        match,
        seed=setup.seed,
        entry_fees=setup.entry_fees,
        reward_mode="shaped_pot",
        reward_multiplier=1.0,
    )

    # Verify telemetry was collected
    assert match.telemetry is not None
    assert match.telemetry.total_cycles > 0

    # If it's a draw (0-0), shaped bonuses should still be applied
    if outcome.winner_team == "draw" or outcome.winner_team is None:
        # Check that some players received shaped bonuses
        # (bonuses appear as energy modifications beyond entry fee refund)
        total_shaped_bonus = 0.0
        for fish in participants:
            # Look for shaped bonus in energy log
            for log_entry in fish._energy_log:
                if "shaped" in log_entry["source"]:
                    total_shaped_bonus += log_entry["amount"]

        # Should have some shaped bonuses if there was any ball activity
        if match.telemetry.teams["left"].touches > 0 or match.telemetry.teams["right"].touches > 0:
            assert (
                total_shaped_bonus > 0
            ), "Expected non-zero shaped bonuses with ball activity in a draw"


def test_shaped_pot_vs_pot_payout_different_outcomes():
    """Verify shaped_pot produces different energy deltas than pot_payout.

    In a 0-0 draw, pot_payout gives no rewards (just refunds), while
    shaped_pot gives bonuses based on activity.
    """
    # Create two identical setups
    fish_set_1 = [create_mock_fish(i, 100.0) for i in range(1, 5)]
    fish_set_2 = [create_mock_fish(i + 10, 100.0) for i in range(1, 5)]

    # Match 1: pot_payout mode
    setup1 = create_soccer_match_from_participants(
        fish_set_1,
        duration_frames=100,
        seed=42,
        entry_fee_energy=10.0,
    )
    match1 = setup1.match
    while not match1.game_over:
        match1.step(num_steps=5)

    outcome1 = finalize_soccer_match(
        match1,
        seed=setup1.seed,
        entry_fees=setup1.entry_fees,
        reward_mode="pot_payout",
    )

    # Match 2: shaped_pot mode (same seed for determinism)
    setup2 = create_soccer_match_from_participants(
        fish_set_2,
        duration_frames=100,
        seed=42,
        entry_fee_energy=10.0,
    )
    match2 = setup2.match
    while not match2.game_over:
        match2.step(num_steps=5)

    outcome2 = finalize_soccer_match(
        match2,
        seed=setup2.seed,
        entry_fees=setup2.entry_fees,
        reward_mode="shaped_pot",
    )

    # Verify same match outcome (deterministic)
    assert outcome1.score_left == outcome2.score_left
    assert outcome1.score_right == outcome2.score_right
    assert outcome1.winner_team == outcome2.winner_team

    # If it's a draw, check energy deltas differ
    if outcome1.winner_team == "draw" or outcome1.winner_team is None:
        # pot_payout in a draw: energy delta should be 0 (refund = entry fee)
        total_delta_1 = sum(outcome1.energy_deltas.values())

        # shaped_pot in a draw: energy delta should be positive (refund + bonuses)
        total_delta_2 = sum(outcome2.energy_deltas.values())

        # Shaped pot should give more total energy (bonuses on top of refunds)
        if (
            match2.telemetry.teams["left"].touches > 0
            or match2.telemetry.teams["right"].touches > 0
        ):
            assert (
                total_delta_2 > total_delta_1
            ), "shaped_pot should give more total energy than pot_payout in a draw with activity"


def test_shaped_pot_with_winner_splits_pot_and_adds_bonuses():
    """Verify shaped_pot gives pot to winners AND shaped bonuses to all."""
    # Create a match likely to have a winner (longer duration)
    fish_participants = [create_mock_fish(i, 100.0) for i in range(1, 5)]

    setup = create_soccer_match_from_participants(
        fish_participants,
        duration_frames=500,  # Longer for better chance of goal
        seed=123,  # Different seed to try to get a winner
        entry_fee_energy=20.0,
    )
    match = setup.match

    while not match.game_over:
        match.step(num_steps=10)

    outcome = finalize_soccer_match(
        match,
        seed=setup.seed,
        entry_fees=setup.entry_fees,
        reward_mode="shaped_pot",
    )

    # If there's a winner, check reward distribution
    if outcome.winner_team and outcome.winner_team != "draw":
        # Winners should get pot payout
        winner_fish_ids = outcome.teams.get(outcome.winner_team, [])
        assert len(winner_fish_ids) > 0

        # Check that winners got pot shares
        for fish_id in winner_fish_ids:
            energy_delta = outcome.energy_deltas.get(fish_id, 0.0)
            # Should be positive (pot share - entry fee + shaped bonus)
            assert energy_delta > -20.0, f"Winner {fish_id} should not lose much energy"

        # ALL players (winners and losers) should have shaped bonuses
        total_shaped = 0.0
        for fish in fish_participants:
            for log_entry in fish._energy_log:
                if "shaped" in log_entry["source"]:
                    total_shaped += log_entry["amount"]

        # Should have some shaped bonuses
        if match.telemetry.teams["left"].touches > 0 or match.telemetry.teams["right"].touches > 0:
            assert total_shaped > 0, "Expected shaped bonuses to all players even with a winner"


def test_shaped_pot_rewards_include_telemetry_in_outcome():
    """Verify that outcomes include telemetry when using shaped_pot."""
    fish_participants = [create_mock_fish(i, 100.0) for i in range(1, 5)]

    setup = create_soccer_match_from_participants(
        fish_participants,
        duration_frames=100,
        seed=42,
        entry_fee_energy=10.0,
    )
    match = setup.match

    while not match.game_over:
        match.step(num_steps=5)

    outcome = finalize_soccer_match(
        match,
        seed=setup.seed,
        entry_fees=setup.entry_fees,
        reward_mode="shaped_pot",
    )

    # Outcome should include telemetry
    assert outcome.telemetry is not None
    assert outcome.telemetry.total_cycles > 0
    assert "left" in outcome.telemetry.teams
    assert "right" in outcome.telemetry.teams


def test_pot_payout_mode_still_works():
    """Verify pot_payout mode still works correctly (regression test)."""
    fish_participants = [create_mock_fish(i, 100.0) for i in range(1, 5)]

    setup = create_soccer_match_from_participants(
        fish_participants,
        duration_frames=100,
        seed=42,
        entry_fee_energy=10.0,
    )
    match = setup.match

    while not match.game_over:
        match.step(num_steps=5)

    outcome = finalize_soccer_match(
        match,
        seed=setup.seed,
        entry_fees=setup.entry_fees,
        reward_mode="pot_payout",
    )

    # Should still have telemetry (it's always collected now)
    assert outcome.telemetry is not None

    # In pot_payout mode, no shaped bonuses should be applied
    total_shaped = 0.0
    for fish in fish_participants:
        for log_entry in fish._energy_log:
            if "shaped" in log_entry["source"]:
                total_shaped += log_entry["amount"]

    assert total_shaped == 0.0, "pot_payout mode should not apply shaped bonuses"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
