import random
from typing import Any, Optional, cast

import pytest

from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import AGGRESSION_MEDIUM
from core.poker.core.cards import Card, Rank, Suit
from core.poker.simulation import hand_engine
from core.poker.simulation import multiplayer_engine as multiplayer_engine
from core.poker.strategy.implementations.base import PokerStrategyAlgorithm


class DummyStrategy(PokerStrategyAlgorithm):
    def __init__(self) -> None:
        super().__init__(rng=random.Random(0))
        self.last_kwargs: dict[str, Any] = {}

    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: Optional[random.Random] = None,
    ) -> tuple[BettingAction, float]:
        self.last_kwargs = {
            "hand_strength": hand_strength,
            "current_bet": current_bet,
            "opponent_bet": opponent_bet,
            "pot": pot,
            "player_energy": player_energy,
            "position_on_button": position_on_button,
            "rng": rng,
        }
        return BettingAction.CHECK, 0.0


def test_simulate_multiplayer_game_rejects_two_players():
    with pytest.raises(ValueError):
        multiplayer_engine.simulate_multiplayer_game(
            num_players=2,
            initial_bet=10.0,
            player_energies=[100.0, 100.0],
        )


def test_simulate_multiplayer_game_uses_default_configs(monkeypatch):
    calls = {"betting": 0, "evaluate": 0}

    def fake_betting_rounds(game_state, **_kwargs):
        calls["betting"] += 1

    def fake_evaluate(game_state):
        calls["evaluate"] += 1

    monkeypatch.setattr(hand_engine, "_play_multiplayer_betting_rounds", fake_betting_rounds)
    monkeypatch.setattr(hand_engine, "_evaluate_multiplayer_hands", fake_evaluate)

    state = multiplayer_engine.simulate_multiplayer_game(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=None,
        player_strategies=None,
        button_position=0,
    )

    assert calls == {"betting": 1, "evaluate": 1}
    assert state.players[0].aggression == AGGRESSION_MEDIUM
    assert state.players[1].strategy is None


def test_create_multiplayer_game_state_posts_blinds_and_hole_cards():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.1, 0.2, 0.3],
        player_strategies=[None, None, None],
        button_position=0,
    )

    assert state.big_blind == 10.0
    assert state.small_blind == 5.0
    assert state.players[1].current_bet == 5.0
    assert state.players[2].current_bet == 10.0
    assert state.pot == 15.0
    assert state.players[1].remaining_energy == 95.0
    assert state.players[2].remaining_energy == 90.0
    assert all(len(player.hole_cards) == 2 for player in state.players.values())


def test_multiplayer_game_state_helpers():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.1, 0.2, 0.3],
        player_strategies=[None, None, None],
        button_position=0,
    )

    state.players[1].folded = True
    state.players[2].folded = True

    assert state.get_active_players() == [0]
    assert state.get_winner_by_fold() == 0

    state.players[1].folded = False
    state.players[2].folded = False
    state.players[0].current_bet = 4.0
    state.players[1].current_bet = 6.0
    state.players[2].current_bet = 2.0
    assert state.get_max_current_bet() == 6.0


def test_player_bet_sets_all_in_and_updates_pot():
    players = {
        0: multiplayer_engine.MultiplayerPlayerContext(
            player_id=0, remaining_energy=5.0, aggression=0.5
        ),
        1: multiplayer_engine.MultiplayerPlayerContext(
            player_id=1, remaining_energy=10.0, aggression=0.5
        ),
        2: multiplayer_engine.MultiplayerPlayerContext(
            player_id=2, remaining_energy=10.0, aggression=0.5
        ),
    }
    state = multiplayer_engine.MultiplayerGameState(num_players=3, players=players)

    state.player_bet(0, 10.0)

    assert state.players[0].current_bet == 5.0
    assert state.players[0].total_bet == 5.0
    assert state.players[0].remaining_energy == 0.0
    assert state.players[0].all_in is True
    assert state.pot == 5.0


def test_advance_round_deals_cards_and_resets_bets():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[0].current_bet = 10.0

    state.advance_round()
    assert state.current_round == BettingRound.FLOP
    assert all(player.current_bet == 0.0 for player in state.players.values())
    assert state.min_raise == state.big_blind
    assert state.last_raise_amount == state.big_blind
    assert len(state.community_cards) == 3

    state.advance_round()
    assert state.current_round == BettingRound.TURN
    assert len(state.community_cards) == 4

    state.advance_round()
    assert state.current_round == BettingRound.RIVER
    assert len(state.community_cards) == 5


