import logging

import pytest

from core.config.poker import POKER_MAX_HAND_RANK
from core.poker.betting.actions import BettingAction
from core.poker.core.cards import Card, Rank, Suit
from core.poker.core.game_state import PokerGameState
from core.poker.core import evaluate_hand
from core.poker.simulation import engine as simulation_engine


class DummyStrategy:
    def __init__(self) -> None:
        self.last_kwargs = None

    def decide_action(self, **kwargs):
        self.last_kwargs = kwargs
        return BettingAction.CHECK, 0.0


class AlwaysCallStrategy:
    def decide_action(self, **kwargs):
        current_bet = kwargs["current_bet"]
        opponent_bet = kwargs["opponent_bet"]
        if opponent_bet > current_bet:
            return BettingAction.CALL, opponent_bet - current_bet
        return BettingAction.CHECK, 0.0


def test_resolve_aggression_returns_default_and_custom():
    assert simulation_engine._resolve_aggression(None) == simulation_engine.AGGRESSION_MEDIUM
    assert simulation_engine._resolve_aggression(0.9) == 0.9


def test_create_game_state_button_position_two_posts_blinds():
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=50.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=50.0, aggression=0.5, strategy=None),
    }

    state = simulation_engine._create_game_state(10.0, 2, contexts)

    assert state.button_position == 2
    assert state.player1_current_bet == state.big_blind
    assert state.player2_current_bet == state.small_blind
    assert contexts[1].remaining_energy == 40.0
    assert contexts[2].remaining_energy == 45.0


def test_decide_player_action_strategy_preflop_uses_starting_hand_strength(monkeypatch):
    strategy = DummyStrategy()

    monkeypatch.setattr(simulation_engine, "evaluate_starting_hand_strength", lambda *_: 0.42)
    monkeypatch.setattr(
        simulation_engine,
        "_evaluate_hand_for_player",
        lambda *_: pytest.fail("Should not evaluate post-flop hand on preflop"),
    )

    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    state.player1_hole_cards = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)]
    state.player2_hole_cards = [Card(Rank.TEN, Suit.SPADES), Card(Rank.TEN, Suit.HEARTS)]
    state.community_cards = []

    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=100.0, aggression=0.5, strategy=strategy),
        2: simulation_engine.PlayerContext(remaining_energy=100.0, aggression=0.5, strategy=None),
    }
    hand_cache = simulation_engine._HandEvaluationCache(community_cards_seen=0, hands={})

    action, amount = simulation_engine._decide_player_action(
        current_player=1,
        game_state=state,
        contexts=contexts,
        button_position=1,
        hand_cache=hand_cache,
        rng=None,
    )

    assert action == BettingAction.CHECK
    assert amount == 0.0
    assert strategy.last_kwargs["hand_strength"] == 0.42
    assert strategy.last_kwargs["position_on_button"] is True


def test_decide_player_action_strategy_postflop_uses_rank_value(monkeypatch):
    strategy = DummyStrategy()

    class DummyHand:
        rank_value = POKER_MAX_HAND_RANK / 2

    monkeypatch.setattr(
        simulation_engine,
        "_evaluate_hand_for_player",
        lambda *_: DummyHand(),
    )
    monkeypatch.setattr(
        simulation_engine,
        "evaluate_starting_hand_strength",
        lambda *_: pytest.fail("Should not call preflop evaluation postflop"),
    )

    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=2)
    state.player1_hole_cards = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)]
    state.player2_hole_cards = [Card(Rank.TEN, Suit.SPADES), Card(Rank.TEN, Suit.HEARTS)]
    state.community_cards = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.SPADES),
    ]

    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=100.0, aggression=0.5, strategy=strategy),
        2: simulation_engine.PlayerContext(remaining_energy=100.0, aggression=0.5, strategy=None),
    }
    hand_cache = simulation_engine._HandEvaluationCache(
        community_cards_seen=len(state.community_cards), hands={}
    )

    action, amount = simulation_engine._decide_player_action(
        current_player=1,
        game_state=state,
        contexts=contexts,
        button_position=2,
        hand_cache=hand_cache,
        rng=None,
    )

    assert action == BettingAction.CHECK
    assert amount == 0.0
    assert strategy.last_kwargs["hand_strength"] == 0.5


