"""
Hand-level poker engine shared by heads-up and multiplayer simulations.

This module implements a single hand of Texas Hold'em for 2+ players, keeping
state and decision logic centralized for reuse across simulation entry points.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from core.config.poker import POKER_MAX_ACTIONS_PER_ROUND
from core.poker.betting.actions import BettingAction, BettingRound
from core.poker.betting.decision import AGGRESSION_MEDIUM, decide_action
from core.poker.core.cards import Card, Deck
from core.poker.core.hand import PokerHand
from core.poker.evaluation.hand_evaluator import evaluate_hand
from core.poker.evaluation.strength import evaluate_hand_strength, evaluate_starting_hand_strength

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
    current_bet: float = 0.0
    total_bet: float = 0.0
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
    button_position: int = 0
    small_blind: float = 2.5
    big_blind: float = 5.0
    deck: Deck = field(default_factory=Deck)
    min_raise: float = 5.0
    last_raise_amount: float = 5.0
    player_hands: Dict[int, Optional[PokerHand]] = field(default_factory=dict)

    def get_active_players(self) -> List[int]:
        """Return list of player IDs who haven't folded."""
        return [pid for pid, player in self.players.items() if not player.folded]

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner if all but one player has folded."""
        active = self.get_active_players()
        if len(active) == 1:
            return active[0]
        return None

    def get_max_current_bet(self) -> float:
        """Get the highest current bet among active players."""
        return max(player.current_bet for player in self.players.values() if not player.folded)

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
        for player in self.players.values():
            player.current_bet = 0.0

        self.current_round += 1
        self.min_raise = self.big_blind
        self.last_raise_amount = self.big_blind

        if self.current_round == BettingRound.FLOP:
            self.deck.deal(1)
            self.community_cards.extend(self.deck.deal(3))
        elif self.current_round == BettingRound.TURN:
            self.deck.deal(1)
            self.community_cards.append(self.deck.deal_one())
        elif self.current_round == BettingRound.RIVER:
            self.deck.deal(1)
            self.community_cards.append(self.deck.deal_one())


@dataclass(frozen=True)
class Deal:
    """Pre-dealt hand data for deterministic replay."""

    hole_cards: Dict[int, List[Card]]
    community_cards: List[Card]
    button_position: int


def simulate_hand(
    num_players: int,
    initial_bet: float,
    player_energies: List[float],
    player_aggressions: Optional[List[float]] = None,
    player_strategies: Optional[List[Optional["PokerStrategyAlgorithm"]]] = None,
    button_position: int = 0,
    rng: Optional[random.Random] = None,
) -> MultiplayerGameState:
    """Simulate a complete Texas Hold'em hand for 2+ players."""
    if num_players < 2:
        raise ValueError("Hand simulation requires at least 2 players")

    if player_aggressions is None:
        player_aggressions = [AGGRESSION_MEDIUM] * num_players
    if player_strategies is None:
        player_strategies = [None] * num_players

    if rng is None:
        rng = random.Random()

    game_state = _create_multiplayer_game_state(
        num_players=num_players,
        initial_bet=initial_bet,
        player_energies=player_energies,
        player_aggressions=player_aggressions,
        player_strategies=player_strategies,
        button_position=button_position,
        rng=rng,
    )

    _play_multiplayer_betting_rounds(game_state, rng=rng)
    _evaluate_multiplayer_hands(game_state)

    return game_state


def simulate_hand_from_deal(
    deal: Deal,
    initial_bet: float,
    player_energies: List[float],
    player_aggressions: Optional[List[float]] = None,
    player_strategies: Optional[List[Optional["PokerStrategyAlgorithm"]]] = None,
    small_blind: Optional[float] = None,
    rng: Optional[random.Random] = None,
) -> MultiplayerGameState:
    """Simulate a complete Texas Hold'em hand using a pre-dealt setup."""
    num_players = len(player_energies)
    if num_players < 2:
        raise ValueError("Hand simulation requires at least 2 players")

    _validate_deal(deal, num_players)

    if player_aggressions is None:
        player_aggressions = [AGGRESSION_MEDIUM] * num_players
    if player_strategies is None:
        player_strategies = [None] * num_players
    if rng is None:
        rng = random.Random()

    game_state = _create_multiplayer_game_state_from_deal(
        num_players=num_players,
        initial_bet=initial_bet,
        player_energies=player_energies,
        player_aggressions=player_aggressions,
        player_strategies=player_strategies,
        deal=deal,
        small_blind_override=small_blind,
    )

    _play_multiplayer_betting_rounds(game_state, rng=rng)
    _evaluate_multiplayer_hands(game_state)

    return game_state


