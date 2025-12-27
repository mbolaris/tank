"""
Multiplayer poker game simulation for Texas Hold'em (3+ players).

This module provides game simulation with full betting rounds, bluffing,
and strategy support for 3 or more players.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from core.config.poker import POKER_MAX_ACTIONS_PER_ROUND
from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import AGGRESSION_MEDIUM, decide_action
from core.poker.core.cards import Card, Deck
from core.poker.core.hand import PokerHand
from core.poker.evaluation.hand_evaluator import evaluate_hand
from core.poker.evaluation.strength import evaluate_starting_hand_strength, evaluate_hand_strength

if TYPE_CHECKING:
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)


@dataclass
class MultiplayerPlayerContext:
    """Runtime state needed to evaluate betting decisions for each player."""
    player_id: int
    remaining_energy: float
    aggression: float
    strategy: Optional["PokerStrategyAlgorithm"] = None
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: float = 0.0  # Bet in current round
    total_bet: float = 0.0    # Total bet across all rounds
    folded: bool = False
    all_in: bool = False


@dataclass
class MultiplayerGameState:
    """Tracks the state of a multiplayer Texas Hold'em poker game."""

    num_players: int
    players: Dict[int, MultiplayerPlayerContext]
    community_cards: List[Card] = field(default_factory=list)
    pot: float = 0.0
    current_round: int = BettingRound.PRE_FLOP
    betting_history: List[Tuple[int, BettingAction, float]] = field(default_factory=list)
    button_position: int = 0  # Index of player on button
    small_blind: float = 2.5
    big_blind: float = 5.0
    deck: Deck = field(default_factory=Deck)
    min_raise: float = 5.0
    last_raise_amount: float = 5.0
    player_hands: Dict[int, Optional[PokerHand]] = field(default_factory=dict)

    def get_active_players(self) -> List[int]:
        """Return list of player IDs who haven't folded."""
        return [pid for pid, p in self.players.items() if not p.folded]

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner if all but one player has folded."""
        active = self.get_active_players()
        if len(active) == 1:
            return active[0]
        return None

    def get_max_current_bet(self) -> float:
        """Get the highest current bet among active players."""
        return max(p.current_bet for p in self.players.values() if not p.folded)

    def player_bet(self, player_id: int, amount: float) -> None:
        """Record a player's bet."""
        player = self.players[player_id]
        actual_amount = min(amount, player.remaining_energy)
        player.current_bet += actual_amount
        player.total_bet += actual_amount
        player.remaining_energy -= actual_amount
        self.pot += actual_amount
        if player.remaining_energy <= 0:
            player.all_in = True

    def advance_round(self) -> None:
        """Move to the next betting round."""
        # Reset current bets for new round
        for player in self.players.values():
            player.current_bet = 0.0

        self.current_round += 1
        self.min_raise = self.big_blind
        self.last_raise_amount = self.big_blind

        # Deal community cards
        if self.current_round == BettingRound.FLOP:
            self.deck.deal(1)  # Burn
            self.community_cards.extend(self.deck.deal(3))
        elif self.current_round == BettingRound.TURN:
            self.deck.deal(1)  # Burn
            self.community_cards.append(self.deck.deal_one())
        elif self.current_round == BettingRound.RIVER:
            self.deck.deal(1)  # Burn
            self.community_cards.append(self.deck.deal_one())


def simulate_multiplayer_game(
    num_players: int,
    initial_bet: float,
    player_energies: List[float],
    player_aggressions: Optional[List[float]] = None,
    player_strategies: Optional[List[Optional["PokerStrategyAlgorithm"]]] = None,
    button_position: int = 0,
) -> MultiplayerGameState:
    """
    Simulate a complete multiplayer Texas Hold'em poker game with blinds.

    Args:
        num_players: Number of players (3+)
        initial_bet: Base bet amount (used for big blind)
        player_energies: Energy for each player
        player_aggressions: Aggression levels (0-1) for each player
        player_strategies: Optional strategy algorithms for each player
        button_position: Index of player on button (0 to num_players-1)

    Returns:
        MultiplayerGameState with complete game results
    """
    if num_players < 3:
        raise ValueError("Multiplayer game requires at least 3 players")

    if player_aggressions is None:
        player_aggressions = [AGGRESSION_MEDIUM] * num_players
    if player_strategies is None:
        player_strategies = [None] * num_players

    game_state = _create_multiplayer_game_state(
        num_players=num_players,
        initial_bet=initial_bet,
        player_energies=player_energies,
        player_aggressions=player_aggressions,
        player_strategies=player_strategies,
        button_position=button_position,
    )

    _play_multiplayer_betting_rounds(game_state)
    _evaluate_multiplayer_hands(game_state)

    return game_state