def test_evaluate_hand_for_player_cache_invalidation():
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    state.player1_hole_cards = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.CLUBS)]
    state.player2_hole_cards = [Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)]
    state.community_cards = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.SPADES),
    ]

    hand_cache = simulation_engine._HandEvaluationCache(community_cards_seen=0, hands={1: "sentinel"})
    first = simulation_engine._evaluate_hand_for_player(1, state, hand_cache)
    second = simulation_engine._evaluate_hand_for_player(1, state, hand_cache)

    assert hand_cache.community_cards_seen == 3
    assert hand_cache.hands[1] is first
    assert first is second

    state.community_cards.append(Card(Rank.JACK, Suit.SPADES))
    third = simulation_engine._evaluate_hand_for_player(1, state, hand_cache)

    assert third is not first
    assert hand_cache.community_cards_seen == 4


def test_apply_action_unknown_logs_warning(caplog):
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
    }

    with caplog.at_level(logging.WARNING):
        result = simulation_engine._apply_action(
            current_player=1,
            action="UNKNOWN",
            bet_amount=0.0,
            remaining_energy=10.0,
            game_state=state,
            contexts=contexts,
        )

    assert result is False
    assert any("Unknown betting action" in message for message in caplog.messages)


def test_apply_action_fold_marks_player():
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
    }

    result = simulation_engine._apply_action(
        current_player=1,
        action=BettingAction.FOLD,
        bet_amount=0.0,
        remaining_energy=10.0,
        game_state=state,
        contexts=contexts,
    )

    assert result is True
    assert state.player1_folded is True
    assert state.betting_history[-1] == (1, BettingAction.FOLD, 0.0)


def test_apply_action_fold_marks_player_two():
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
    }

    result = simulation_engine._apply_action(
        current_player=2,
        action=BettingAction.FOLD,
        bet_amount=0.0,
        remaining_energy=10.0,
        game_state=state,
        contexts=contexts,
    )

    assert result is True
    assert state.player2_folded is True
    assert state.betting_history[-1] == (2, BettingAction.FOLD, 0.0)


def test_apply_action_check_records_history():
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
    }

    result = simulation_engine._apply_action(
        current_player=1,
        action=BettingAction.CHECK,
        bet_amount=0.0,
        remaining_energy=10.0,
        game_state=state,
        contexts=contexts,
    )

    assert result is False
    assert state.betting_history[-1] == (1, BettingAction.CHECK, 0.0)


def test_apply_action_call_matches_bet():
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    state.player_bet(1, 5.0)
    state.player_bet(2, 10.0)
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=10.0, aggression=0.5, strategy=None),
    }

    result = simulation_engine._apply_action(
        current_player=1,
        action=BettingAction.CALL,
        bet_amount=0.0,
        remaining_energy=contexts[1].remaining_energy,
        game_state=state,
        contexts=contexts,
    )

    assert result is False
    assert state.player1_current_bet == state.player2_current_bet
    assert contexts[1].remaining_energy == 5.0


def test_apply_action_raise_updates_min_raise():
    state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    state.player_bet(1, 10.0)
    state.player_bet(2, 10.0)
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=50.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=50.0, aggression=0.5, strategy=None),
    }

    result = simulation_engine._apply_action(
        current_player=1,
        action=BettingAction.RAISE,
        bet_amount=5.0,
        remaining_energy=contexts[1].remaining_energy,
        game_state=state,
        contexts=contexts,
    )

    assert result is False
    assert state.last_raise_amount == 10.0
    assert state.min_raise == 10.0
    assert state.betting_history[-1] == (1, BettingAction.RAISE, 10.0)


def test_apply_action_raise_downgrades_to_call_when_under_minimum():
    state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    state.player_bet(1, 10.0)
    state.player_bet(2, 20.0)
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=5.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=50.0, aggression=0.5, strategy=None),
    }

    result = simulation_engine._apply_action(
        current_player=1,
        action=BettingAction.RAISE,
        bet_amount=50.0,
        remaining_energy=contexts[1].remaining_energy,
        game_state=state,
        contexts=contexts,
    )

    assert result is True
    assert state.betting_history[-1] == (1, BettingAction.CALL, 5.0)
    assert state.player1_current_bet == 15.0
    assert contexts[1].remaining_energy == 0.0