def test_play_multiplayer_betting_rounds_auto_advances_when_only_one_can_act():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[1].all_in = True
    state.players[2].all_in = True

    hand_engine._play_multiplayer_betting_rounds(state, rng=random.Random(0))

    assert state.current_round == BettingRound.RIVER
    assert len(state.community_cards) == 5


def test_play_multiplayer_betting_rounds_breaks_on_fold_winner():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[1].folded = True
    state.players[2].folded = True

    hand_engine._play_multiplayer_betting_rounds(state, rng=random.Random(0))

    assert state.current_round == BettingRound.PRE_FLOP
    assert len(state.community_cards) == 0


def test_play_multiplayer_betting_rounds_advances_rounds(monkeypatch):
    seen = []

    def fake_play_round(game_state, hand_cache, round_num, **_kwargs):
        seen.append((round_num, len(hand_cache)))
        hand_cache[round_num] = "seen"

    monkeypatch.setattr(hand_engine, "_play_single_betting_round", fake_play_round)
    monkeypatch.setattr(hand_engine, "_refund_unmatched_bets", lambda *_: None)

    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )

    hand_engine._play_multiplayer_betting_rounds(state, rng=random.Random(0))

    assert state.current_round == BettingRound.RIVER
    assert seen[0][0] == 0
    assert any(round_num == 1 and cache_size == 0 for round_num, cache_size in seen)


def test_is_round_complete_requires_matching_bets_and_actions():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    for player in state.players.values():
        player.current_bet = 10.0
    state.players[2].current_bet = 5.0

    assert not hand_engine._is_round_complete(state, 0, {0, 1}, 0)

    state.players[2].current_bet = 10.0
    assert not hand_engine._is_round_complete(state, 0, {0, 1}, 0)
    assert hand_engine._is_round_complete(state, 0, {0, 1, 2}, 0)

    state.players[1].folded = True
    state.players[2].folded = True
    assert hand_engine._is_round_complete(state, 0, {0}, 0)


def test_decide_multiplayer_action_strategy_preflop_uses_starting_strength(monkeypatch):
    strategy = DummyStrategy()
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[strategy, None, None],
        button_position=0,
    )
    state.community_cards = []

    monkeypatch.setattr(hand_engine, "evaluate_starting_hand_strength", lambda *_: 0.33)

    action, amount = hand_engine._decide_multiplayer_action(0, state, {}, rng=random.Random(0))

    assert action == BettingAction.CHECK
    assert amount == 0.0
    assert strategy.last_kwargs["hand_strength"] == 0.33
    assert strategy.last_kwargs["position_on_button"] is True


def test_decide_multiplayer_action_strategy_postflop_uses_rank_value(monkeypatch):
    strategy = DummyStrategy()

    class DummyHand:
        rank_value = 5  # Arbitrary value, not used directly
        primary_ranks = [14]  # Ace high
        kickers = []

    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[strategy, None, None],
        button_position=1,
    )
    state.community_cards = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.SPADES),
    ]

    monkeypatch.setattr(hand_engine, "evaluate_hand", lambda *_: DummyHand())
    monkeypatch.setattr(hand_engine, "evaluate_hand_strength", lambda *_: 0.5)
    monkeypatch.setattr(
        hand_engine,
        "evaluate_starting_hand_strength",
        lambda *_: pytest.fail("Should not call preflop evaluation postflop"),
    )

    action, amount = hand_engine._decide_multiplayer_action(0, state, {}, rng=random.Random(0))

    assert action == BettingAction.CHECK
    assert amount == 0.0
    assert strategy.last_kwargs["hand_strength"] == 0.5


def test_decide_multiplayer_action_default_uses_decide_action(monkeypatch):
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )

    monkeypatch.setattr(hand_engine, "decide_action", lambda **_: (BettingAction.CHECK, 0.0))

    action, amount = hand_engine._decide_multiplayer_action(0, state, {}, rng=random.Random(0))

    assert action == BettingAction.CHECK
    assert amount == 0.0


def test_apply_multiplayer_action_fold_and_check():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )

    result = hand_engine._apply_multiplayer_action(0, BettingAction.FOLD, 0.0, state)
    assert result is False
    assert state.players[0].folded is True
    assert state.betting_history[-1] == (0, BettingAction.FOLD, 0.0)

    result = hand_engine._apply_multiplayer_action(1, BettingAction.CHECK, 0.0, state)
    assert result is False
    assert state.betting_history[-1] == (1, BettingAction.CHECK, 0.0)


def test_apply_multiplayer_action_call_updates_bet():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[0].current_bet = 5.0
    state.players[1].current_bet = 10.0
    state.players[2].current_bet = 10.0

    result = hand_engine._apply_multiplayer_action(0, BettingAction.CALL, 0.0, state)
    assert result is False
    assert state.players[0].current_bet == 10.0
    assert state.betting_history[-1] == (0, BettingAction.CALL, 5.0)


