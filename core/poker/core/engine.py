"""
Poker game engine implementing Texas Hold'em rules and betting logic.

This module contains the core game engine, game state tracking, and AI decision making.
"""

import logging
import random
from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations
from typing import TYPE_CHECKING, List, Optional, Tuple

from core.constants import (
    POKER_MAX_ACTIONS_PER_ROUND,
    POKER_MEDIUM_AGGRESSION_MULTIPLIER,
    POKER_MEDIUM_CALL_MULTIPLIER,
    POKER_MEDIUM_ENERGY_FRACTION,
    POKER_MEDIUM_ENERGY_FRACTION_RERAISE,
    POKER_MEDIUM_POT_MULTIPLIER,
    POKER_MEDIUM_POT_ODDS_FOLD_THRESHOLD,
    POKER_MEDIUM_RAISE_PROBABILITY,
    POKER_STRONG_CALL_MULTIPLIER,
    POKER_STRONG_ENERGY_FRACTION,
    POKER_STRONG_ENERGY_FRACTION_RERAISE,
    POKER_STRONG_POT_MULTIPLIER,
    POKER_STRONG_RAISE_PROBABILITY,
    POKER_WEAK_BLUFF_PROBABILITY,
    POKER_WEAK_CALL_PROBABILITY,
    POKER_WEAK_ENERGY_FRACTION,
    POKER_WEAK_POT_MULTIPLIER,
)
from core.poker.core.cards import Card, Deck
from core.poker.core.hand import HandRank, PokerHand

if TYPE_CHECKING:
    from core.poker.strategy.implementations import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)


class BettingRound(IntEnum):
    """Betting rounds in Texas Hold'em."""

    PRE_FLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3
    SHOWDOWN = 4


class BettingAction(IntEnum):
    """Possible betting actions."""

    FOLD = 0
    CHECK = 1
    CALL = 2
    RAISE = 3


