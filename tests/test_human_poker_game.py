"""Tests for human vs AI poker game realism."""

from core.human_poker_game import HumanPokerGame
from core.poker.core import BettingRound
from core.poker.core.cards import Card, Rank, Suit


def test_showdown_splits_pot_on_tie():
    """Ensure the pot is split evenly when multiple players tie."""

    game = HumanPokerGame(
        game_id="test",
        human_energy=100.0,
        ai_fish=[{"name": "AI One"}, {"name": "AI Two"}, {"name": "AI Three"}],
    )

    # Force a board where the best hand comes from the community cards (Broadway straight)
    game.community_cards = [
        Card(Rank.TEN, Suit.CLUBS),
        Card(Rank.JACK, Suit.DIAMONDS),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.ACE, Suit.CLUBS),
    ]

    # Only the human and first AI contest the pot; others fold out
    competitors = [game.players[0], game.players[1]]
    for player in competitors:
        player.folded = False
        player.hole_cards = [Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.SPADES)]
        player.current_bet = 0.0
        player.total_bet = 20.0
        player.energy = 80.0

    for player in game.players[2:]:
        player.folded = True

    # Pot reflects equal contributions from the two competitors
    game.pot = 40.0
    game.current_round = BettingRound.RIVER

    game._showdown()

    assert game.game_over
    assert game.players[0].energy == 100.0
    assert game.players[1].energy == 100.0
    assert "split" in game.message.lower()