def _create_multiplayer_game_state(
    num_players: int,
    initial_bet: float,
    player_energies: List[float],
    player_aggressions: List[float],
    player_strategies: List[Optional["PokerStrategyAlgorithm"]],
    button_position: int,
    rng: Optional[random.Random] = None,
) -> MultiplayerGameState:
    """Create and initialize a multiplayer game state."""
    min_energy = min(player_energies)
    big_blind = min(initial_bet, min_energy)
    small_blind = min(initial_bet / 2, big_blind / 2, min_energy)

    players: Dict[int, MultiplayerPlayerContext] = {}
    for i in range(num_players):
        players[i] = MultiplayerPlayerContext(
            player_id=i,
            remaining_energy=player_energies[i],
            aggression=player_aggressions[i],
            strategy=player_strategies[i] if player_strategies else None,
        )

    deck = Deck(rng=rng)
    game_state = MultiplayerGameState(
        num_players=num_players,
        players=players,
        button_position=button_position,
        small_blind=small_blind,
        big_blind=big_blind,
        min_raise=big_blind,
        last_raise_amount=big_blind,
        deck=deck,
    )

    _deal_hole_cards(game_state)

    small_blind_pos, big_blind_pos = _blind_positions(num_players, button_position)
    game_state.player_bet(small_blind_pos, small_blind)
    game_state.player_bet(big_blind_pos, big_blind)

    return game_state


def _create_multiplayer_game_state_from_deal(
    num_players: int,
    initial_bet: float,
    player_energies: List[float],
    player_aggressions: List[float],
    player_strategies: List[Optional["PokerStrategyAlgorithm"]],
    deal: Deal,
    small_blind_override: Optional[float] = None,
) -> MultiplayerGameState:
    """Create and initialize a multiplayer game state from a pre-dealt hand."""
    min_energy = min(player_energies)
    big_blind = min(initial_bet, min_energy)
    if small_blind_override is None:
        small_blind = min(initial_bet / 2, big_blind / 2, min_energy)
    else:
        small_blind = min(small_blind_override, big_blind, min_energy)

    players: Dict[int, MultiplayerPlayerContext] = {}
    for i in range(num_players):
        players[i] = MultiplayerPlayerContext(
            player_id=i,
            remaining_energy=player_energies[i],
            aggression=player_aggressions[i],
            strategy=player_strategies[i] if player_strategies else None,
        )

    deck = _build_deck_from_deal(deal, num_players)
    game_state = MultiplayerGameState(
        num_players=num_players,
        players=players,
        button_position=deal.button_position,
        small_blind=small_blind,
        big_blind=big_blind,
        min_raise=big_blind,
        last_raise_amount=big_blind,
        deck=deck,
    )

    for player_id in range(num_players):
        game_state.players[player_id].hole_cards = list(deal.hole_cards[player_id])

    small_blind_pos, big_blind_pos = _blind_positions(num_players, deal.button_position)
    game_state.player_bet(small_blind_pos, small_blind)
    game_state.player_bet(big_blind_pos, big_blind)

    return game_state


def _build_deck_from_deal(deal: Deal, num_players: int) -> Deck:
    """Create a deck that will deal the deal's community cards in order."""
    if len(deal.community_cards) != 5:
        raise ValueError("Deal must include exactly 5 community cards")

    used_cards = []
    for player_id in range(num_players):
        used_cards.extend(deal.hole_cards[player_id])
    used_cards.extend(deal.community_cards)

    if len(set(used_cards)) != len(used_cards):
        raise ValueError("Deal contains duplicate cards")

    remaining = [card for card in Deck._TEMPLATE_DECK if card not in used_cards]
    burn_cards = remaining[:3]
    remaining = remaining[3:]

    deck = Deck(rng=random.Random(0))
    deck.cards = [
        burn_cards[0],
        deal.community_cards[0],
        deal.community_cards[1],
        deal.community_cards[2],
        burn_cards[1],
        deal.community_cards[3],
        burn_cards[2],
        deal.community_cards[4],
        *remaining,
    ]
    return deck