def test_resolve_bet_handles_non_tie_outcomes():
    community = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.SPADES),
        Card(Rank.JACK, Suit.HEARTS),
        Card(Rank.FOUR, Suit.CLUBS),
    ]
    hand1 = evaluate_hand(
        [Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.CLUBS)],
        community,
    )
    hand2 = evaluate_hand(
        [Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)],
        community,
    )

    assert simulation_engine.resolve_bet(hand1, hand2, 10.0, 5.0) == (5.0, -5.0)
    assert simulation_engine.resolve_bet(hand2, hand1, 10.0, 5.0) == (-10.0, 10.0)


def test_resolve_bet_handles_tie():
    community = [
        Card(Rank.TEN, Suit.CLUBS),
        Card(Rank.JACK, Suit.DIAMONDS),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.ACE, Suit.CLUBS),
    ]
    hand1 = evaluate_hand(
        [Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.SPADES)],
        community,
    )
    hand2 = evaluate_hand(
        [Card(Rank.FOUR, Suit.HEARTS), Card(Rank.SIX, Suit.SPADES)],
        community,
    )

    assert simulation_engine.resolve_bet(hand1, hand2, 10.0, 10.0) == (0.0, 0.0)


def test_finalize_pot_covers_fold_and_hand_win_for_player_two():
    fold_state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    fold_state.pot = 60.0
    fold_state.player2_folded = True

    assert simulation_engine.finalize_pot(fold_state) == (60.0, 0.0)

    win_state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    win_state.pot = 80.0
    win_state.player1_hole_cards = [Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)]
    win_state.player2_hole_cards = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.CLUBS)]
    win_state.community_cards = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.THREE, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.DIAMONDS),
    ]

    assert simulation_engine.finalize_pot(win_state) == (0.0, 80.0)


def test_finalize_pot_handles_player_one_fold_and_split():
    fold_state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    fold_state.pot = 50.0
    fold_state.player1_folded = True

    assert simulation_engine.finalize_pot(fold_state) == (0.0, 50.0)

    split_state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    split_state.pot = 100.0
    split_state.player1_hole_cards = [Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.SPADES)]
    split_state.player2_hole_cards = [Card(Rank.FOUR, Suit.HEARTS), Card(Rank.SIX, Suit.HEARTS)]
    split_state.community_cards = [
        Card(Rank.TEN, Suit.CLUBS),
        Card(Rank.JACK, Suit.DIAMONDS),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.ACE, Suit.CLUBS),
    ]

    assert simulation_engine.finalize_pot(split_state) == (50.0, 50.0)


def test_finalize_pot_handles_player_one_hand_win():
    win_state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    win_state.pot = 70.0
    win_state.player1_hole_cards = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.CLUBS)]
    win_state.player2_hole_cards = [Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)]
    win_state.community_cards = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.THREE, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.DIAMONDS),
    ]

    assert simulation_engine.finalize_pot(win_state) == (70.0, 0.0)


def test_build_player_contexts_returns_mapping():
    contexts = simulation_engine._build_player_contexts(
        player1_energy=10.0,
        player2_energy=12.0,
        player1_aggression=0.1,
        player2_aggression=0.9,
        player1_strategy=None,
        player2_strategy=None,
    )

    assert contexts[1].remaining_energy == 10.0
    assert contexts[2].remaining_energy == 12.0
    assert contexts[1].aggression == 0.1
    assert contexts[2].aggression == 0.9


def test_calculate_call_amount_for_each_player():
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    state.player1_current_bet = 4.0
    state.player2_current_bet = 10.0

    assert simulation_engine._calculate_call_amount(1, state) == 6.0
    assert simulation_engine._calculate_call_amount(2, state) == 0.0


def test_calculate_actual_raise_respects_min_raise_and_cap():
    state = PokerGameState(small_blind=1.0, big_blind=10.0, button_position=1)

    assert simulation_engine._calculate_actual_raise(
        bet_amount=15.0, available_energy=5.0, game_state=state
    ) == 0.0
    assert simulation_engine._calculate_actual_raise(
        bet_amount=5.0, available_energy=20.0, game_state=state
    ) == 10.0
    assert simulation_engine._calculate_actual_raise(
        bet_amount=15.0, available_energy=12.0, game_state=state
    ) == 12.0


