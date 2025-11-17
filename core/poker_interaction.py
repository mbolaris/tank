"""
Poker game engine for fish interactions.

This module implements an authentic Texas Hold'em poker system for determining
outcomes of fish-to-fish encounters. When two fish collide, they play a hand
of poker to determine energy transfer.

Features:
- Real 52-card deck with shuffling
- Community cards (flop, turn, river)
- Proper hand evaluation with kicker support
- Small blind/big blind system
- Position-based play (button rotation)
- Multiple betting rounds with folding
"""

import random
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Set
from enum import IntEnum
from collections import Counter


class Suit(IntEnum):
    """Card suits."""
    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3


class Rank(IntEnum):
    """Card ranks (2-14, where 14 is Ace)."""
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


@dataclass(frozen=True)
class Card:
    """Represents a single playing card."""
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        rank_names = {2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8',
                     9: '9', 10: 'T', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
        suit_names = {0: '♣', 1: '♦', 2: '♥', 3: '♠'}
        return f"{rank_names[self.rank]}{suit_names[self.suit]}"

    def __lt__(self, other: 'Card') -> bool:
        return self.rank < other.rank


class Deck:
    """52-card deck for Texas Hold'em."""

    def __init__(self):
        """Initialize and shuffle a standard 52-card deck."""
        self.cards: List[Card] = []
        self.reset()

    def reset(self):
        """Reset and shuffle the deck."""
        self.cards = [Card(Rank(r), Suit(s))
                     for r in range(2, 15)
                     for s in range(4)]
        random.shuffle(self.cards)

    def deal(self, count: int = 1) -> List[Card]:
        """Deal cards from the deck."""
        if count > len(self.cards):
            raise ValueError("Not enough cards in deck")
        dealt = self.cards[:count]
        self.cards = self.cards[count:]
        return dealt

    def deal_one(self) -> Card:
        """Deal a single card."""
        return self.deal(1)[0]


class HandRank(IntEnum):
    """Poker hand rankings from weakest to strongest."""
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


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
class PokerHand:
    """Represents a poker hand and its rank with kickers."""
    hand_type: str
    rank_value: HandRank
    description: str
    cards: List[Card] = field(default_factory=list)  # The 5 cards that make up the hand
    primary_ranks: List[int] = field(default_factory=list)  # Main ranks (e.g., pair ranks)
    kickers: List[int] = field(default_factory=list)  # Kicker ranks for tie-breaking

    def beats(self, other: 'PokerHand') -> bool:
        """Check if this hand beats another hand, including kicker comparison."""
        if self.rank_value != other.rank_value:
            return self.rank_value > other.rank_value

        # Same rank - compare primary ranks
        for my_rank, their_rank in zip(self.primary_ranks, other.primary_ranks):
            if my_rank != their_rank:
                return my_rank > their_rank

        # Same primary ranks - compare kickers
        for my_kicker, their_kicker in zip(self.kickers, other.kickers):
            if my_kicker != their_kicker:
                return my_kicker > their_kicker

        # Completely tied
        return False

    def ties(self, other: 'PokerHand') -> bool:
        """Check if this hand ties with another hand."""
        if self.rank_value != other.rank_value:
            return False
        if self.primary_ranks != other.primary_ranks:
            return False
        if self.kickers != other.kickers:
            return False
        return True

    def __str__(self) -> str:
        return f"{self.description} (rank {self.rank_value})"


@dataclass
class PokerGameState:
    """Tracks the state of a multi-round Texas Hold'em poker game."""
    current_round: BettingRound
    pot: float
    player1_total_bet: float
    player2_total_bet: float
    player1_current_bet: float  # Bet in current round
    player2_current_bet: float  # Bet in current round
    player1_folded: bool
    player2_folded: bool
    player1_hole_cards: List[Card]  # Player 1's 2 hole cards
    player2_hole_cards: List[Card]  # Player 2's 2 hole cards
    community_cards: List[Card]  # Community cards (0 pre-flop, 3 after flop, 4 after turn, 5 after river)
    player1_hand: Optional[PokerHand]  # Best 5-card hand (evaluated at showdown)
    player2_hand: Optional[PokerHand]  # Best 5-card hand (evaluated at showdown)
    betting_history: List[Tuple[int, BettingAction, float]]  # (player, action, amount)
    button_position: int  # Which player is on the button (1 or 2)
    small_blind: float
    big_blind: float
    deck: Deck

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

    def is_betting_complete(self) -> bool:
        """Check if betting is complete for current round."""
        # Betting is complete if bets are equal and both players have acted
        return (self.player1_current_bet == self.player2_current_bet and
                len([h for h in self.betting_history
                     if h[0] in [1, 2]]) >= 2)

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner if someone folded, None otherwise."""
        if self.player1_folded:
            return 2
        elif self.player2_folded:
            return 1
        return None


class PokerEngine:
    """Core poker game logic for fish interactions with authentic Texas Hold'em."""

    # Aggression factors for betting decisions
    # Higher values = more aggressive (more likely to raise/call)
    AGGRESSION_LOW = 0.3
    AGGRESSION_MEDIUM = 0.6
    AGGRESSION_HIGH = 0.9

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
                kickers=[c.rank for c in sorted_cards[1:5]] if len(sorted_cards) > 1 else []
            )

        # Find best 5-card combination
        from itertools import combinations
        best_hand = None

        for five_cards in combinations(all_cards, 5):
            hand = PokerEngine._evaluate_five_cards(list(five_cards))
            if best_hand is None or hand.beats(best_hand):
                best_hand = hand

        return best_hand

    @staticmethod
    def _rank_name(rank: int) -> str:
        """Get the name of a rank."""
        names = {2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8',
                9: '9', 10: 'Ten', 11: 'Jack', 12: 'Queen', 13: 'King', 14: 'Ace'}
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
                    kickers=[]
                )
            else:
                return PokerHand(
                    hand_type="straight_flush",
                    rank_value=HandRank.STRAIGHT_FLUSH,
                    description=f"Straight Flush, {PokerEngine._rank_name(straight_high)} high",
                    cards=sorted_cards,
                    primary_ranks=[straight_high],
                    kickers=[]
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
                kickers=[kicker]
            )

        if rank_count_list[0][1] == 3 and rank_count_list[1][1] == 2:
            # Full house
            trips_rank = rank_count_list[0][0]
            pair_rank = rank_count_list[1][0]
            return PokerHand(
                hand_type="full_house",
                rank_value=HandRank.FULL_HOUSE,
                description=f"Full House, {PokerEngine._rank_name(trips_rank)}s over {PokerEngine._rank_name(pair_rank)}s",
                cards=sorted_cards,
                primary_ranks=[trips_rank, pair_rank],
                kickers=[]
            )

        if is_flush:
            return PokerHand(
                hand_type="flush",
                rank_value=HandRank.FLUSH,
                description=f"Flush, {PokerEngine._rank_name(ranks[0])} high",
                cards=sorted_cards,
                primary_ranks=[],
                kickers=ranks
            )

        if is_straight:
            return PokerHand(
                hand_type="straight",
                rank_value=HandRank.STRAIGHT,
                description=f"Straight, {PokerEngine._rank_name(straight_high)} high",
                cards=sorted_cards,
                primary_ranks=[straight_high],
                kickers=[]
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
                kickers=kickers_list
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
                kickers=[kicker]
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
                kickers=kickers_list
            )

        # High card
        return PokerHand(
            hand_type="high_card",
            rank_value=HandRank.HIGH_CARD,
            description=f"High Card {PokerEngine._rank_name(ranks[0])}",
            cards=sorted_cards,
            primary_ranks=[],
            kickers=ranks
        )

    @staticmethod
    def decide_action(
        hand: PokerHand,
        current_bet: float,
        opponent_bet: float,
        pot: float,
        player_energy: float,
        aggression: float = AGGRESSION_MEDIUM
    ) -> Tuple[BettingAction, float]:
        """
        Decide what action to take based on hand strength and game state.

        Args:
            hand: Player's poker hand
            current_bet: Player's current bet this round
            opponent_bet: Opponent's current bet this round
            pot: Current pot size
            player_energy: Player's available energy
            aggression: Aggression factor (0-1, higher = more aggressive)

        Returns:
            Tuple of (action, bet_amount)
        """
        # Calculate how much needs to be called
        call_amount = opponent_bet - current_bet

        # Can't bet more than available energy
        if call_amount > player_energy:
            # Must fold if can't afford to call
            return (BettingAction.FOLD, 0.0)

        # Determine hand strength category
        hand_strength = hand.rank_value

        # Strong hands (flush or better)
        if hand_strength >= HandRank.FLUSH:
            if call_amount == 0:
                # No bet to call - raise most of the time
                if random.random() < 0.8:
                    raise_amount = min(pot * 0.5, player_energy * 0.3)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    return (BettingAction.CHECK, 0.0)
            else:
                # There's a bet - call or raise
                if random.random() < aggression:
                    # Raise
                    raise_amount = min(call_amount * 2, player_energy * 0.4)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    # Call
                    return (BettingAction.CALL, call_amount)

        # Medium hands (pair through straight)
        elif hand_strength >= HandRank.PAIR:
            if call_amount == 0:
                # No bet - check or small raise
                if random.random() < aggression * 0.6:
                    raise_amount = min(pot * 0.3, player_energy * 0.2)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    return (BettingAction.CHECK, 0.0)
            else:
                # There's a bet - fold, call, or raise based on bet size and aggression
                pot_odds = call_amount / (pot + call_amount) if pot > 0 else 1.0

                # More likely to fold if bet is large relative to pot
                if pot_odds > 0.5 and random.random() > aggression:
                    return (BettingAction.FOLD, 0.0)
                elif random.random() < aggression * 0.4:
                    # Sometimes raise with medium hands
                    raise_amount = min(call_amount * 1.5, player_energy * 0.25)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    # Usually call
                    return (BettingAction.CALL, call_amount)

        # Weak hands (high card)
        else:
            if call_amount == 0:
                # No bet - usually check, rarely bluff
                if random.random() < aggression * 0.2:
                    # Bluff
                    raise_amount = min(pot * 0.4, player_energy * 0.15)
                    return (BettingAction.RAISE, raise_amount)
                else:
                    return (BettingAction.CHECK, 0.0)
            else:
                # There's a bet - usually fold, rarely bluff call
                if random.random() < aggression * 0.15:
                    # Bluff call
                    return (BettingAction.CALL, call_amount)
                else:
                    return (BettingAction.FOLD, 0.0)

    @staticmethod
    def simulate_multi_round_game(
        initial_bet: float,
        player1_energy: float,
        player2_energy: float,
        player1_aggression: float = AGGRESSION_MEDIUM,
        player2_aggression: float = AGGRESSION_MEDIUM,
        button_position: int = 1
    ) -> PokerGameState:
        """
        Simulate a complete multi-round Texas Hold'em poker game with blinds.

        Args:
            initial_bet: Base bet amount (used to calculate blinds)
            player1_energy: Player 1's available energy
            player2_energy: Player 2's available energy
            player1_aggression: Player 1's aggression factor
            player2_aggression: Player 2's aggression factor
            button_position: Which player has the button (1 or 2)

        Returns:
            PokerGameState with final game results
        """
        # Calculate blinds from initial bet
        big_blind = initial_bet
        small_blind = initial_bet / 2

        # Ensure blinds don't exceed available energy
        big_blind = min(big_blind, player1_energy, player2_energy)
        small_blind = min(small_blind, player1_energy, player2_energy, big_blind / 2)

        game_state = PokerGameState(small_blind=small_blind, big_blind=big_blind, button_position=button_position)

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
            max_actions_per_round = 10  # Prevent infinite loops
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
                    hand = PokerEngine.evaluate_hand(game_state.player1_hole_cards, game_state.community_cards)
                    current_bet = game_state.player1_current_bet
                    opponent_bet = game_state.player2_current_bet
                    remaining_energy = player1_remaining
                    aggression = player1_aggression
                else:
                    hand = PokerEngine.evaluate_hand(game_state.player2_hole_cards, game_state.community_cards)
                    current_bet = game_state.player2_current_bet
                    opponent_bet = game_state.player1_current_bet
                    remaining_energy = player2_remaining
                    aggression = player2_aggression

                # Decide action
                action, bet_amount = PokerEngine.decide_action(
                    hand=hand,
                    current_bet=current_bet,
                    opponent_bet=opponent_bet,
                    pot=game_state.pot,
                    player_energy=remaining_energy,
                    aggression=aggression
                )

                # Record action
                game_state.betting_history.append((current_player, action, bet_amount))

                # Process action
                if action == BettingAction.FOLD:
                    if current_player == 1:
                        game_state.player1_folded = True
                    else:
                        game_state.player2_folded = True
                    break

                elif action == BettingAction.CHECK:
                    # Check - no bet
                    pass

                elif action == BettingAction.CALL:
                    # Call - match opponent's bet
                    game_state.player_bet(current_player, bet_amount)
                    if current_player == 1:
                        player1_remaining -= bet_amount
                    else:
                        player2_remaining -= bet_amount

                elif action == BettingAction.RAISE:
                    # Raise - increase bet
                    # First call to match, then add raise amount
                    call_amount = opponent_bet - current_bet
                    total_bet = call_amount + bet_amount
                    game_state.player_bet(current_player, total_bet)
                    if current_player == 1:
                        player1_remaining -= total_bet
                    else:
                        player2_remaining -= total_bet

                actions_this_round += 1

                # Check if betting is complete for this round
                # Complete if both players have equal bets and at least one has acted
                if (game_state.player1_current_bet == game_state.player2_current_bet and
                    actions_this_round >= 2):
                    break

                # Switch to other player
                current_player = 2 if current_player == 1 else 1

        # Game is over - evaluate final hands at showdown
        game_state.current_round = BettingRound.SHOWDOWN

        # Evaluate best hands using all 7 cards (2 hole + 5 community)
        if not game_state.player1_folded:
            game_state.player1_hand = PokerEngine.evaluate_hand(
                game_state.player1_hole_cards,
                game_state.community_cards
            )
        if not game_state.player2_folded:
            game_state.player2_hand = PokerEngine.evaluate_hand(
                game_state.player2_hole_cards,
                game_state.community_cards
            )

        return game_state

    @staticmethod
    def resolve_bet(
        hand1: PokerHand,
        hand2: PokerHand,
        bet1_amount: float,
        bet2_amount: float
    ) -> Tuple[float, float]:
        """
        Resolve a poker bet between two hands with proper kicker comparison.

        Args:
            hand1: First player's hand
            hand2: Second player's hand
            bet1_amount: Amount wagered by first player
            bet2_amount: Amount wagered by second player

        Returns:
            Tuple of (player1_winnings, player2_winnings)
            This is a zero-sum game, so winnings sum to 0
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
    def simulate_game(bet_amount: float = 10.0, player1_energy: float = 100.0,
                     player2_energy: float = 100.0) -> PokerGameState:
        """
        Simulate a complete Texas Hold'em poker game between two players.

        Args:
            bet_amount: Base bet amount (for blinds)
            player1_energy: Player 1's available energy
            player2_energy: Player 2's available energy

        Returns:
            PokerGameState with complete game results
        """
        return PokerEngine.simulate_multi_round_game(
            initial_bet=bet_amount,
            player1_energy=player1_energy,
            player2_energy=player2_energy
        )


# Example usage and testing
if __name__ == "__main__":
    print("Texas Hold'em Poker Engine Test")
    print("=" * 80)

    # Test hand evaluation
    print("\nTest 1: Hand Evaluation")
    print("-" * 80)

    # Create test hands
    deck = Deck()
    hole_cards = deck.deal(2)
    community_cards = deck.deal(5)

    print(f"Hole cards: {' '.join(str(c) for c in hole_cards)}")
    print(f"Community cards: {' '.join(str(c) for c in community_cards)}")

    hand = PokerEngine.evaluate_hand(hole_cards, community_cards)
    print(f"Best hand: {hand}")
    print(f"Hand cards: {' '.join(str(c) for c in hand.cards)}")

    # Test a few complete games
    print("\n" + "=" * 80)
    print("Simulating 5 complete Texas Hold'em games:")
    print("=" * 80)

    for i in range(5):
        game = PokerEngine.simulate_game(bet_amount=10.0, player1_energy=100.0, player2_energy=100.0)

        print(f"\nGame {i+1}:")
        print(f"  Button: Player {game.button_position}")
        print(f"  Blinds: {game.small_blind}/{game.big_blind}")

        if game.player1_hole_cards:
            print(f"  Player 1 hole cards: {' '.join(str(c) for c in game.player1_hole_cards)}")
        if game.player2_hole_cards:
            print(f"  Player 2 hole cards: {' '.join(str(c) for c in game.player2_hole_cards)}")

        if game.community_cards:
            print(f"  Community cards: {' '.join(str(c) for c in game.community_cards)}")

        winner = game.get_winner_by_fold()
        if winner:
            print(f"  Result: Player {winner} wins by fold (pot: {game.pot:.1f})")
        else:
            print(f"  Player 1 hand: {game.player1_hand}")
            print(f"  Player 2 hand: {game.player2_hand}")

            if game.player1_hand.beats(game.player2_hand):
                print(f"  Winner: Player 1 (pot: {game.pot:.1f})")
            elif game.player2_hand.beats(game.player1_hand):
                print(f"  Winner: Player 2 (pot: {game.pot:.1f})")
            else:
                print(f"  Result: Tie - pot split (pot: {game.pot:.1f})")
