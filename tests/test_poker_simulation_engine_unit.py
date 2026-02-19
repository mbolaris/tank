import random

import pytest

from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.core import evaluate_hand
from core.poker.core.cards import Card, Rank, Suit
from core.poker.core.game_state import PokerGameState
from core.poker.simulation import engine as simulation_engine
from core.poker.simulation import hand_engine
from core.poker.strategy.implementations.base import PokerStrategyAlgorithm


class AlwaysCallStrategy(PokerStrategyAlgorithm):
    def decide_action(
        self,
        hand_strength: float,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        position_on_button: bool = False,
        rng: random.Random | None = None,
    ) -> tuple[BettingAction, float]:
        if opponent_bet > current_bet:
            return BettingAction.CALL, opponent_bet - current_bet
        return BettingAction.CHECK, 0.0


def test_resolve_aggression_returns_default_and_custom():
    assert simulation_engine._resolve_aggression(None) == simulation_engine.AGGRESSION_MEDIUM
    assert simulation_engine._resolve_aggression(0.9) == 0.9


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


def test_finalize_pot_covers_fold_and_split():
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


def test_finalize_pot_handles_hand_win_for_player_two():
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


def test_simulate_multi_round_game_with_strategies_reaches_showdown():
    strategy = AlwaysCallStrategy()

    game_state = simulation_engine.simulate_multi_round_game(
        initial_bet=10.0,
        player1_energy=100.0,
        player2_energy=100.0,
        player1_strategy=strategy,
        player2_strategy=strategy,
        rng=random.Random(0),
    )

    assert game_state.current_round == BettingRound.SHOWDOWN
    assert game_state.get_winner_by_fold() is None
    assert game_state.player1_hand is not None
    assert game_state.player2_hand is not None


@pytest.mark.parametrize("button_position", [1, 2])
def test_simulate_multi_round_game_matches_hand_engine(button_position):
    rng_seed = 123
    rng_hand = random.Random(rng_seed)
    rng_engine = random.Random(rng_seed)

    hand_state = hand_engine.simulate_hand(
        num_players=2,
        initial_bet=10.0,
        player_energies=[100.0, 100.0],
        player_aggressions=[0.5, 0.5],
        player_strategies=[AlwaysCallStrategy(), AlwaysCallStrategy()],
        button_position=button_position - 1,
        rng=rng_hand,
    )

    game_state = simulation_engine.simulate_multi_round_game(
        initial_bet=10.0,
        player1_energy=100.0,
        player2_energy=100.0,
        player1_strategy=AlwaysCallStrategy(),
        player2_strategy=AlwaysCallStrategy(),
        button_position=button_position,
        rng=rng_engine,
    )

    assert game_state.current_round == hand_state.current_round
    assert game_state.pot == hand_state.pot
    assert game_state.min_raise == hand_state.min_raise
    assert game_state.last_raise_amount == hand_state.last_raise_amount
    assert game_state.community_cards == hand_state.community_cards
    assert game_state.player1_hole_cards == hand_state.players[0].hole_cards
    assert game_state.player2_hole_cards == hand_state.players[1].hole_cards
    assert game_state.player1_folded == hand_state.players[0].folded
    assert game_state.player2_folded == hand_state.players[1].folded
    assert game_state.player1_total_bet == hand_state.players[0].total_bet
    assert game_state.player2_total_bet == hand_state.players[1].total_bet


def test_simulate_game_returns_state():
    game_state = simulation_engine.simulate_game(
        bet_amount=5.0,
        player1_energy=20.0,
        player2_energy=20.0,
    )

    assert isinstance(game_state, PokerGameState)