def test_round_is_complete_requires_equal_bets_and_two_actions():
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    state.player1_current_bet = 5.0
    state.player2_current_bet = 5.0

    assert simulation_engine._round_is_complete(state, actions_this_round=1) is False
    assert simulation_engine._round_is_complete(state, actions_this_round=2) is True


@pytest.mark.parametrize(
    ("player1_bet", "player2_bet", "expected_refund_player"),
    [(20.0, 10.0, 1), (10.0, 25.0, 2)],
)
def test_refund_unmatched_bets_refunds_excess(player1_bet, player2_bet, expected_refund_player):
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    state.player1_current_bet = player1_bet
    state.player2_current_bet = player2_bet
    state.player1_total_bet = player1_bet
    state.player2_total_bet = player2_bet
    state.pot = player1_bet + player2_bet
    contexts = {
        1: simulation_engine.PlayerContext(remaining_energy=0.0, aggression=0.5, strategy=None),
        2: simulation_engine.PlayerContext(remaining_energy=0.0, aggression=0.5, strategy=None),
    }

    simulation_engine._refund_unmatched_bets(state, contexts)

    assert state.player1_current_bet == state.player2_current_bet
    if expected_refund_player == 1:
        assert contexts[1].remaining_energy > 0.0
    else:
        assert contexts[2].remaining_energy > 0.0


@pytest.mark.parametrize("player1_folded,player2_folded", [(True, False), (False, True)])
def test_evaluate_final_hands_respects_folds(player1_folded, player2_folded):
    state = PokerGameState(small_blind=1.0, big_blind=2.0, button_position=1)
    state.player1_folded = player1_folded
    state.player2_folded = player2_folded
    state.player1_hole_cards = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.CLUBS)]
    state.player2_hole_cards = [Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)]
    state.community_cards = [
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.THREE, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.NINE, Suit.DIAMONDS),
    ]

    simulation_engine._evaluate_final_hands(state)

    if player1_folded:
        assert state.player1_hand is None
        assert state.player2_hand is not None
    else:
        assert state.player1_hand is not None
        assert state.player2_hand is None


def test_simulate_multi_round_game_with_strategies_reaches_showdown():
    strategy = AlwaysCallStrategy()

    game_state = simulation_engine.simulate_multi_round_game(
        initial_bet=10.0,
        player1_energy=100.0,
        player2_energy=100.0,
        player1_strategy=strategy,
        player2_strategy=strategy,
        rng=None,
    )

    assert game_state.current_round == simulation_engine.BettingRound.SHOWDOWN
    assert game_state.get_winner_by_fold() is None
    assert game_state.player1_hand is not None
    assert game_state.player2_hand is not None


def test_play_betting_rounds_exits_when_fold_already_set():
    contexts = simulation_engine._build_player_contexts(
        player1_energy=20.0,
        player2_energy=20.0,
        player1_aggression=0.5,
        player2_aggression=0.5,
        player1_strategy=None,
        player2_strategy=None,
    )
    state = PokerGameState(small_blind=5.0, big_blind=10.0, button_position=1)
    state.player1_folded = True

    simulation_engine._play_betting_rounds(state, contexts, button_position=1, rng=None)

    assert state.get_winner_by_fold() == 2


def test_play_betting_rounds_breaks_on_fold_action(monkeypatch):
    strategy = AlwaysCallStrategy()
    contexts = simulation_engine._build_player_contexts(
        player1_energy=20.0,
        player2_energy=20.0,
        player1_aggression=0.5,
        player2_aggression=0.5,
        player1_strategy=strategy,
        player2_strategy=strategy,
    )
    state = simulation_engine._create_game_state(10.0, 1, contexts)

    monkeypatch.setattr(
        simulation_engine,
        "_decide_player_action",
        lambda **_: (BettingAction.FOLD, 0.0),
    )

    simulation_engine._play_betting_rounds(state, contexts, button_position=1, rng=None)

    assert state.get_winner_by_fold() is not None


def test_simulate_game_calls_multi_round():
    game_state = simulation_engine.simulate_game(bet_amount=5.0, player1_energy=20.0, player2_energy=20.0)

    assert isinstance(game_state, PokerGameState)