def test_apply_multiplayer_action_raise_updates_min_raise():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[1].current_bet = 10.0
    state.players[0].current_bet = 0.0

    result = hand_engine._apply_multiplayer_action(0, BettingAction.RAISE, 12.0, state)

    assert result is True
    assert state.last_raise_amount == 12.0
    assert state.min_raise == 12.0
    assert state.betting_history[-1] == (0, BettingAction.RAISE, 12.0)


def test_apply_multiplayer_action_raise_downgrades_to_call_when_min_raise_zero():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=0.0,
        player_energies=[10.0, 10.0, 10.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.min_raise = 0.0
    state.players[0].current_bet = 0.0

    result = hand_engine._apply_multiplayer_action(0, BettingAction.RAISE, 0.0, state)

    assert result is False
    assert state.betting_history[-1] == (0, BettingAction.CALL, 0.0)


def test_apply_multiplayer_action_unknown_returns_false():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )

    result = hand_engine._apply_multiplayer_action(0, cast(BettingAction, "UNKNOWN"), 0.0, state)

    assert result is False


def test_refund_unmatched_bets_refunds_excess():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[0].current_bet = 20.0
    state.players[1].current_bet = 10.0
    state.players[2].current_bet = 10.0
    state.players[0].total_bet = 20.0
    state.players[1].total_bet = 10.0
    state.players[2].total_bet = 10.0
    state.pot = 40.0

    hand_engine._refund_unmatched_bets(state)

    assert state.players[0].current_bet == 10.0
    assert state.players[0].total_bet == 10.0
    assert state.players[0].remaining_energy == 110.0
    assert state.pot == 30.0


def test_refund_unmatched_bets_skips_when_only_one_active():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[1].folded = True
    state.players[2].folded = True
    state.pot = 25.0

    hand_engine._refund_unmatched_bets(state)

    assert state.pot == 25.0


def test_evaluate_multiplayer_hands_sets_none_for_folded():
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )
    state.players[1].folded = True
    state.community_cards = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.THREE, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.DIAMONDS),
    ]

    hand_engine._evaluate_multiplayer_hands(state)

    assert state.player_hands[1] is None
    assert state.player_hands[0] is not None
    assert state.player_hands[2] is not None


def test_play_single_betting_round_records_actions():
    strategy = DummyStrategy()
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[strategy, strategy, strategy],
        button_position=0,
    )
    for player in state.players.values():
        player.current_bet = 0.0

    hand_engine._play_single_betting_round(state, {}, 0, rng=random.Random(0))

    assert len(state.betting_history) == 3
    assert all(action == BettingAction.CHECK for _, action, _ in state.betting_history)


def test_play_single_betting_round_skips_folded_player_postflop():
    strategy = DummyStrategy()
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[strategy, strategy, strategy],
        button_position=2,
    )
    for player in state.players.values():
        player.current_bet = 0.0
    state.players[0].folded = True

    hand_engine._play_single_betting_round(state, {}, 1, rng=random.Random(0))

    assert all(pid != 0 for pid, _, _ in state.betting_history)


def test_play_single_betting_round_updates_last_raiser(monkeypatch):
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )

    monkeypatch.setattr(
        hand_engine,
        "_decide_multiplayer_action",
        lambda **_: (BettingAction.RAISE, 5.0),
    )
    monkeypatch.setattr(hand_engine, "_apply_multiplayer_action", lambda **_: True)

    hand_engine._play_single_betting_round(state, {}, 0, rng=random.Random(0))

    assert state.betting_history == []


def test_play_single_betting_round_breaks_on_fold_victory(monkeypatch):
    state = hand_engine._create_multiplayer_game_state(
        num_players=3,
        initial_bet=10.0,
        player_energies=[100.0, 100.0, 100.0],
        player_aggressions=[0.5, 0.5, 0.5],
        player_strategies=[None, None, None],
        button_position=0,
    )

    def fake_apply(player_id, action, bet_amount, game_state):
        game_state.betting_history.append((player_id, action, 0.0))
        for pid, player in game_state.players.items():
            if pid != player_id:
                player.folded = True
        return False

    monkeypatch.setattr(
        hand_engine,
        "_decide_multiplayer_action",
        lambda **_: (BettingAction.CHECK, 0.0),
    )
    monkeypatch.setattr(hand_engine, "_apply_multiplayer_action", fake_apply)

    hand_engine._play_single_betting_round(state, {}, 0, rng=random.Random(0))

    assert len(state.betting_history) == 1
    assert state.get_winner_by_fold() is not None
