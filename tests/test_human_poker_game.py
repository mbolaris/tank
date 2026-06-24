"""Tests for human vs AI poker game realism."""

from core.poker.core import BettingRound
from core.poker.core.cards import Card, Rank, Suit
from core.poker.human_poker_game import HumanPokerGame


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


def test_all_in_bet_still_requires_action_from_opponent():
    """An all-in bettor should not short-circuit the betting round."""

    game = HumanPokerGame(
        game_id="test",
        human_energy=100.0,
        ai_fish=[{"name": "AI One"}, {"name": "AI Two"}, {"name": "AI Three"}],
    )

    human = game.players[0]
    aggressor = game.players[1]

    # Only human and aggressor contest the pot
    for player in game.players:
        player.folded = player not in (human, aggressor)
        player.current_bet = 0.0
        player.total_bet = 0.0
        player.energy = 100.0

    game.current_round = BettingRound.PRE_FLOP
    game.big_blind_has_option = False

    # Aggressor jams all their chips; human posted a smaller bet
    aggressor.current_bet = 100.0
    aggressor.total_bet = 100.0
    aggressor.energy = 0.0

    human.current_bet = 10.0
    human.total_bet = 10.0
    human.energy = 90.0

    game.pot = aggressor.current_bet + human.current_bet
    game.actions_this_round = 1  # Aggressor acted
    game.current_player_index = 1  # Aggressor just acted; advance to next player

    # Betting should not be considered complete yet because the human owes a call decision
    assert not game._is_betting_complete()

    game._next_player()

    assert game.current_round == BettingRound.PRE_FLOP
    assert game.current_player_index == 0  # Human's turn
    assert game._get_call_amount(0) == 90.0


def test_game_ends_immediately_when_all_but_one_fold():
    """Verify game ends without dealing extra cards when all but one player folds."""

    game = HumanPokerGame(
        game_id="test",
        human_energy=100.0,
        ai_fish=[{"name": "AI One"}, {"name": "AI Two"}, {"name": "AI Three"}],
    )

    # Manually set up PRE_FLOP scenario where 3 players will fold sequentially
    # Fold 2 AI immediately to leave human + 1 AI
    game.players[2].folded = True  # AI Two folds
    game.players[3].folded = True  # AI Three folds

    # Reset to PRE_FLOP state
    game.current_round = BettingRound.PRE_FLOP
    game.community_cards = []
    game.game_over = False
    game.pot = 15.0  # Just blinds
    game.current_player_index = 0  # Human's turn

    # Record state
    cards_before = len(game.community_cards)

    # Human folds, leaving only AI One
    game.handle_action("human", "fold")

    # Verify game ended immediately
    assert game.game_over, "Game should end when only one player remains"
    assert len(game.community_cards) == cards_before, (
        f"No community cards should be dealt when fold leaves 1 player. "
        f"Started with {cards_before}, ended with {len(game.community_cards)}"
    )


def test_start_hand_with_inactive_player():
    """Verify that starting a hand with an inactive player (energy <= 0) assigns the blinds to active players only."""
    ai_fish = [{"name": "AI One"}, {"name": "AI Two"}, {"name": "AI Three"}]
    game = HumanPokerGame(
        game_id="test",
        human_energy=100.0,
        ai_fish=ai_fish,
    )

    # Now set AI Two (index 2) to 0 energy
    game.players[2].energy = 0.0
    game.game_over = True  # Force game over to allow start_new_hand
    game.session_over = False

    # Force button index to 0, so next hand's button index will advance to 1 (AI One)
    game.button_index = 0

    # Start the hand
    result = game.start_new_hand()
    assert result["success"]

    # Dealer button: 1 (AI One)
    # Small blind: 3 (AI Three, since 2 has 0 energy and is skipped)
    # Big blind: 0 (You, since 3 is SB)
    assert game.button_index == 1
    assert game.big_blind_index == 0

    assert game.players[3].current_bet == 5.0
    assert game.players[0].current_bet == 10.0
    assert game.players[2].current_bet == 0.0
    assert game.players[2].folded

    # Verify hand engine matches human game's expectations
    assert game._hand_state.players[3].current_bet == 5.0
    assert game._hand_state.players[0].current_bet == 10.0
    assert game._hand_state.players[2].current_bet == 0.0
