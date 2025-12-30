"""
Poker hand evaluation for Texas Hold'em.

This module provides hand evaluation logic for determining the best 5-card
poker hand from hole cards and community cards.
"""

from functools import lru_cache
from itertools import combinations
from typing import List, Tuple

from core.poker.core.cards import Card, get_card
from core.poker.core.hand import HandRank, PokerHand

# Pre-computed rank names for fast lookup (index 0-14, only 2-14 valid)
_RANK_NAMES = (
    "",
    "",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "Ten",
    "Jack",
    "Queen",
    "King",
    "Ace",
)


def _rank_name(rank: int) -> str:
    """Get the name of a rank."""
    return _RANK_NAMES[rank] if 2 <= rank <= 14 else str(rank)


def _evaluate_five_cards_core(
    ranks: List[int], suits: List[int]
) -> Tuple[str, HandRank, str, List[int], List[int]]:
    """Core 5-card evaluation logic.

    Args:
        ranks: List of 5 card ranks (integers 2-14), sorted descending
        suits: List of 5 card suits (integers 0-3), in same order as ranks

    Returns:
        Tuple of (hand_type, rank_value, description, primary_ranks, kickers)
    """
    # Count ranks using a simple dict (faster than Counter for 5 items)
    rank_count: dict = {}
    for r in ranks:
        rank_count[r] = rank_count.get(r, 0) + 1

    # Sort by (count desc, rank desc)
    rank_count_list = sorted(rank_count.items(), key=lambda x: (x[1], x[0]), reverse=True)

    # Check for flush (all same suit)
    is_flush = suits[0] == suits[1] == suits[2] == suits[3] == suits[4]

    # Check for straight (including wheel A-2-3-4-5)
    is_straight = False
    straight_high = 0
    if ranks[0] - ranks[4] == 4 and len(rank_count) == 5:
        is_straight = True
        straight_high = ranks[0]
    elif set(ranks) == {14, 2, 3, 4, 5}:
        is_straight = True
        straight_high = 5

    # Evaluate hand type
    if is_straight and is_flush:
        if straight_high == 14:
            return ("royal_flush", HandRank.ROYAL_FLUSH, "Royal Flush", [14], [])
        return (
            "straight_flush",
            HandRank.STRAIGHT_FLUSH,
            f"Straight Flush, {_rank_name(straight_high)} high",
            [straight_high],
            [],
        )

    if rank_count_list[0][1] == 4:
        quad_rank = rank_count_list[0][0]
        kicker = rank_count_list[1][0]
        return (
            "four_of_kind",
            HandRank.FOUR_OF_KIND,
            f"Four {_rank_name(quad_rank)}s",
            [quad_rank],
            [kicker],
        )

    if rank_count_list[0][1] == 3 and rank_count_list[1][1] == 2:
        trips_rank = rank_count_list[0][0]
        pair_rank = rank_count_list[1][0]
        return (
            "full_house",
            HandRank.FULL_HOUSE,
            f"Full House, {_rank_name(trips_rank)}s over {_rank_name(pair_rank)}s",
            [trips_rank, pair_rank],
            [],
        )

    if is_flush:
        return (
            "flush",
            HandRank.FLUSH,
            f"Flush, {_rank_name(ranks[0])} high",
            [],
            list(ranks),
        )

    if is_straight:
        return (
            "straight",
            HandRank.STRAIGHT,
            f"Straight, {_rank_name(straight_high)} high",
            [straight_high],
            [],
        )

    if rank_count_list[0][1] == 3:
        trips_rank = rank_count_list[0][0]
        kickers_list = sorted([rank_count_list[1][0], rank_count_list[2][0]], reverse=True)
        return (
            "three_of_kind",
            HandRank.THREE_OF_KIND,
            f"Three {_rank_name(trips_rank)}s",
            [trips_rank],
            kickers_list,
        )

    if rank_count_list[0][1] == 2 and rank_count_list[1][1] == 2:
        pair1 = rank_count_list[0][0]
        pair2 = rank_count_list[1][0]
        pairs = sorted([pair1, pair2], reverse=True)
        kicker = rank_count_list[2][0]
        return (
            "two_pair",
            HandRank.TWO_PAIR,
            f"Two Pair, {_rank_name(pairs[0])}s and {_rank_name(pairs[1])}s",
            pairs,
            [kicker],
        )

    if rank_count_list[0][1] == 2:
        pair_rank = rank_count_list[0][0]
        kickers_list = sorted(
            [rank_count_list[1][0], rank_count_list[2][0], rank_count_list[3][0]], reverse=True
        )
        return (
            "pair",
            HandRank.PAIR,
            f"Pair of {_rank_name(pair_rank)}s",
            [pair_rank],
            kickers_list,
        )

    # High card
    return (
        "high_card",
        HandRank.HIGH_CARD,
        f"High Card {_rank_name(ranks[0])}",
        [],
        list(ranks),
    )


def _evaluate_five_cards(cards: List[Card]) -> PokerHand:
    """Evaluate exactly 5 Card objects and return the poker hand."""
    # Sort cards by rank descending
    sorted_cards = sorted(cards, key=lambda c: c.rank, reverse=True)
    ranks = [c.rank for c in sorted_cards]
    suits = [c.suit for c in sorted_cards]

    hand_type, rank_value, description, primary_ranks, kickers = _evaluate_five_cards_core(
        ranks, suits
    )
    return PokerHand(
        hand_type=hand_type,
        rank_value=rank_value,
        description=description,
        cards=sorted_cards,
        primary_ranks=primary_ranks,
        kickers=kickers,
    )