@dataclass
class PokerGameState:
    """Tracks the state of a multi-round Texas Hold'em poker game."""

    current_round: BettingRound
    pot: float
    player1_total_bet: float
    player2_total_bet: float
    player1_current_bet: float
    player2_current_bet: float
    player1_folded: bool
    player2_folded: bool
    player1_hole_cards: List[Card]
    player2_hole_cards: List[Card]
    community_cards: List[Card]  # 0 pre-flop, 3 after flop, 4 after turn, 5 after river
    player1_hand: Optional[PokerHand]  # Evaluated at showdown
    player2_hand: Optional[PokerHand]  # Evaluated at showdown
    betting_history: List[Tuple[int, BettingAction, float]]  # (player, action, amount)
    button_position: int  # Which player is on the button (1 or 2)
    small_blind: float
    big_blind: float
    deck: Deck
    min_raise: float  # Minimum raise amount (Texas Hold'em rule)
    last_raise_amount: float  # Size of the last raise (to calculate next min raise)

    def __init__(self, small_blind: float = 2.5, big_blind: float = 5.0, button_position: int = 1):
        self.current_round = BettingRound.PRE_FLOP
        self.pot = 0.0
        self.player1_total_bet = 0.0
        self.player2_total_bet = 0.0
        self.player1_current_bet = 0.0
        self.player2_current_bet = 0.0
        self.player1_folded = False
        self.player2_folded = False
        self.player1_hole_cards = []
        self.player2_hole_cards = []
        self.community_cards = []
        self.player1_hand = None
        self.player2_hand = None
        self.betting_history = []
        self.button_position = button_position
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck = Deck()
        # Min raise starts at big blind and updates with each raise
        self.min_raise = big_blind
        self.last_raise_amount = big_blind  # BB counts as the first "raise" pre-flop

    def add_to_pot(self, amount: float):
        """Add money to the pot."""
        self.pot += amount

    def player_bet(self, player: int, amount: float):
        """Record a player's bet."""
        if player == 1:
            self.player1_current_bet += amount
            self.player1_total_bet += amount
        else:
            self.player2_current_bet += amount
            self.player2_total_bet += amount
        self.add_to_pot(amount)

    def deal_cards(self):
        """Deal hole cards to both players."""
        self.player1_hole_cards = self.deck.deal(2)
        self.player2_hole_cards = self.deck.deal(2)

    def deal_flop(self):
        """Deal the flop (3 community cards)."""
        self.deck.deal(1)  # Burn card
        self.community_cards.extend(self.deck.deal(3))

    def deal_turn(self):
        """Deal the turn (4th community card)."""
        self.deck.deal(1)  # Burn card
        self.community_cards.append(self.deck.deal_one())

    def deal_river(self):
        """Deal the river (5th community card)."""
        self.deck.deal(1)  # Burn card
        self.community_cards.append(self.deck.deal_one())

    def advance_round(self):
        """Move to the next betting round and deal appropriate community cards."""
        if self.current_round < BettingRound.SHOWDOWN:
            self.current_round = BettingRound(self.current_round + 1)

            # Deal community cards based on new round
            if self.current_round == BettingRound.FLOP:
                self.deal_flop()
            elif self.current_round == BettingRound.TURN:
                self.deal_turn()
            elif self.current_round == BettingRound.RIVER:
                self.deal_river()

            # Reset current round bets
            self.player1_current_bet = 0.0
            self.player2_current_bet = 0.0

            # Reset minimum raise to big blind for the new round
            self.min_raise = self.big_blind
            self.last_raise_amount = self.big_blind

    def is_betting_complete(self) -> bool:
        """Check if betting is complete for current round."""
        # Betting is complete if bets are equal and both players have acted
        return (
            self.player1_current_bet == self.player2_current_bet
            and len([h for h in self.betting_history if h[0] in [1, 2]]) >= 2
        )

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner if someone folded, None otherwise."""
        if self.player1_folded:
            return 2
        elif self.player2_folded:
            return 1
        return None


class PokerEngine:
    """Core poker game logic for fish interactions with authentic Texas Hold'em."""

    # Import aggression constants from centralized constants module
    from core.constants import (
        POKER_AGGRESSION_HIGH as AGGRESSION_HIGH,
    )
    from core.constants import (
        POKER_AGGRESSION_LOW as AGGRESSION_LOW,
    )
    from core.constants import (
        POKER_AGGRESSION_MEDIUM as AGGRESSION_MEDIUM,
    )

    @staticmethod
    def _rank_name(rank: int) -> str:
        """Get the name of a rank."""
        names = {
            2: "2",
            3: "3",
            4: "4",
            5: "5",
            6: "6",
            7: "7",
            8: "8",
            9: "9",
            10: "Ten",
            11: "Jack",
            12: "Queen",
            13: "King",
            14: "Ace",
        }
        return names.get(rank, str(rank))

    @staticmethod
    def _evaluate_five_cards(cards: List[Card]) -> PokerHand:
        """Evaluate exactly 5 cards and return the poker hand."""
        sorted_cards = sorted(cards, key=lambda c: c.rank, reverse=True)
        ranks = [c.rank for c in sorted_cards]
        suits = [c.suit for c in sorted_cards]

        rank_counts = Counter(ranks)
        rank_count_list = rank_counts.most_common()

        # Check for flush
        is_flush = len(set(suits)) == 1

        # Check for straight (including A-2-3-4-5)
        is_straight = False
        straight_high = 0
        if ranks == list(range(ranks[0], ranks[0] - 5, -1)):
            is_straight = True
            straight_high = ranks[0]
        elif ranks == [14, 5, 4, 3, 2]:  # Ace-low straight (wheel)
            is_straight = True
            straight_high = 5

        # Evaluate hand type
        if is_straight and is_flush:
            if straight_high == 14:
                return PokerHand(
                    hand_type="royal_flush",
                    rank_value=HandRank.ROYAL_FLUSH,
                    description="Royal Flush",
                    cards=sorted_cards,
                    primary_ranks=[14],
                    kickers=[],
                )
            else:
                return PokerHand(
                    hand_type="straight_flush",
                    rank_value=HandRank.STRAIGHT_FLUSH,
                    description=f"Straight Flush, {PokerEngine._rank_name(straight_high)} high",
                    cards=sorted_cards,
                    primary_ranks=[straight_high],
                    kickers=[],
                )

        if rank_count_list[0][1] == 4:
            # Four of a kind
            quad_rank = rank_count_list[0][0]
            kicker = rank_count_list[1][0]
            return PokerHand(
                hand_type="four_of_kind",
                rank_value=HandRank.FOUR_OF_KIND,
                description=f"Four {PokerEngine._rank_name(quad_rank)}s",
                cards=sorted_cards,
                primary_ranks=[quad_rank],
                kickers=[kicker],
            )

        if rank_count_list[0][1] == 3 and rank_count_list[1][1] == 2:
            # Full house
            trips_rank = rank_count_list[0][0]
            pair_rank = rank_count_list[1][0]
            return PokerHand(
                hand_type="full_house",
                rank_value=HandRank.FULL_HOUSE,
                description=(
                    f"Full House, {PokerEngine._rank_name(trips_rank)}s "
                    f"over {PokerEngine._rank_name(pair_rank)}s"
                ),
                cards=sorted_cards,
                primary_ranks=[trips_rank, pair_rank],
                kickers=[],
            )

        if is_flush:
            return PokerHand(
                hand_type="flush",
                rank_value=HandRank.FLUSH,
                description=f"Flush, {PokerEngine._rank_name(ranks[0])} high",
                cards=sorted_cards,
                primary_ranks=[],
                kickers=ranks,
            )

        if is_straight:
            return PokerHand(
                hand_type="straight",
                rank_value=HandRank.STRAIGHT,
                description=f"Straight, {PokerEngine._rank_name(straight_high)} high",
                cards=sorted_cards,
                primary_ranks=[straight_high],
                kickers=[],
            )

        if rank_count_list[0][1] == 3:
            # Three of a kind
            trips_rank = rank_count_list[0][0]
            kickers_list = [rank_count_list[1][0], rank_count_list[2][0]]
            kickers_list.sort(reverse=True)
            return PokerHand(
                hand_type="three_of_kind",
                rank_value=HandRank.THREE_OF_KIND,
                description=f"Three {PokerEngine._rank_name(trips_rank)}s",
                cards=sorted_cards,
                primary_ranks=[trips_rank],
                kickers=kickers_list,
            )

        if rank_count_list[0][1] == 2 and rank_count_list[1][1] == 2:
            # Two pair
            pair1 = rank_count_list[0][0]
            pair2 = rank_count_list[1][0]
            pairs = sorted([pair1, pair2], reverse=True)
            kicker = rank_count_list[2][0]
            return PokerHand(
                hand_type="two_pair",
                rank_value=HandRank.TWO_PAIR,
                description=f"Two Pair, {PokerEngine._rank_name(pairs[0])}s and {PokerEngine._rank_name(pairs[1])}s",
                cards=sorted_cards,
                primary_ranks=pairs,
                kickers=[kicker],
            )

        if rank_count_list[0][1] == 2:
            # One pair
            pair_rank = rank_count_list[0][0]
            kickers_list = [rank_count_list[1][0], rank_count_list[2][0], rank_count_list[3][0]]
            kickers_list.sort(reverse=True)
            return PokerHand(
                hand_type="pair",
                rank_value=HandRank.PAIR,
                description=f"Pair of {PokerEngine._rank_name(pair_rank)}s",
                cards=sorted_cards,
                primary_ranks=[pair_rank],
                kickers=kickers_list,
            )

        # High card
        return PokerHand(
            hand_type="high_card",
            rank_value=HandRank.HIGH_CARD,
            description=f"High Card {PokerEngine._rank_name(ranks[0])}",
            cards=sorted_cards,
            primary_ranks=[],
            kickers=ranks,
        )

    @staticmethod
    def evaluate_hand(hole_cards: List[Card], community_cards: List[Card]) -> PokerHand:
        """
        Evaluate the best 5-card poker hand from hole cards and community cards.

        Args:
            hole_cards: Player's 2 hole cards
            community_cards: 0-5 community cards

        Returns:
            PokerHand with rank, description, and kickers
        """
        # Combine all available cards
        all_cards = hole_cards + community_cards

        if len(all_cards) < 5:
            # Not enough cards yet - return high card from what we have
            sorted_cards = sorted(all_cards, key=lambda c: c.rank, reverse=True)
            return PokerHand(
                hand_type="high_card",
                rank_value=HandRank.HIGH_CARD,
                description=f"High Card {PokerEngine._rank_name(sorted_cards[0].rank)}",
                cards=sorted_cards[:5] if len(sorted_cards) >= 5 else sorted_cards,
                primary_ranks=[sorted_cards[0].rank] if sorted_cards else [],
                kickers=[c.rank for c in sorted_cards[1:5]] if len(sorted_cards) > 1 else [],
            )

        # Find best 5-card combination
        best_hand = None

        for five_cards in combinations(all_cards, 5):
            hand = PokerEngine._evaluate_five_cards(list(five_cards))
            if best_hand is None or hand.beats(best_hand):
                best_hand = hand

        return best_hand

    @staticmethod
    def _decide_strong_hand_action(
        call_amount: float, pot: float, player_energy: float, aggression: float
    ) -> Tuple[BettingAction, float]:
        """Decide action for strong hands (flush or better)."""
        if call_amount == 0:
            # No bet to call - raise most of the time
            if random.random() < POKER_STRONG_RAISE_PROBABILITY:
                raise_amount = min(
                    pot * POKER_STRONG_POT_MULTIPLIER, player_energy * POKER_STRONG_ENERGY_FRACTION
                )
                return (BettingAction.RAISE, raise_amount)
            else:
                return (BettingAction.CHECK, 0.0)
        else:
            # There's a bet - call or raise
            if random.random() < aggression:
                # Raise
                raise_amount = min(
                    call_amount * POKER_STRONG_CALL_MULTIPLIER,
                    player_energy * POKER_STRONG_ENERGY_FRACTION_RERAISE,
                )
                return (BettingAction.RAISE, raise_amount)
            else:
                # Call
                return (BettingAction.CALL, call_amount)

    @staticmethod
    def _decide_medium_hand_action(
        call_amount: float, pot: float, player_energy: float, aggression: float
    ) -> Tuple[BettingAction, float]:
        """Decide action for medium hands (pair through straight)."""
        if call_amount == 0:
            # No bet - check or small raise
            if random.random() < aggression * POKER_MEDIUM_AGGRESSION_MULTIPLIER:
                raise_amount = min(
                    pot * POKER_MEDIUM_POT_MULTIPLIER, player_energy * POKER_MEDIUM_ENERGY_FRACTION
                )
                return (BettingAction.RAISE, raise_amount)
            else:
                return (BettingAction.CHECK, 0.0)
        else:
            # There's a bet - fold, call, or raise based on bet size and aggression
            pot_odds = call_amount / (pot + call_amount) if pot > 0 else 1.0

            # More likely to fold if bet is large relative to pot
            if pot_odds > POKER_MEDIUM_POT_ODDS_FOLD_THRESHOLD and random.random() > aggression:
                return (BettingAction.FOLD, 0.0)
            elif random.random() < aggression * POKER_MEDIUM_RAISE_PROBABILITY:
                # Sometimes raise with medium hands
                raise_amount = min(
                    call_amount * POKER_MEDIUM_CALL_MULTIPLIER,
                    player_energy * POKER_MEDIUM_ENERGY_FRACTION_RERAISE,
                )
                return (BettingAction.RAISE, raise_amount)
            else:
                # Usually call
                return (BettingAction.CALL, call_amount)

    @staticmethod
    def _decide_weak_hand_action(
        call_amount: float, pot: float, player_energy: float, aggression: float
    ) -> Tuple[BettingAction, float]:
        """Decide action for weak hands (high card)."""
        if call_amount == 0:
            # No bet - usually check, rarely bluff
            if random.random() < aggression * POKER_WEAK_BLUFF_PROBABILITY:
                # Bluff
                raise_amount = min(
                    pot * POKER_WEAK_POT_MULTIPLIER, player_energy * POKER_WEAK_ENERGY_FRACTION
                )
                return (BettingAction.RAISE, raise_amount)
            else:
                return (BettingAction.CHECK, 0.0)
        else:
            # There's a bet - usually fold, rarely bluff call
            if random.random() < aggression * POKER_WEAK_CALL_PROBABILITY:
                # Bluff call
                return (BettingAction.CALL, call_amount)
            else:
                return (BettingAction.FOLD, 0.0)

    @staticmethod
    def decide_action(
        hand: PokerHand,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        aggression: float = None,
        hole_cards: Optional[List[Card]] = None,
        community_cards: Optional[List[Card]] = None,
        position_on_button: bool = False,
    ) -> Tuple[BettingAction, float]:
        """
        Decide what action to take based on hand strength and game state.

        Enhanced with realistic pre-flop hand evaluation and position awareness.
        """
        if aggression is None:
            aggression = PokerEngine.AGGRESSION_MEDIUM

        # Calculate how much needs to be called
        call_amount = opponent_bet - current_bet

        # Can't bet more than available energy
        if call_amount > player_energy:
            # Must fold if can't afford to call
            return (BettingAction.FOLD, 0.0)

        # Enhanced pre-flop decision making with starting hand evaluation
        is_preflop = community_cards is None or len(community_cards) == 0
        if is_preflop and hole_cards is not None and len(hole_cards) == 2:
            from core.poker.evaluation.strength import (
                calculate_pot_odds,
                evaluate_starting_hand_strength,
                get_action_recommendation,
            )

            # Evaluate starting hand strength
            starting_strength = evaluate_starting_hand_strength(hole_cards, position_on_button)

            # Calculate pot odds
            pot_odds = calculate_pot_odds(call_amount, pot) if call_amount > 0 else 0.0

            # Get recommended action based on situation
            action_type, bet_multiplier = get_action_recommendation(
                hand_strength=starting_strength,
                pot_odds=pot_odds,
                aggression=aggression,
                position_on_button=position_on_button,
                is_preflop=True,
            )

            # Convert recommendation to actual action
            if action_type == "fold":
                return (BettingAction.FOLD, 0.0)
            elif action_type == "check":
                if call_amount == 0:
                    return (BettingAction.CHECK, 0.0)
                else:
                    # Can't check with a bet to call
                    if starting_strength > pot_odds * 0.8:
                        return (BettingAction.CALL, call_amount)
                    else:
                        return (BettingAction.FOLD, 0.0)
            elif action_type == "call":
                if call_amount == 0:
                    return (BettingAction.CHECK, 0.0)
                else:
                    return (BettingAction.CALL, call_amount)
            else:  # raise
                raise_amount = min(pot * bet_multiplier, player_energy * 0.3)
                if call_amount > 0:
                    raise_amount = max(raise_amount, call_amount * 1.5)
                return (BettingAction.RAISE, raise_amount)

        # Determine hand strength category and delegate to appropriate helper
        hand_strength = hand.rank_value

        # Strong hands (flush or better)
        if hand_strength >= HandRank.FLUSH:
            return PokerEngine._decide_strong_hand_action(
                call_amount, pot, player_energy, aggression
            )
        # Medium hands (pair through straight)
        elif hand_strength >= HandRank.PAIR:
            return PokerEngine._decide_medium_hand_action(
                call_amount, pot, player_energy, aggression
            )
        # Weak hands (high card)
        else:
            return PokerEngine._decide_weak_hand_action(call_amount, pot, player_energy, aggression)

    @staticmethod
    def simulate_multi_round_game(
        initial_bet: float,
        player1_energy: float,
        player2_energy: float,
        player1_aggression: float = None,
        player2_aggression: float = None,
        button_position: int = 1,
        player1_strategy: Optional["PokerStrategyAlgorithm"] = None,
        player2_strategy: Optional["PokerStrategyAlgorithm"] = None,
    ) -> PokerGameState:
        """
        Simulate a complete multi-round Texas Hold'em poker game with blinds.
        """
        if player1_aggression is None:
            player1_aggression = PokerEngine.AGGRESSION_MEDIUM
        if player2_aggression is None:
            player2_aggression = PokerEngine.AGGRESSION_MEDIUM

        # Calculate blinds from initial bet
        big_blind = initial_bet
        small_blind = initial_bet / 2

        # Ensure blinds don't exceed available energy
        big_blind = min(big_blind, player1_energy, player2_energy)
        small_blind = min(small_blind, player1_energy, player2_energy, big_blind / 2)

        game_state = PokerGameState(
            small_blind=small_blind, big_blind=big_blind, button_position=button_position
        )

        # Deal hole cards
        game_state.deal_cards()

        # Post blinds
        # In heads-up, button posts small blind, other player posts big blind
        if button_position == 1:
            small_blind_player = 1
            big_blind_player = 2
        else:
            small_blind_player = 2
            big_blind_player = 1

        game_state.player_bet(small_blind_player, small_blind)
        game_state.player_bet(big_blind_player, big_blind)

        if small_blind_player == 1:
            player1_remaining = player1_energy - small_blind
            player2_remaining = player2_energy - big_blind
        else:
            player1_remaining = player1_energy - big_blind
            player2_remaining = player2_energy - small_blind

        # Play through betting rounds
        for round_num in range(4):  # Pre-flop, Flop, Turn, River
            if game_state.get_winner_by_fold() is not None:
                break

            # Advance round and deal community cards
            if round_num > 0:
                game_state.advance_round()

            # Simulate betting for this round
            # Players alternate actions until both have matched bets or someone folds
            max_actions_per_round = POKER_MAX_ACTIONS_PER_ROUND  # Prevent infinite loops
            actions_this_round = 0

            # In heads-up pre-flop, button (small blind) acts first
            # Post-flop, button acts last (so non-button acts first)
            if round_num == 0:  # Pre-flop
                current_player = button_position
            else:  # Post-flop
                current_player = 2 if button_position == 1 else 1

            while actions_this_round < max_actions_per_round:
                # Evaluate current hand strength based on available cards
                if current_player == 1:
                    hand = PokerEngine.evaluate_hand(
                        game_state.player1_hole_cards, game_state.community_cards
                    )
                    current_bet = game_state.player1_current_bet
                    opponent_bet = game_state.player2_current_bet
                    remaining_energy = player1_remaining
                    aggression = player1_aggression
                else:
                    hand = PokerEngine.evaluate_hand(
                        game_state.player2_hole_cards, game_state.community_cards
                    )
                    current_bet = game_state.player2_current_bet
                    opponent_bet = game_state.player1_current_bet
                    remaining_energy = player2_remaining
                    aggression = player2_aggression

                # Decide action
                # Determine if player is on button
                player_on_button = current_player == button_position

                # Get hole cards and community cards for enhanced decision making
                hole_cards = (
                    game_state.player1_hole_cards
                    if current_player == 1
                    else game_state.player2_hole_cards
                )

                # Use poker strategy algorithm if available, otherwise fall back to aggression-based
                player_strategy = player1_strategy if current_player == 1 else player2_strategy

                if player_strategy is not None:
                    # Use evolving poker strategy algorithm
                    # Normalize hand strength from HandRank (0-9) to 0.0-1.0
                    from core.constants import POKER_MAX_HAND_RANK

                    hand_strength = hand.rank_value / POKER_MAX_HAND_RANK

                    action, bet_amount = player_strategy.decide_action(
                        hand_strength=hand_strength,
                        current_bet=current_bet,
                        opponent_bet=opponent_bet,
                        pot=game_state.pot,
                        player_energy=remaining_energy,
                        position_on_button=player_on_button,
                    )
                else:
                    # Fall back to old aggression-based decision making
                    action, bet_amount = PokerEngine.decide_action(
                        hand=hand,
                        current_bet=current_bet,
                        opponent_bet=opponent_bet,
                        pot=game_state.pot,
                        player_energy=remaining_energy,
                        aggression=aggression,
                        hole_cards=hole_cards,
                        community_cards=game_state.community_cards,
                        position_on_button=player_on_button,
                    )

                # Process action
                if action == BettingAction.FOLD:
                    game_state.betting_history.append((current_player, action, 0.0))
                    if current_player == 1:
                        game_state.player1_folded = True
                    else:
                        game_state.player2_folded = True
                    break

                elif action == BettingAction.CHECK:
                    # Check - no bet
                    game_state.betting_history.append((current_player, action, 0.0))

                elif action == BettingAction.CALL:
                    # Call - match opponent's bet
                    game_state.betting_history.append((current_player, action, bet_amount))
                    game_state.player_bet(current_player, bet_amount)
                    if current_player == 1:
                        player1_remaining -= bet_amount
                    else:
                        player2_remaining -= bet_amount

                elif action == BettingAction.RAISE:
                    # Raise - increase bet
                    # First call to match, then add raise amount
                    call_amount = opponent_bet - current_bet

                    # Enforce minimum raise rule (Texas Hold'em)
                    # The raise amount must be at least the size of the last raise
                    actual_raise = max(bet_amount, game_state.min_raise)

                    # Cap raise at remaining energy after call
                    max_raise = remaining_energy - call_amount
                    if max_raise < game_state.min_raise:
                        # Can't afford minimum raise - treat as all-in
                        actual_raise = max(0, max_raise)
                    else:
                        actual_raise = min(actual_raise, max_raise)

                    total_bet = call_amount + actual_raise
                    game_state.player_bet(current_player, total_bet)

                    # Record the actual raise amount (after enforcement)
                    game_state.betting_history.append((current_player, action, actual_raise))

                    # Update minimum raise for next raise (min raise = this raise amount)
                    if actual_raise > 0:
                        game_state.last_raise_amount = actual_raise
                        game_state.min_raise = actual_raise

                    if current_player == 1:
                        player1_remaining -= total_bet
                    else:
                        player2_remaining -= total_bet

                actions_this_round += 1

                # Check if betting is complete for this round
                # Complete if both players have equal bets and at least one has acted
                if (
                    game_state.player1_current_bet == game_state.player2_current_bet
                    and actions_this_round >= 2
                ):
                    break

                # Switch to other player
                current_player = 2 if current_player == 1 else 1

        # Game is over - evaluate final hands at showdown
        game_state.current_round = BettingRound.SHOWDOWN

        # Evaluate best hands using all 7 cards (2 hole + 5 community)
        if not game_state.player1_folded:
            game_state.player1_hand = PokerEngine.evaluate_hand(
                game_state.player1_hole_cards, game_state.community_cards
            )
        if not game_state.player2_folded:
            game_state.player2_hand = PokerEngine.evaluate_hand(
                game_state.player2_hole_cards, game_state.community_cards
            )

        return game_state

    @staticmethod
    def resolve_bet(
        hand1: PokerHand, hand2: PokerHand, bet1_amount: float, bet2_amount: float
    ) -> Tuple[float, float]:
        """
        Resolve a poker bet between two hands with proper kicker comparison.
        """
        # Determine winner using proper hand comparison including kickers
        if hand1.beats(hand2):
            # Player 1 wins, takes both bets
            return (bet2_amount, -bet2_amount)
        elif hand2.beats(hand1):
            # Player 2 wins, takes both bets
            return (-bet1_amount, bet1_amount)
        else:
            # Tie (same rank and kickers) - no money changes hands
            return (0.0, 0.0)

    @staticmethod
    def simulate_game(
        bet_amount: float = 10.0, player1_energy: float = 100.0, player2_energy: float = 100.0
    ) -> PokerGameState:
        """
        Simulate a complete Texas Hold'em poker game between two players.
        """
        return PokerEngine.simulate_multi_round_game(
            initial_bet=bet_amount, player1_energy=player1_energy, player2_energy=player2_energy
        )
