"""Advanced poker strategy system for fish.

This module implements sophisticated poker playing strategies including:
- Hand selection (which starting hands to play)
- Positional awareness (adjust strategy based on button position)
- Opponent modeling (remember and adapt to opponent tendencies)
- Bluffing logic (when to bluff based on game state)

These strategies evolve over time as fish learn from poker outcomes.
"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.poker.core.cards import Card, Rank, Suit
from core.poker.evaluation.strength import evaluate_starting_hand_strength as _evaluate_strength

if TYPE_CHECKING:
    from core.entities import Fish


class HandStrength(Enum):
    """Categories of poker hand strength."""

    PREMIUM = "premium"  # AA, KK, QQ, AK
    STRONG = "strong"  # JJ, TT, AQ, AJ
    MEDIUM = "medium"  # 99-66, KQ, KJ
    WEAK = "weak"  # 55-22, suited connectors
    TRASH = "trash"  # Random low cards


@dataclass
class OpponentModel:
    """Model of an opponent's playing tendencies."""

    fish_id: int
    games_played: int = 0
    hands_won: int = 0
    hands_lost: int = 0
    times_folded: int = 0
    times_raised: int = 0
    times_called: int = 0
    avg_aggression: float = 0.5  # Running average
    is_tight: bool = False  # Folds often
    is_aggressive: bool = False  # Raises often
    is_passive: bool = False  # Calls often
    bluff_frequency: float = 0.0  # Estimated bluff rate
    last_seen_frame: int = 0

    def update_from_game(
        self, won: bool, folded: bool, raised: bool, called: bool, aggression: float, frame: int
    ) -> None:
        """Update model based on observed behavior."""
        self.games_played += 1
        if won:
            self.hands_won += 1
        else:
            self.hands_lost += 1

        if folded:
            self.times_folded += 1
        if raised:
            self.times_raised += 1
        if called:
            self.times_called += 1

        # Update running average of aggression
        self.avg_aggression = (
            self.avg_aggression * (self.games_played - 1) + aggression
        ) / self.games_played

        # Classify playing style
        if self.games_played >= 5:  # Need at least 5 games for classification
            fold_rate = self.times_folded / self.games_played
            raise_rate = self.times_raised / (self.times_raised + self.times_called + 1)

            self.is_tight = fold_rate > 0.5
            self.is_aggressive = raise_rate > 0.6
            self.is_passive = raise_rate < 0.3

            # Estimate bluff frequency (simplistic model)
            if self.hands_won > 0:
                showdown_wins = self.hands_won - self.times_folded  # Rough estimate
                self.bluff_frequency = max(0.0, 1.0 - showdown_wins / max(1, self.hands_won))

        self.last_seen_frame = frame

    def get_win_rate(self) -> float:
        """Get opponent's observed win rate."""
        if self.games_played == 0:
            return 0.5
        return self.hands_won / self.games_played

    def get_style_description(self) -> str:
        """Get a description of opponent's playing style."""
        if self.games_played < 5:
            return "unknown"

        if self.is_tight and self.is_aggressive:
            return "tight-aggressive"
        elif self.is_tight and self.is_passive:
            return "tight-passive"
        elif not self.is_tight and self.is_aggressive:
            return "loose-aggressive"
        elif not self.is_tight and self.is_passive:
            return "loose-passive"
        else:
            return "balanced"