def _deal_hole_cards(game_state: MultiplayerGameState) -> None:
    """Deal hole cards, preserving heads-up interleaving."""
    num_players = game_state.num_players
    deck = game_state.deck

    if num_players == 2:
        for _ in range(2):
            for i in range(num_players):
                game_state.players[i].hole_cards.append(deck.deal_one())
        return

    for i in range(num_players):
        game_state.players[i].hole_cards = deck.deal(2)


def _blind_positions(num_players: int, button_position: int) -> Tuple[int, int]:
    if num_players == 2:
        return button_position, (button_position + 1) % num_players
    return (button_position + 1) % num_players, (button_position + 2) % num_players


def _starting_player_for_round(
    num_players: int, button_position: int, round_num: int
) -> int:
    if num_players == 2:
        if round_num == 0:
            return button_position
        return (button_position + 1) % num_players
    if round_num == 0:
        return (button_position + 3) % num_players
    return (button_position + 1) % num_players


def _play_multiplayer_betting_rounds(
    game_state: MultiplayerGameState, rng: Optional[random.Random] = None
) -> None:
    """Play all betting rounds of the game."""
    hand_cache: Dict[int, PokerHand] = {}

    for round_num in range(4):
        if game_state.get_winner_by_fold() is not None:
            break

        active_can_act = [
            pid for pid, player in game_state.players.items()
            if not player.folded and not player.all_in
        ]
        if len(active_can_act) <= 1:
            while game_state.current_round < BettingRound.RIVER:
                game_state.advance_round()
            break

        if round_num > 0:
            game_state.advance_round()
            hand_cache.clear()

        _play_single_betting_round(game_state, hand_cache, round_num, rng=rng)
        _refund_unmatched_bets(game_state)


def _play_single_betting_round(
    game_state: MultiplayerGameState,
    hand_cache: Dict[int, PokerHand],
    round_num: int,
    rng: Optional[random.Random] = None,
) -> None:
    """Play a single betting round."""
    num_players = game_state.num_players
    button = game_state.button_position

    start_pos = _starting_player_for_round(num_players, button, round_num)
    current_player = start_pos
    actions_this_round = 0
    last_raiser: Optional[int] = None
    players_acted_since_raise = set()

    if round_num == 0:
        _, big_blind_pos = _blind_positions(num_players, button)
        last_raiser = big_blind_pos

    max_actions = POKER_MAX_ACTIONS_PER_ROUND * num_players

    while actions_this_round < max_actions:
        player = game_state.players[current_player]

        if player.folded or player.all_in:
            current_player = (current_player + 1) % num_players
            continue

        if _is_round_complete(game_state, last_raiser, players_acted_since_raise, round_num):
            break

        action, bet_amount = _decide_multiplayer_action(
            player_id=current_player,
            game_state=game_state,
            hand_cache=hand_cache,
            rng=rng,
        )

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
        pid for pid, player in game_state.players.items()
        if not player.folded and not player.all_in
    ]

    if len(active_players) <= 1:
        return True

    max_bet = game_state.get_max_current_bet()

    for pid in active_players:
        player = game_state.players[pid]
        if player.current_bet < max_bet:
            return False
        if pid not in players_acted_since_raise:
            return False

    return True


