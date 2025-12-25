import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.poker.core import BettingAction, PokerGameState, simulate_game


def test_is_betting_complete_only_checks_current_bets():
    gs = PokerGameState()

    # Precondition: no bets, should be complete (both zero)
    assert gs.is_betting_complete() is True

    # Simulate a bet by player 1 in current round
    gs.player_bet(1, 10.0)
    assert gs.is_betting_complete() is False

    # Player 2 calls
    gs.player_bet(2, 10.0)
    assert gs.is_betting_complete() is True

    # Add historical betting entries (should not affect current round outcome)
    gs.betting_history.append((1, BettingAction.RAISE, 100.0))
    gs.betting_history.append((2, BettingAction.CALL, 100.0))

    # Bets are still equal for the current round
    assert gs.is_betting_complete() is True


def test_simulate_game_runs_to_showdown_or_fold():
    state = simulate_game(bet_amount=5.0, player1_energy=50.0, player2_energy=50.0)
    # Pot should be non-negative and bets should be non-negative
    assert state.pot >= 0
    assert state.player1_current_bet >= 0
    assert state.player2_current_bet >= 0

    # One of the hands should be evaluated or a fold occurred
    assert state.player1_folded or state.player1_hand is not None or state.player2_folded or state.player2_hand is not None