class PokerStrategyEngine:
    """Manages advanced poker decision-making for a fish.

    This engine uses:
    - Hand strength evaluation
    - Position-based adjustments
    - Opponent modeling
    - Learning from past games
    """

    # Hand selection ranges by position
    BUTTON_RANGE_PREMIUM = 0.15  # Play top 15% of hands from button
    BUTTON_RANGE_TIGHT = 0.10  # Play top 10% when tight
    OFF_BUTTON_RANGE = 0.08  # Play top 8% off button

    # Aggression modifiers
    POSITION_AGGRESSION_BONUS = 0.15  # +15% aggression on button
    OPPONENT_TIGHT_MODIFIER = 0.2  # +20% aggression vs tight players
    OPPONENT_AGGRESSIVE_MODIFIER = -0.1  # -10% aggression vs aggressive players

    def __init__(self, fish: "Fish"):
        """Initialize the poker strategy engine."""
        self.fish = fish

        # Opponent models (fish_id -> OpponentModel)
        self.opponent_models: Dict[int, OpponentModel] = {}

        # Hand selection preferences (learned over time)
        self.hand_selection_tightness = 0.5  # 0=loose, 1=tight
        self.positional_awareness = 0.5  # 0=ignore position, 1=strict position play
        self.bluff_frequency = 0.2  # Base bluff frequency

    def get_opponent_model(self, opponent_id: int) -> OpponentModel:
        """Get or create opponent model."""
        if opponent_id not in self.opponent_models:
            self.opponent_models[opponent_id] = OpponentModel(fish_id=opponent_id)
        return self.opponent_models[opponent_id]

    def update_opponent_model(
        self,
        opponent_id: int,
        won: bool,
        folded: bool,
        raised: bool,
        called: bool,
        aggression: float,
        frame: int,
    ) -> None:
        """Update our model of an opponent's playing style."""
        model = self.get_opponent_model(opponent_id)
        model.update_from_game(won, folded, raised, called, aggression, frame)

    # Rank and suit mappings for converting tuple format to Card objects
    _RANK_MAP = {
        "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
        "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
        "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE,
    }
    _SUIT_MAP = {
        "c": Suit.CLUBS, "d": Suit.DIAMONDS, "h": Suit.HEARTS, "s": Suit.SPADES,
    }

    def evaluate_starting_hand_strength(self, hole_cards: List[Tuple[str, str]]) -> float:
        """Evaluate the strength of starting hole cards (0.0-1.0).

        Delegates to core.poker.evaluation.strength for the actual evaluation.
        """
        if len(hole_cards) != 2:
            return 0.5

        # Convert tuple format (rank, suit) to Card objects
        try:
            cards = [
                Card(self._RANK_MAP[r], self._SUIT_MAP[s.lower()])
                for r, s in hole_cards
            ]
        except (KeyError, AttributeError):
            return 0.5  # Invalid card format

        # Delegate to the canonical implementation (without position adjustment)
        return _evaluate_strength(cards, position_on_button=False)

    def should_play_hand(
        self,
        hole_cards: List[Tuple[str, str]],
        position_on_button: bool,
        opponent_id: Optional[int] = None,
    ) -> bool:
        """Decide whether to play this starting hand."""
        hand_strength = self.evaluate_starting_hand_strength(hole_cards)

        # Determine hand selection range based on position and learning
        if position_on_button:
            # Looser from button
            base_range = self.BUTTON_RANGE_PREMIUM
            # Adjust based on learned positional awareness
            range_adjustment = self.positional_awareness * 0.05
            hand_range = base_range + range_adjustment
        else:
            # Tighter off button
            hand_range = self.OFF_BUTTON_RANGE

        # Adjust based on hand selection tightness (learned behavior)
        hand_range *= 1.0 + (0.5 - self.hand_selection_tightness) * 0.3

        # Adjust based on opponent model
        if opponent_id is not None:
            opponent = self.get_opponent_model(opponent_id)
            if opponent.games_played >= 5:
                if opponent.is_tight:
                    # Play looser vs tight opponents (steal their blinds)
                    hand_range *= 1.2
                elif opponent.is_aggressive:
                    # Play tighter vs aggressive opponents
                    hand_range *= 0.9

        # Decision: play if hand strength is in top X% of hands
        threshold = 1.0 - hand_range
        return hand_strength >= threshold

    def calculate_adjusted_aggression(
        self,
        base_aggression: float,
        position_on_button: bool,
        opponent_id: Optional[int] = None,
        hand_strength: float = 0.5,
    ) -> float:
        """Calculate aggression level adjusted for position and opponent."""
        adjusted = base_aggression

        # Position adjustment
        if position_on_button:
            adjusted += self.POSITION_AGGRESSION_BONUS * self.positional_awareness

        # Opponent adjustment
        if opponent_id is not None:
            opponent = self.get_opponent_model(opponent_id)
            if opponent.games_played >= 5:
                if opponent.is_tight:
                    adjusted += self.OPPONENT_TIGHT_MODIFIER
                elif opponent.is_aggressive:
                    adjusted += self.OPPONENT_AGGRESSIVE_MODIFIER

        # Hand strength adjustment
        if hand_strength > 0.8:
            # Very strong hand - increase aggression
            adjusted += 0.1
        elif hand_strength < 0.4:
            # Weak hand - reduce aggression (unless bluffing)
            adjusted -= 0.15

        # Clamp to valid range
        return max(0.3, min(0.9, adjusted))

    def should_bluff(
        self,
        position_on_button: bool,
        opponent_id: Optional[int] = None,
        pot_size: float = 0.0,
        hand_strength: float = 0.0,
    ) -> bool:
        """Decide whether to bluff in this situation."""
        # Base bluff frequency
        bluff_chance = self.bluff_frequency

        # Increase bluff frequency on button
        if position_on_button:
            bluff_chance *= 1.5

        # Adjust based on opponent
        if opponent_id is not None:
            opponent = self.get_opponent_model(opponent_id)
            if opponent.games_played >= 5:
                if opponent.is_tight and opponent.is_passive:
                    # Bluff more vs tight-passive (they fold a lot)
                    bluff_chance *= 1.8
                elif opponent.is_aggressive:
                    # Bluff less vs aggressive (they call/raise)
                    bluff_chance *= 0.5

        # Bluff more with medium hands, less with very weak hands
        if 0.3 < hand_strength < 0.6:
            bluff_chance *= 1.2
        elif hand_strength < 0.2:
            bluff_chance *= 0.6

        # Random decision
        return random.random() < bluff_chance

    def learn_from_poker_outcome(
        self,
        won: bool,
        hand_strength: float,
        position_on_button: bool,
        bluffed: bool,
        opponent_id: Optional[int] = None,
    ) -> None:
        """Update strategy based on poker game outcome."""
        learning_rate = 0.05

        if won:
            # Win - reinforce strategy
            if bluffed:
                # Successful bluff - increase bluff frequency slightly
                self.bluff_frequency = min(0.4, self.bluff_frequency + learning_rate * 0.5)

            if position_on_button:
                # Won from button - increase positional awareness
                self.positional_awareness = min(1.0, self.positional_awareness + learning_rate)

            if hand_strength < 0.4:
                # Won with weak hand - loosen hand selection
                self.hand_selection_tightness = max(
                    0.0, self.hand_selection_tightness - learning_rate
                )
        else:
            # Loss - adjust strategy
            if bluffed:
                # Failed bluff - decrease bluff frequency
                self.bluff_frequency = max(0.05, self.bluff_frequency - learning_rate * 0.3)

            if hand_strength < 0.5:
                # Lost with weak hand - tighten hand selection
                self.hand_selection_tightness = min(
                    1.0, self.hand_selection_tightness + learning_rate * 0.5
                )

    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get summary of current poker strategy."""
        return {
            "hand_selection_tightness": self.hand_selection_tightness,
            "positional_awareness": self.positional_awareness,
            "bluff_frequency": self.bluff_frequency,
            "opponents_tracked": len(self.opponent_models),
            "opponents_modeled": sum(
                1 for m in self.opponent_models.values() if m.games_played >= 5
            ),
        }

    def get_opponent_summary(self, opponent_id: int) -> Dict[str, Any]:
        """Get summary of opponent model."""
        if opponent_id not in self.opponent_models:
            return {}

        model = self.opponent_models[opponent_id]
        return {
            "games_played": model.games_played,
            "win_rate": model.get_win_rate(),
            "style": model.get_style_description(),
            "avg_aggression": model.avg_aggression,
            "bluff_frequency": model.bluff_frequency,
        }
