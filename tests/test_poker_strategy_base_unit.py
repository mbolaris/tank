import math

import pytest

from core.poker.strategy.base import OpponentModel, PokerStrategyEngine


class DummyFish:
    pass


class FixedRng:
    def __init__(self, value: float) -> None:
        self._value = value

    def random(self) -> float:
        return self._value


def test_opponent_model_update_and_style():
    model = OpponentModel(fish_id=1)
    updates = [
        dict(won=True, folded=False, raised=True, called=False, aggression=0.8, frame=10),
        dict(won=False, folded=False, raised=False, called=True, aggression=0.4, frame=11),
        dict(won=True, folded=False, raised=False, called=True, aggression=0.6, frame=12),
        dict(won=False, folded=False, raised=False, called=True, aggression=0.3, frame=13),
        dict(won=False, folded=True, raised=False, called=False, aggression=0.2, frame=14),
    ]

    for update in updates:
        model.update_from_game(**update)

    assert model.games_played == 5
    assert model.hands_won == 2
    assert model.hands_lost == 3
    assert model.times_folded == 1
    assert model.times_raised == 1
    assert model.times_called == 3
    assert math.isclose(model.avg_aggression, 0.46, rel_tol=0.0, abs_tol=1e-6)
    assert model.is_tight is False
    assert model.is_aggressive is False
    assert model.is_passive is True
    assert model.get_style_description() == "loose-passive"
    assert math.isclose(model.bluff_frequency, 0.5, rel_tol=0.0, abs_tol=1e-6)
    assert model.last_seen_frame == 14
    assert math.isclose(model.get_win_rate(), 0.4, rel_tol=0.0, abs_tol=1e-6)


def test_opponent_model_defaults_when_unseen():
    model = OpponentModel(fish_id=2)

    assert model.get_win_rate() == 0.5
    assert model.get_style_description() == "unknown"


def test_evaluate_starting_hand_strength_valid_and_invalid():
    engine = PokerStrategyEngine(DummyFish())

    assert engine.evaluate_starting_hand_strength([("A", "s")]) == 0.5
    assert engine.evaluate_starting_hand_strength([("1", "s"), ("A", "h")]) == 0.5
    assert engine.evaluate_starting_hand_strength([("A", "x"), ("A", "h")]) == 0.5

    strength = engine.evaluate_starting_hand_strength([("A", "s"), ("A", "h")])
    assert strength >= 0.95


def test_should_play_hand_position_and_opponent(monkeypatch):
    engine = PokerStrategyEngine(DummyFish())

    monkeypatch.setattr(engine, "evaluate_starting_hand_strength", lambda *_: 0.83)
    assert engine.should_play_hand([("A", "s"), ("K", "h")], position_on_button=True) is True
    assert engine.should_play_hand([("A", "s"), ("K", "h")], position_on_button=False) is False

    monkeypatch.setattr(engine, "evaluate_starting_hand_strength", lambda *_: 0.91)
    model = engine.get_opponent_model(7)
    model.games_played = 5
    model.is_tight = True
    assert (
        engine.should_play_hand(
            [("A", "s"), ("K", "h")], position_on_button=False, opponent_id=7
        )
        is True
    )


def test_calculate_adjusted_aggression_accounts_for_position_opponent_and_hand():
    engine = PokerStrategyEngine(DummyFish())
    model = engine.get_opponent_model(5)
    model.games_played = 5
    model.is_tight = True

    adjusted = engine.calculate_adjusted_aggression(
        base_aggression=0.5,
        position_on_button=True,
        opponent_id=5,
        hand_strength=0.85,
    )

    assert math.isclose(adjusted, 0.875, rel_tol=0.0, abs_tol=1e-6)


def test_calculate_adjusted_aggression_clamps_low_values():
    engine = PokerStrategyEngine(DummyFish())
    model = engine.get_opponent_model(6)
    model.games_played = 5
    model.is_aggressive = True

    adjusted = engine.calculate_adjusted_aggression(
        base_aggression=0.4,
        position_on_button=False,
        opponent_id=6,
        hand_strength=0.2,
    )

    assert math.isclose(adjusted, 0.3, rel_tol=0.0, abs_tol=1e-6)


def test_should_bluff_uses_probabilities():
    engine = PokerStrategyEngine(DummyFish())
    engine.bluff_frequency = 0.2

    assert engine.should_bluff(
        position_on_button=False,
        hand_strength=0.5,
        rng=FixedRng(0.23),
    ) is True
    assert engine.should_bluff(
        position_on_button=False,
        hand_strength=0.5,
        rng=FixedRng(0.25),
    ) is False


def test_learn_from_poker_outcome_updates_on_win():
    engine = PokerStrategyEngine(DummyFish())

    engine.learn_from_poker_outcome(
        won=True,
        hand_strength=0.3,
        position_on_button=True,
        bluffed=True,
    )

    assert math.isclose(engine.bluff_frequency, 0.225, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(engine.positional_awareness, 0.55, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(engine.hand_selection_tightness, 0.45, rel_tol=0.0, abs_tol=1e-6)


def test_learn_from_poker_outcome_updates_on_loss():
    engine = PokerStrategyEngine(DummyFish())
    engine.bluff_frequency = 0.225
    engine.hand_selection_tightness = 0.45

    engine.learn_from_poker_outcome(
        won=False,
        hand_strength=0.4,
        position_on_button=False,
        bluffed=True,
    )

    assert math.isclose(engine.bluff_frequency, 0.21, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(engine.hand_selection_tightness, 0.475, rel_tol=0.0, abs_tol=1e-6)


def test_strategy_and_opponent_summaries():
    engine = PokerStrategyEngine(DummyFish())
    model_a = engine.get_opponent_model(1)
    model_b = engine.get_opponent_model(2)

    model_a.games_played = 5
    model_a.hands_won = 3
    model_a.avg_aggression = 0.6
    model_a.bluff_frequency = 0.2
    model_a.is_aggressive = True
    model_b.games_played = 3

    summary = engine.get_strategy_summary()
    assert summary["opponents_tracked"] == 2
    assert summary["opponents_modeled"] == 1

    assert engine.get_opponent_summary(999) == {}

    opponent_summary = engine.get_opponent_summary(1)
    assert opponent_summary["games_played"] == 5
    assert math.isclose(opponent_summary["win_rate"], 0.6, rel_tol=0.0, abs_tol=1e-6)
    assert opponent_summary["style"] == "loose-aggressive"
    assert math.isclose(opponent_summary["avg_aggression"], 0.6, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(opponent_summary["bluff_frequency"], 0.2, rel_tol=0.0, abs_tol=1e-6)
