import random
from typing import Optional

import pytest

from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.core.cards import Card, Rank, Suit
from core.poker.simulation.hand_engine import (Deal, determine_payouts,
                                               simulate_hand_from_deal)
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
        rng: Optional[random.Random] = None,
    ) -> tuple[BettingAction, float]:
        if opponent_bet > current_bet:
            return BettingAction.CALL, opponent_bet - current_bet
        return BettingAction.CHECK, 0.0


def test_simulate_hand_from_deal_uses_board_and_reaches_showdown():
    deal = Deal(
        hole_cards={
            0: [Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.DIAMONDS)],
            1: [Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.CLUBS)],
        },
        community_cards=[
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.DIAMONDS),
            Card(Rank.NINE, Suit.SPADES),
            Card(Rank.JACK, Suit.HEARTS),
            Card(Rank.FOUR, Suit.CLUBS),
        ],
        button_position=0,
    )

    game_state = simulate_hand_from_deal(
        deal=deal,
        initial_bet=10.0,
        player_energies=[100.0, 100.0],
        player_aggressions=[0.5, 0.5],
        player_strategies=[AlwaysCallStrategy(), AlwaysCallStrategy()],
        small_blind=5.0,
        rng=random.Random(0),
    )

    assert game_state.current_round == BettingRound.SHOWDOWN
    assert game_state.community_cards == deal.community_cards
    assert game_state.player_hands[0] is not None
    assert game_state.player_hands[1] is not None
    assert game_state.small_blind == 5.0


def test_determine_payouts_splits_on_tie():
    deal = Deal(
        hole_cards={
            0: [Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.SPADES)],
            1: [Card(Rank.FOUR, Suit.HEARTS), Card(Rank.SIX, Suit.HEARTS)],
        },
        community_cards=[
            Card(Rank.TEN, Suit.CLUBS),
            Card(Rank.JACK, Suit.DIAMONDS),
            Card(Rank.QUEEN, Suit.HEARTS),
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.ACE, Suit.CLUBS),
        ],
        button_position=1,
    )

    game_state = simulate_hand_from_deal(
        deal=deal,
        initial_bet=10.0,
        player_energies=[100.0, 100.0],
        player_aggressions=[0.5, 0.5],
        player_strategies=[AlwaysCallStrategy(), AlwaysCallStrategy()],
        small_blind=5.0,
        rng=random.Random(1),
    )

    payouts = determine_payouts(game_state)

    assert set(payouts.keys()) == {0, 1}
    assert pytest.approx(sum(payouts.values())) == game_state.pot
    assert pytest.approx(payouts[0]) == game_state.pot / 2
    assert pytest.approx(payouts[1]) == game_state.pot / 2


def test_simulate_hand_from_deal_rejects_duplicate_cards():
    duplicate = Card(Rank.ACE, Suit.SPADES)
    deal = Deal(
        hole_cards={
            0: [duplicate, Card(Rank.ACE, Suit.DIAMONDS)],
            1: [duplicate, Card(Rank.KING, Suit.CLUBS)],
        },
        community_cards=[
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.DIAMONDS),
            Card(Rank.NINE, Suit.SPADES),
            Card(Rank.JACK, Suit.HEARTS),
            Card(Rank.FOUR, Suit.CLUBS),
        ],
        button_position=0,
    )

    with pytest.raises(ValueError):
        simulate_hand_from_deal(
            deal=deal,
            initial_bet=10.0,
            player_energies=[100.0, 100.0],
            player_aggressions=[0.5, 0.5],
            player_strategies=[AlwaysCallStrategy(), AlwaysCallStrategy()],
            small_blind=5.0,
            rng=random.Random(2),
        )
