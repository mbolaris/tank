"""Verification tests for GTOExpertStrategy."""

import random
from core.poker.betting.actions import BettingAction
from core.poker.strategy.implementations.expert import GTOExpertStrategy


def test_expert_initialization():
    rng = random.Random(42)
    strategy = GTOExpertStrategy(rng=rng)
    assert strategy.strategy_id == "gto_expert"
    assert "bluff_efficiency" in strategy.parameters
    assert "value_sizing_efficiency" in strategy.parameters


def test_expert_value_bet_behavior():
    rng = random.Random(42)
    strategy = GTOExpertStrategy(rng=rng)

    # Strong hand (0.95), we are aggressor (call_amount=0)
    action, amount = strategy.decide_action(
        hand_strength=0.95,
        current_bet=100,
        opponent_bet=100,
        pot=200,
        player_energy=1000,
        position_on_button=True,
    )

    # Should raise for value
    assert action == BettingAction.RAISE
    assert amount > 100  # Should be substantial raise


def test_expert_bluff_behavior():
    rng = random.Random(42)
    strategy = GTOExpertStrategy(rng=rng)
    # Force bluff efficiency to max to encourage bluffing
    strategy.parameters["bluff_efficiency"] = 20.0

    # Weak hand (< 0.3), call_amount=0
    # We should bluff sometimes
    bluff_count = 0
    trials = 100
    for _ in range(trials):
        action, _ = strategy.decide_action(
            hand_strength=0.1,  # Weak
            current_bet=100,
            opponent_bet=100,
            pot=200,
            player_energy=1000,
            position_on_button=True,
        )
        if action == BettingAction.RAISE:
            bluff_count += 1

    # Should verify that it bluffs at least once (with high efficiency forced)
    # With normal efficiency it's probabilistic
    assert bluff_count > 0


def test_expert_fold_vs_aggression():
    rng = random.Random(42)
    strategy = GTOExpertStrategy(rng=rng)

    # Weak hand (0.1) vs big bet (pot sized)
    # Pot = 200, Opponent bets 200 (Total pot 400). Call = 200.
    # Pot odds = 0.33. Hand strength 0.1 < 0.33. Should fold.

    action, _ = strategy.decide_action(
        hand_strength=0.1,
        current_bet=0,
        opponent_bet=200,
        pot=200,
        player_energy=1000,
        position_on_button=False,
    )

    assert action == BettingAction.FOLD