def _create_multiplayer_game_state(
    num_players: int,
    initial_bet: float,
    player_energies: List[float],
    player_aggressions: List[float],
    player_strategies: List[Optional["PokerStrategyAlgorithm"]],
    button_position: int,
) -> MultiplayerGameState:
    """Create and initialize a multiplayer game state."""

    # Calculate blinds
    min_energy = min(player_energies)
    big_blind = min(initial_bet, min_energy)
    small_blind = min(initial_bet / 2, big_blind / 2, min_energy)

    # Create player contexts
    players: Dict[int, MultiplayerPlayerContext] = {}
    for i in range(num_players):
        players[i] = MultiplayerPlayerContext(
            player_id=i,
            remaining_energy=player_energies[i],
            aggression=player_aggressions[i],
            strategy=player_strategies[i] if player_strategies else None,
        )

    game_state = MultiplayerGameState(
        num_players=num_players,
        players=players,
        button_position=button_position,
        small_blind=small_blind,
        big_blind=big_blind,
        min_raise=big_blind,
        last_raise_amount=big_blind,
    )

    # Deal hole cards
    deck = game_state.deck
    for i in range(num_players):
        game_state.players[i].hole_cards = deck.deal(2)

    # Post blinds (small blind is left of button, big blind is 2 left of button)
    sb_pos = (button_position + 1) % num_players
    bb_pos = (button_position + 2) % num_players

    game_state.player_bet(sb_pos, small_blind)
    game_state.player_bet(bb_pos, big_blind)

    return game_state


def _play_multiplayer_betting_rounds(game_state: MultiplayerGameState) -> None:
    """Play all betting rounds of the game."""

    hand_cache: Dict[int, PokerHand] = {}

    for round_num in range(4):  # Pre-flop, Flop, Turn, River
        if game_state.get_winner_by_fold() is not None:
            break

        # Check if only one player can act (others are all-in or folded)
        active_can_act = [
            pid for pid, p in game_state.players.items()
            if not p.folded and not p.all_in
        ]
        if len(active_can_act) <= 1:
            # Deal remaining community cards and go to showdown
            while game_state.current_round < BettingRound.RIVER:
                game_state.advance_round()
            break

        if round_num > 0:
            game_state.advance_round()
            hand_cache.clear()

        _play_single_betting_round(game_state, hand_cache, round_num)
        _refund_unmatched_bets(game_state)


def _play_single_betting_round(
    game_state: MultiplayerGameState,
    hand_cache: Dict[int, PokerHand],
    round_num: int,
) -> None:
    """Play a single betting round."""

    num_players = game_state.num_players
    button = game_state.button_position

    # Determine starting player:
    # Pre-flop: UTG (3 left of button, or left of BB)
    # Post-flop: First active player left of button
    if round_num == 0:
        # Pre-flop: start with UTG (3 positions left of button)
        start_pos = (button + 3) % num_players
    else:
        # Post-flop: start with first active player left of button
        start_pos = (button + 1) % num_players

    current_player = start_pos
    actions_this_round = 0
    last_raiser: Optional[int] = None
    players_acted_since_raise = set()

    # In pre-flop, BB is considered the last raiser initially
    if round_num == 0:
        last_raiser = (button + 2) % num_players

    max_actions = POKER_MAX_ACTIONS_PER_ROUND * num_players

    while actions_this_round < max_actions:
        player = game_state.players[current_player]

        # Skip folded or all-in players
        if player.folded or player.all_in:
            current_player = (current_player + 1) % num_players
            continue

        # Check if betting round is complete
        if _is_round_complete(game_state, last_raiser, players_acted_since_raise, round_num):
            break

        # Get player's action
        action, bet_amount = _decide_multiplayer_action(
            player_id=current_player,
            game_state=game_state,
            hand_cache=hand_cache,
        )

        # Apply the action
        was_raise = _apply_multiplayer_action(
            player_id=current_player,
            action=action,
            bet_amount=bet_amount,
            game_state=game_state,
        )

        if was_raise:
            last_raiser = current_player
            players_acted_since_raise = {current_player}
        else:
            players_acted_since_raise.add(current_player)

        actions_this_round += 1

        # Check for fold victory
        if game_state.get_winner_by_fold() is not None:
            break

        current_player = (current_player + 1) % num_players


def _is_round_complete(
    game_state: MultiplayerGameState,
    last_raiser: Optional[int],
    players_acted_since_raise: set,
    round_num: int,
) -> bool:
    """Check if the betting round is complete."""

    active_players = [
        pid for pid, p in game_state.players.items()
        if not p.folded and not p.all_in
    ]

    if len(active_players) <= 1:
        return True

    # All active players must have acted since the last raise
    # and all bets must be equal
    max_bet = game_state.get_max_current_bet()

    for pid in active_players:
        player = game_state.players[pid]
        # Player hasn't matched the bet
        if player.current_bet < max_bet:
            return False
        # Player hasn't had a chance to act since the last raise
        if pid not in players_acted_since_raise:
            return False

    return True