@lru_cache(maxsize=4096)
def _evaluate_five_cards_cached(five_cards_key: Tuple[int, int, int, int, int]) -> PokerHand:
    """Cached hand evaluation using compact int keys.

    `five_cards_key` is a tuple of 5 integers encoding (rank << 2) | suit,
    sorted by rank descending. Evaluates directly from integers to avoid
    Enum construction overhead in the hot path.
    """
    # Extract ranks and suits directly (no Enum construction)
    ranks = [(k >> 2) for k in five_cards_key]
    suits = [(k & 3) for k in five_cards_key]

    hand_type, rank_value, description, primary_ranks, kickers = _evaluate_five_cards_core(
        ranks, suits
    )
    cards = [get_card(r, s) for r, s in zip(ranks, suits)]
    return PokerHand(
        hand_type=hand_type,
        rank_value=rank_value,
        description=description,
        cards=cards,
        primary_ranks=primary_ranks,
        kickers=kickers,
    )


def _make_pokerhand_from_ints(
    hand_type, rank_value, description, card_ints, primary_ranks, kickers
) -> PokerHand:
    """Build PokerHand from integer card representations.

    card_ints is an iterable of (rank, suit) integer tuples.
    """
    cards = [get_card(r, s) for r, s in card_ints]
    return PokerHand(
        hand_type=hand_type,
        rank_value=rank_value,
        description=description,
        cards=cards,
        primary_ranks=primary_ranks,
        kickers=kickers,
    )


def evaluate_hand(hole_cards: List[Card], community_cards: List[Card]) -> PokerHand:
    """
    Evaluate the best 5-card poker hand from hole cards and community cards.

    Args:
        hole_cards: Player's 2 hole cards
        community_cards: 0-5 community cards

    Returns:
        PokerHand with rank, description, and kickers
    """
    # Implementation notes:
    # - Each 5-card combination is sorted once and passed to a cached
    #   evaluator (`_evaluate_five_cards_cached`) to avoid repeated work.
    # - The cache key is the tuple of Card objects; Card instances are
    #   expected to be stable/immutable during evaluations.
    # Combine all available cards
    all_cards = hole_cards + community_cards
    n_cards = len(all_cards)

    if n_cards < 5:
        # Not enough cards yet - return high card from what we have
        sorted_cards = sorted(all_cards, key=lambda c: c.rank, reverse=True)
        return PokerHand(
            hand_type="high_card",
            rank_value=HandRank.HIGH_CARD,
            description=f"High Card {_rank_name(sorted_cards[0].rank)}",
            cards=sorted_cards[:5] if len(sorted_cards) >= 5 else sorted_cards,
            primary_ranks=[sorted_cards[0].rank] if sorted_cards else [],
            kickers=[c.rank for c in sorted_cards[1:5]] if len(sorted_cards) > 1 else [],
        )

    # Use an integer-keyed cached evaluator keyed by hole+community card ints
    # to avoid re-evaluating the same card sets repeatedly during betting.
    hole_key = tuple(((c.rank) << 2) | (c.suit) for c in hole_cards)
    community_key = tuple(((c.rank) << 2) | (c.suit) for c in community_cards)
    return evaluate_hand_cached(hole_key, community_key)


@lru_cache(maxsize=16384)
def evaluate_hand_cached(hole_key: Tuple[int, ...], community_key: Tuple[int, ...]) -> PokerHand:
    """Cached evaluate_hand that uses compact int keys for input cards.

    This function reconstructs minimal int lists for ranks and suits and
    reuses `_evaluate_five_cards_cached` for 5-card evaluation. Final
    returned `PokerHand.cards` are constructed as real `Card` objects to
    preserve downstream expectations.
    """
    # Reconstruct lists of (rank,suit) ints
    hole_cards = [((k >> 2), (k & 3)) for k in hole_key]
    community_cards = [((k >> 2), (k & 3)) for k in community_key]

    # Combine
    all_cards_int = hole_cards + community_cards
    n_cards = len(all_cards_int)

    if n_cards < 5:
        # Not enough cards yet - high card from what we have
        sorted_cards = sorted(all_cards_int, key=lambda x: x[0], reverse=True)
        if not sorted_cards:
            return PokerHand(
                hand_type="high_card",
                rank_value=HandRank.HIGH_CARD,
                description="No Cards",
                cards=[],
                primary_ranks=[],
                kickers=[],
            )
        top_rank = sorted_cards[0][0]
        description = f"High Card {_rank_name(top_rank)}"
        card_ints = sorted_cards[:5]
        return _make_pokerhand_from_ints(
            "high_card",
            HandRank.HIGH_CARD,
            description,
            card_ints,
            [],
            [r for r, s in card_ints[1:5]],
        )

    # For exactly 5 cards, directly evaluate using cached five-card evaluator
    if n_cards == 5:
        # Create compact keys tuple sorted by rank descending
        five_sorted = tuple(sorted([r << 2 | s for r, s in all_cards_int], reverse=True))
        return _evaluate_five_cards_cached(five_sorted)

    # For 6-7 cards, evaluate all 5-card combinations using cached evaluator
    all_sorted = sorted(all_cards_int, key=lambda x: x[0], reverse=True)
    best_hand = None
    for five in combinations(all_sorted, 5):
        key = tuple(((r << 2) | s) for r, s in five)
        hand = _evaluate_five_cards_cached(key)
        if best_hand is None or hand.beats(best_hand):
            best_hand = hand
    return best_hand