def _decide_multiplayer_action(
    player_id: int,
    game_state: MultiplayerGameState,
    hand_cache: Dict[int, PokerHand],
    rng: Optional[random.Random] = None,
) -> Tuple[BettingAction, float]:
    """Decide what action a player should take."""
    player = game_state.players[player_id]

    if player_id not in hand_cache:
        hand_cache[player_id] = evaluate_hand(
            player.hole_cards, game_state.community_cards
        )
    hand = hand_cache[player_id]

    active_others = [
        other for pid, other in game_state.players.items()
        if pid != player_id and not other.folded
    ]
    opponent_bet = (
        sum(other.current_bet for other in active_others) / len(active_others)
        if active_others
        else 0
    )

    if player.strategy is not None:
        is_preflop = len(game_state.community_cards) == 0
        position_on_button = player_id == game_state.button_position
        if is_preflop and player.hole_cards and len(player.hole_cards) == 2:
            hand_strength = evaluate_starting_hand_strength(
                player.hole_cards, position_on_button
            )
        else:
            hand_strength = evaluate_hand_strength(hand)
        return player.strategy.decide_action(
            hand_strength=hand_strength,
            current_bet=player.current_bet,
            opponent_bet=opponent_bet,
            pot=game_state.pot,
            player_energy=player.remaining_energy,
            position_on_button=position_on_button,
            rng=rng,
        )

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
        rng=rng,
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
        call_payment = min(call_amount, player.remaining_energy)
        remaining_after_call = player.remaining_energy - call_payment

        min_raise = game_state.min_raise
        if remaining_after_call < min_raise:
            actual_raise = 0.0
        else:
            actual_raise = max(min_raise, min(bet_amount, remaining_after_call))

        total_bet = call_payment + actual_raise

        if actual_raise > 0:
            game_state.betting_history.append((player_id, action, actual_raise))
            game_state.player_bet(player_id, total_bet)
            game_state.last_raise_amount = actual_raise
            game_state.min_raise = actual_raise
            return True
        game_state.betting_history.append((player_id, BettingAction.CALL, call_payment))
        game_state.player_bet(player_id, call_payment)
        return False

    return False


def _refund_unmatched_bets(game_state: MultiplayerGameState) -> None:
    """Refund any unmatched portion of bets at end of round."""
    active_players = [player for player in game_state.players.values() if not player.folded]
    if len(active_players) <= 1:
        return

    bets = sorted([player.current_bet for player in active_players], reverse=True)
    if len(bets) < 2:
        return

    max_matched = bets[1]

    for player in active_players:
        if player.current_bet > max_matched:
            refund = player.current_bet - max_matched
            player.current_bet = max_matched
            player.total_bet -= refund
            player.remaining_energy += refund
            game_state.pot -= refund


def _evaluate_multiplayer_hands(game_state: MultiplayerGameState) -> None:
    """Evaluate hands for all active players at showdown."""
    game_state.current_round = BettingRound.SHOWDOWN
    for player_id, player in game_state.players.items():
        if not player.folded:
            game_state.player_hands[player_id] = evaluate_hand(
                player.hole_cards, game_state.community_cards
            )
        else:
            game_state.player_hands[player_id] = None


def determine_payouts(game_state: MultiplayerGameState) -> Dict[int, float]:
    """Determine payouts for each player after a hand."""
    winner_by_fold = game_state.get_winner_by_fold()
    if winner_by_fold is not None:
        return {winner_by_fold: game_state.pot}

    active_players = [
        player_id for player_id, player in game_state.players.items() if not player.folded
    ]
    if not active_players:
        return {}

    best_hand: Optional[PokerHand] = None
    winners: List[int] = []

    for player_id in active_players:
        hand = game_state.player_hands.get(player_id)
        if hand is None:
            player = game_state.players[player_id]
            hand = evaluate_hand(player.hole_cards, game_state.community_cards)
            game_state.player_hands[player_id] = hand

        if best_hand is None or hand.beats(best_hand):
            best_hand = hand
            winners = [player_id]
        elif hand.ties(best_hand):
            winners.append(player_id)

    if not winners:
        return {}

    split_amount = game_state.pot / len(winners)
    return {player_id: split_amount for player_id in winners}


def _validate_deal(deal: Deal, num_players: int) -> None:
    if len(deal.hole_cards) != num_players:
        raise ValueError("Deal hole cards must match player count")

    for player_id in range(num_players):
        cards = deal.hole_cards.get(player_id)
        if cards is None or len(cards) != 2:
            raise ValueError("Each player must have exactly 2 hole cards")

    if deal.button_position < 0 or deal.button_position >= num_players:
        raise ValueError("Deal button position must be a valid player index")