def _decide_multiplayer_action(
    player_id: int,
    game_state: MultiplayerGameState,
    hand_cache: Dict[int, PokerHand],
) -> Tuple[BettingAction, float]:
    """Decide what action a player should take."""

    player = game_state.players[player_id]

    # Evaluate hand
    if player_id not in hand_cache:
        hand_cache[player_id] = evaluate_hand(
            player.hole_cards, game_state.community_cards
        )
    hand = hand_cache[player_id]

    # Calculate opponent bet (average of other active players)
    active_others = [
        p for pid, p in game_state.players.items()
        if pid != player_id and not p.folded
    ]
    opponent_bet = sum(p.current_bet for p in active_others) / len(active_others) if active_others else 0

    # Use strategy if available
    if player.strategy is not None:
        is_preflop = len(game_state.community_cards) == 0
        position_on_button = player_id == game_state.button_position
        # Use starting hand evaluation for pre-flop to match standard algorithm's info
        if is_preflop and player.hole_cards and len(player.hole_cards) == 2:
            hand_strength = evaluate_starting_hand_strength(player.hole_cards, position_on_button)
        else:
            hand_strength = evaluate_hand_strength(hand)
        return player.strategy.decide_action(
            hand_strength=hand_strength,
            current_bet=player.current_bet,
            opponent_bet=opponent_bet,
            pot=game_state.pot,
            player_energy=player.remaining_energy,
            position_on_button=position_on_button,
        )

    # Use default decision logic
    return decide_action(
        hand=hand,
        current_bet=player.current_bet,
        opponent_bet=opponent_bet,
        pot=game_state.pot,
        player_energy=player.remaining_energy,
        aggression=player.aggression,
        hole_cards=player.hole_cards,
        community_cards=game_state.community_cards,
        position_on_button=(player_id == game_state.button_position),
    )


def _apply_multiplayer_action(
    player_id: int,
    action: BettingAction,
    bet_amount: float,
    game_state: MultiplayerGameState,
) -> bool:
    """Apply a player's action. Returns True if it was a raise."""

    player = game_state.players[player_id]

    if action == BettingAction.FOLD:
        game_state.betting_history.append((player_id, action, 0.0))
        player.folded = True
        return False

    if action == BettingAction.CHECK:
        game_state.betting_history.append((player_id, action, 0.0))
        return False

    max_bet = game_state.get_max_current_bet()
    call_amount = max_bet - player.current_bet

    if action == BettingAction.CALL:
        actual_call = min(call_amount, player.remaining_energy)
        game_state.betting_history.append((player_id, action, actual_call))
        game_state.player_bet(player_id, actual_call)
        return False

    if action == BettingAction.RAISE:
        # First call the current bet
        call_payment = min(call_amount, player.remaining_energy)
        remaining_after_call = player.remaining_energy - call_payment

        # Then add raise amount
        min_raise = game_state.min_raise
        actual_raise = max(min_raise, min(bet_amount, remaining_after_call))

        total_bet = call_payment + actual_raise

        if actual_raise > 0:
            game_state.betting_history.append((player_id, action, actual_raise))
            game_state.player_bet(player_id, total_bet)
            game_state.last_raise_amount = actual_raise
            game_state.min_raise = actual_raise
            return True
        else:
            # Can't raise, just call
            game_state.betting_history.append((player_id, BettingAction.CALL, call_payment))
            game_state.player_bet(player_id, call_payment)
            return False

    return False


def _refund_unmatched_bets(game_state: MultiplayerGameState) -> None:
    """Refund any unmatched portion of bets at end of round."""

    active_players = [p for p in game_state.players.values() if not p.folded]
    if len(active_players) <= 1:
        return

    # Find the second-highest bet (max that was matched)
    bets = sorted([p.current_bet for p in active_players], reverse=True)
    if len(bets) < 2:
        return

    max_matched = bets[1]  # Second highest = amount that was actually matched

    for player in active_players:
        if player.current_bet > max_matched:
            refund = player.current_bet - max_matched
            player.current_bet = max_matched
            player.total_bet -= refund
            player.remaining_energy += refund
            game_state.pot -= refund


def _evaluate_multiplayer_hands(game_state: MultiplayerGameState) -> None:
    """Evaluate hands for all active players at showdown."""

    for player_id, player in game_state.players.items():
        if not player.folded:
            game_state.player_hands[player_id] = evaluate_hand(
                player.hole_cards, game_state.community_cards
            )
        else:
            game_state.player_hands[player_id] = None
