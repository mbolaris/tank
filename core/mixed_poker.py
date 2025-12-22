"""
Mixed Fish-Plant poker interaction system.

This module handles poker games between any combination of fish and plants.
Supports 2-6 players with a mix of species.

Features:
- Full Texas Hold'em with betting rounds for all game sizes (2-6 players)
- Proper blind structure and position-based play
- Multi-round betting: pre-flop, flop, turn, river
- Folding, checking, calling, and raising
"""

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from core.config.poker import (
    POKER_AGGRESSION_HIGH,
    POKER_AGGRESSION_LOW,
    POKER_MAX_ACTIONS_PER_ROUND,
    POKER_MAX_HAND_RANK,
    POKER_MAX_PLAYERS,
)
from core.poker.betting.actions import BettingAction
from core.poker.core import Deck, PokerHand, evaluate_hand
from core.poker.evaluation.strength import evaluate_starting_hand_strength

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.plant import Plant

logger = logging.getLogger(__name__)


class MultiplayerBettingRound(IntEnum):
    """Betting rounds in Texas Hold'em."""
    PRE_FLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3
    SHOWDOWN = 4

# Type alias for players
Player = Union["Fish", "Plant"]


@dataclass
class MixedPokerResult:
    """Result of a mixed poker game."""

    winner_id: int
    winner_type: str  # "fish" or "plant"
    winner_hand: Optional[PokerHand]
    loser_ids: List[int]
    loser_types: List[str]
    loser_hands: List[Optional[PokerHand]]
    energy_transferred: float
    total_pot: float
    house_cut: float
    is_tie: bool
    tied_player_ids: List[int]
    player_count: int
    fish_count: int
    plant_count: int
    # New fields for full Texas Hold'em
    won_by_fold: bool = False
    total_rounds: int = 4
    players_folded: List[bool] = field(default_factory=list)
    betting_history: List[Tuple[int, BettingAction, float]] = field(default_factory=list)


@dataclass
class MultiplayerPlayerContext:
    """Runtime state for a player in multiplayer poker."""
    player: Player
    player_idx: int  # 0-indexed position at table
    remaining_energy: float
    aggression: float
    current_bet: float = 0.0  # Bet in current betting round
    total_bet: float = 0.0  # Total bet across all rounds
    folded: bool = False
    is_all_in: bool = False
    strategy: Optional[Any] = None  # PokerStrategyAlgorithm if available


class MultiplayerGameState:
    """Tracks the state of a multiplayer Texas Hold'em poker game."""

    def __init__(
        self,
        num_players: int,
        small_blind: float = 2.5,
        big_blind: float = 5.0,
        button_position: int = 0,
    ):
        self.num_players = num_players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.button_position = button_position  # 0-indexed

        self.current_round = MultiplayerBettingRound.PRE_FLOP
        self.pot = 0.0
        self.deck = Deck()

        # Per-player state
        self.player_hole_cards: List[List[Any]] = [[] for _ in range(num_players)]
        self.player_hands: List[Optional[PokerHand]] = [None] * num_players
        self.player_current_bets: List[float] = [0.0] * num_players
        self.player_total_bets: List[float] = [0.0] * num_players
        self.player_folded: List[bool] = [False] * num_players
        self.player_all_in: List[bool] = [False] * num_players

        self.community_cards: List[Any] = []
        self.betting_history: List[Tuple[int, BettingAction, float]] = []

        # Raise tracking
        self.min_raise = big_blind
        self.last_raise_amount = big_blind
        self.last_aggressor: Optional[int] = None  # Who made the last raise

    def deal_hole_cards(self) -> None:
        """Deal 2 hole cards to each player."""
        for _ in range(2):
            for player_idx in range(self.num_players):
                if not self.player_folded[player_idx]:
                    self.player_hole_cards[player_idx].append(self.deck.deal_one())

    def deal_flop(self) -> None:
        """Deal the flop (3 community cards)."""
        self.deck.deal(1)  # Burn
        self.community_cards.extend(self.deck.deal(3))

    def deal_turn(self) -> None:
        """Deal the turn (4th community card)."""
        self.deck.deal(1)  # Burn
        self.community_cards.append(self.deck.deal_one())

    def deal_river(self) -> None:
        """Deal the river (5th community card)."""
        self.deck.deal(1)  # Burn
        self.community_cards.append(self.deck.deal_one())

    def advance_round(self) -> None:
        """Move to the next betting round."""
        if self.current_round < MultiplayerBettingRound.SHOWDOWN:
            self.current_round = MultiplayerBettingRound(self.current_round + 1)

            if self.current_round == MultiplayerBettingRound.FLOP:
                self.deal_flop()
            elif self.current_round == MultiplayerBettingRound.TURN:
                self.deal_turn()
            elif self.current_round == MultiplayerBettingRound.RIVER:
                self.deal_river()

            # Reset current round bets
            self.player_current_bets = [0.0] * self.num_players
            self.min_raise = self.big_blind
            self.last_raise_amount = self.big_blind
            self.last_aggressor = None

    def player_bet(self, player_idx: int, amount: float) -> None:
        """Record a player's bet."""
        self.player_current_bets[player_idx] += amount
        self.player_total_bets[player_idx] += amount
        self.pot += amount

    def get_active_player_count(self) -> int:
        """Return number of players still in the hand."""
        return sum(1 for folded in self.player_folded if not folded)

    def get_winner_by_fold(self) -> Optional[int]:
        """Return winner index if only one player remains, None otherwise."""
        active_players = [i for i, folded in enumerate(self.player_folded) if not folded]
        if len(active_players) == 1:
            return active_players[0]
        return None

    def get_max_current_bet(self) -> float:
        """Get the highest current bet among active players."""
        return max(
            bet for i, bet in enumerate(self.player_current_bets)
            if not self.player_folded[i]
        )

    def is_betting_complete(self) -> bool:
        """Check if betting round is complete."""
        active_players = [
            i for i in range(self.num_players)
            if not self.player_folded[i] and not self.player_all_in[i]
        ]

        if not active_players:
            return True

        max_bet = self.get_max_current_bet()
        return all(
            self.player_current_bets[i] == max_bet
            for i in active_players
        )

    def evaluate_hands(self) -> None:
        """Evaluate hands for all active players."""
        for i in range(self.num_players):
            if not self.player_folded[i]:
                self.player_hands[i] = evaluate_hand(
                    self.player_hole_cards[i],
                    self.community_cards
                )


class MixedPokerInteraction:
    """Handles poker games between any mix of fish and plants.

    Supports 2-6 players total, with any combination of fish and plants.
    Uses Full Texas Hold'em with betting rounds for all game sizes.
    """

    # Minimum energy required to play poker
    MIN_ENERGY_TO_PLAY = 10.0

    # Default bet amount
    DEFAULT_BET_AMOUNT = 8.0

    # Cooldown between poker games (in frames)
    POKER_COOLDOWN = 60

    @staticmethod
    def _is_fish_player(player: Any) -> bool:
        """Robust fish detection.

        Uses `isinstance` when possible but falls back to duck-typing to avoid
        issues when modules are reloaded (old instances won't match new classes).
        """
        try:
            from core.entities.fish import Fish  # type: ignore

            if isinstance(player, Fish):
                return True
        except Exception:
            pass

        return hasattr(player, "fish_id") and hasattr(player, "genome")

    @staticmethod
    def _is_plant_player(player: Any) -> bool:
        """Robust plant detection (see `_is_fish_player`)."""
        try:
            from core.entities.plant import Plant  # type: ignore

            if isinstance(player, Plant):
                return True
        except Exception:
            pass

        return hasattr(player, "plant_id") and hasattr(player, "gain_energy") and hasattr(player, "lose_energy")

    def __init__(self, players: List[Player]):
        """Initialize a mixed poker interaction.

        Args:
            players: List of Fish and/or Plant objects (2-6 players)

        Raises:
            ValueError: If fewer than 2 players, more than max players,
                       or no fish players are present.
        """
        if len(players) < 2:
            raise ValueError("Poker requires at least 2 players")

        if len(players) > POKER_MAX_PLAYERS:
            raise ValueError(f"Poker limited to {POKER_MAX_PLAYERS} players max")

        # Check that at least one fish is present
        fish_count = sum(1 for p in players if self._is_fish_player(p))
        if fish_count == 0:
            raise ValueError("MixedPokerInteraction: require at least 1 fish")

        self.players = players
        self.num_players = len(players)
        self.player_hands: List[Optional[PokerHand]] = [None] * self.num_players
        self.result: Optional[MixedPokerResult] = None

        # Categorize players
        self.fish_players = [p for p in players if self._is_fish_player(p)]
        self.plant_players = [p for p in players if self._is_plant_player(p)]
        self.fish_count = len(self.fish_players)
        self.plant_count = len(self.plant_players)

        # Snapshot player energies at the start of the interaction so callers can
        # attribute the net deltas correctly (fish-vs-plant transfer vs house cut).
        self._initial_player_energies: List[float] = [
            self._get_player_energy(p) for p in self.players
        ]

    def _get_player_id(self, player: Player) -> int:
        """Get the stable ID of a player (matching frontend entity IDs).
        
        Uses the PokerPlayer protocol's get_poker_id() method.
        """
        return player.get_poker_id()

    def _get_player_type(self, player: Player) -> str:
        """Get the type of a player (matching frontend entity type names)."""
        if self._is_fish_player(player):
            return "fish"
        elif self._is_plant_player(player):
            return "plant"  # Must match frontend entity type
        return "unknown"

    def _get_player_energy(self, player: Player) -> float:
        """Get the energy of a player."""
        return getattr(player, "energy", 0.0)

    def _get_player_size(self, player: Player) -> float:
        """Get the size of a player."""
        return getattr(player, "size", 1.0)

    def _get_player_strategy(self, player: Player) -> Optional[Any]:
        """Get the poker strategy algorithm of a player.

        Uses the PokerPlayer protocol's get_poker_strategy() method.
        """
        return player.get_poker_strategy()

    def _get_player_aggression(self, player: Player) -> float:
        """Get the poker aggression of a player.
        
        Uses the PokerPlayer protocol's get_poker_aggression() method.
        Maps base aggression (0-1) to poker range.
        """
        base = player.get_poker_aggression()
        return POKER_AGGRESSION_LOW + (base * (POKER_AGGRESSION_HIGH - POKER_AGGRESSION_LOW))

    def _modify_player_energy(self, player: Player, amount: float) -> None:
        """Modify the energy of a player."""
        if self._is_fish_player(player) or hasattr(player, "modify_energy"):
            # Use modify_energy to properly cap at max and route overflow to reproduction/food
            player.modify_energy(amount)
        elif self._is_plant_player(player):
            if amount > 0:
                player.gain_energy(amount)
            else:
                player.lose_energy(abs(amount))

    def _set_player_cooldown(self, player: Player) -> None:
        """Set poker cooldown on a player."""
        if hasattr(player, "poker_cooldown"):
            player.poker_cooldown = self.POKER_COOLDOWN

    def _set_poker_effect(
        self,
        player: Player,
        won: bool,
        amount: float = 0.0,
        target_id: Optional[int] = None,
        target_type: Optional[str] = None
    ) -> None:
        """Set visual poker effect on a player.

        Args:
            player: The player to set the effect on
            won: True if player won, False if lost
            amount: Energy amount won or lost
            target_id: ID of the opponent (for drawing arrows)
            target_type: Type of the opponent ('fish' or 'plant')
        """
        from core.entities import Fish
        from core.entities.plant import Plant

        status = "won" if won else "lost"

        if isinstance(player, Fish):
            # Fish uses set_poker_effect method
            if hasattr(player, "set_poker_effect"):
                player.set_poker_effect(status, amount, target_id=target_id, target_type=target_type)
            else:
                player.poker_effect_state = {
                    "status": status,
                    "amount": amount,
                    "target_id": target_id,
                    "target_type": target_type,
                }
                if hasattr(player, "poker_effect_timer"):
                    player.poker_effect_timer = 60
        elif isinstance(player, Plant):
            # Plants have similar structure
            player.poker_effect_state = {
                "status": status,
                "amount": amount,
                "target_id": target_id,
                "target_type": target_type,
            }
            if hasattr(player, "poker_effect_timer"):
                player.poker_effect_timer = 60

    def can_play_poker(self) -> bool:
        """Check if all players can play poker.

        Returns:
            True if poker game can proceed
        """
        # Need at least 2 players
        if self.num_players < 2:
            return False

        # Require at least 1 fish (no plant-only poker)
        if self.fish_count < 1:
            return False

        for player in self.players:
            # Check if player exists and is valid
            if player is None:
                return False

            # Check if plant is dead
            if self._is_plant_player(player) and player.is_dead():
                return False

            # Check cooldown
            cooldown = getattr(player, "poker_cooldown", 0)
            if cooldown > 0:
                return False

        return True

    def calculate_bet_amount(self, base_bet: float = DEFAULT_BET_AMOUNT) -> float:
        """Calculate the bet amount based on players' energy.

        Args:
            base_bet: Base bet amount

        Returns:
            Calculated bet amount (limited by poorest player)
        """
        # Find the player with lowest energy
        min_energy = min(self._get_player_energy(p) for p in self.players)

        # Bet can't exceed what poorest player can afford
        max_bet = min_energy * 0.3  # Max 30% of poorest player's energy
        return min(base_bet, max_bet, 20.0)  # Also cap at 20

    def _decide_player_action(
        self,
        player_idx: int,
        game_state: MultiplayerGameState,
        contexts: List[MultiplayerPlayerContext],
    ) -> Tuple[BettingAction, float]:
        """Decide action for a player based on hand strength and aggression.

        Args:
            player_idx: Index of the player making the decision
            game_state: Current game state
            contexts: List of player contexts

        Returns:
            Tuple of (action, bet_amount)
        """
        import random

        ctx = contexts[player_idx]

        # Can't act if folded or all-in
        if ctx.folded or ctx.is_all_in:
            return BettingAction.CHECK, 0.0

        # Evaluate current hand strength
        hole_cards = game_state.player_hole_cards[player_idx]
        is_preflop = len(game_state.community_cards) == 0
        position_on_button = (player_idx == game_state.button_position)

        if is_preflop and hole_cards and len(hole_cards) == 2:
            # Pre-flop: use proper starting hand evaluation
            hand_strength = evaluate_starting_hand_strength(hole_cards, position_on_button)
        elif game_state.community_cards:
            hand = evaluate_hand(hole_cards, game_state.community_cards)
            # Normalize hand rank (0-1 scale) using correct constant
            hand_strength = hand.rank_value / POKER_MAX_HAND_RANK
        else:
            hand_strength = 0.5

        # Calculate amount needed to call
        max_bet = game_state.get_max_current_bet()
        call_amount = max_bet - ctx.current_bet

        # Use evolved poker strategy if available (from fish or plant genome)
        if ctx.strategy is not None:
            return ctx.strategy.decide_action(
                hand_strength=hand_strength,
                current_bet=ctx.current_bet,
                opponent_bet=max_bet,
                pot=game_state.pot,
                player_energy=ctx.remaining_energy,
                position_on_button=position_on_button,
            )

        # Fallback: Simple aggression-based decision
        aggression = ctx.aggression
        play_strength = hand_strength + (aggression - 0.5) * 0.2 + random.uniform(-0.1, 0.1)

        if call_amount <= 0:
            # No bet to call - can check or raise
            if play_strength > 0.6 and ctx.remaining_energy > game_state.big_blind * 2:
                # Strong hand or aggressive - raise
                raise_amount = game_state.big_blind * (1 + play_strength * 2)
                raise_amount = min(raise_amount, ctx.remaining_energy)
                return BettingAction.RAISE, raise_amount
            else:
                return BettingAction.CHECK, 0.0
        else:
            # Must call, raise, or fold
            pot_odds = call_amount / (game_state.pot + call_amount) if game_state.pot > 0 else 0.5

            if play_strength > pot_odds + 0.2:
                # Strong hand - might raise
                if play_strength > 0.7 and ctx.remaining_energy > call_amount + game_state.big_blind:
                    raise_amount = call_amount + game_state.big_blind * (1 + play_strength)
                    raise_amount = min(raise_amount, ctx.remaining_energy)
                    return BettingAction.RAISE, raise_amount
                else:
                    return BettingAction.CALL, call_amount
            elif play_strength > pot_odds - 0.1:
                # Marginal hand - call
                if call_amount <= ctx.remaining_energy:
                    return BettingAction.CALL, call_amount
                else:
                    return BettingAction.FOLD, 0.0
            else:
                # Weak hand - fold
                return BettingAction.FOLD, 0.0

    def _play_betting_round(
        self,
        game_state: MultiplayerGameState,
        contexts: List[MultiplayerPlayerContext],
        start_position: int,
    ) -> bool:
        """Play a single betting round.

        Args:
            game_state: Current game state
            contexts: Player contexts
            start_position: Position to start betting from

        Returns:
            True if round completed normally, False if only one player remains
        """
        actions_this_round = 0
        current_pos = start_position
        players_acted = set()

        while actions_this_round < POKER_MAX_ACTIONS_PER_ROUND * self.num_players:
            # Safety check: if all active players are all-in, we're done
            # This prevents infinite loop where we keep skipping all-in players
            active_can_act = [
                i for i in range(self.num_players)
                if not contexts[i].folded and not contexts[i].is_all_in
            ]
            if not active_can_act:
                return game_state.get_active_player_count() > 1

            # Skip folded or all-in players
            if contexts[current_pos].folded or contexts[current_pos].is_all_in:
                current_pos = (current_pos + 1) % self.num_players
                continue

            # Check if only one player remains
            if game_state.get_active_player_count() <= 1:
                return False

            # Get player action
            action, amount = self._decide_player_action(current_pos, game_state, contexts)

            # Apply action
            if action == BettingAction.FOLD:
                contexts[current_pos].folded = True
                game_state.player_folded[current_pos] = True
                game_state.betting_history.append((current_pos, action, 0.0))

            elif action == BettingAction.CHECK:
                game_state.betting_history.append((current_pos, action, 0.0))
                players_acted.add(current_pos)

            elif action == BettingAction.CALL:
                call_amount = min(amount, contexts[current_pos].remaining_energy)
                game_state.player_bet(current_pos, call_amount)
                contexts[current_pos].remaining_energy -= call_amount
                contexts[current_pos].current_bet += call_amount
                # CRITICAL: Actually deduct energy from the player!
                self._modify_player_energy(self.players[current_pos], -call_amount)
                game_state.betting_history.append((current_pos, action, call_amount))
                players_acted.add(current_pos)

                if contexts[current_pos].remaining_energy <= 0:
                    contexts[current_pos].is_all_in = True
                    game_state.player_all_in[current_pos] = True

            elif action == BettingAction.RAISE:
                # First call, then raise
                max_bet = game_state.get_max_current_bet()
                call_amount = max_bet - contexts[current_pos].current_bet

                total_amount = min(amount, contexts[current_pos].remaining_energy)
                raise_portion = total_amount - call_amount

                if raise_portion > 0:
                    game_state.player_bet(current_pos, total_amount)
                    contexts[current_pos].remaining_energy -= total_amount
                    contexts[current_pos].current_bet += total_amount
                    # CRITICAL: Actually deduct energy from the player!
                    self._modify_player_energy(self.players[current_pos], -total_amount)
                    game_state.betting_history.append((current_pos, action, raise_portion))
                    players_acted = {current_pos}  # Reset - others need to act again

                    if contexts[current_pos].remaining_energy <= 0:
                        contexts[current_pos].is_all_in = True
                        game_state.player_all_in[current_pos] = True
                else:
                    # Can't raise, just call
                    game_state.player_bet(current_pos, call_amount)
                    contexts[current_pos].remaining_energy -= call_amount
                    contexts[current_pos].current_bet += call_amount
                    # CRITICAL: Actually deduct energy from the player!
                    self._modify_player_energy(self.players[current_pos], -call_amount)
                    game_state.betting_history.append((current_pos, BettingAction.CALL, call_amount))
                    players_acted.add(current_pos)

            actions_this_round += 1

            # Check if betting round is complete
            active_players = [
                i for i in range(self.num_players)
                if not contexts[i].folded and not contexts[i].is_all_in
            ]

            if not active_players:
                return game_state.get_active_player_count() > 1

            # All active players have acted and bets are equal
            max_bet = game_state.get_max_current_bet()
            all_matched = all(
                contexts[i].current_bet == max_bet or contexts[i].is_all_in
                for i in active_players
            )
            all_acted = all(i in players_acted for i in active_players)

            if all_matched and all_acted:
                return game_state.get_active_player_count() > 1

            current_pos = (current_pos + 1) % self.num_players

        return game_state.get_active_player_count() > 1

    def play_poker(self, bet_amount: Optional[float] = None) -> bool:
        """Play a full Texas Hold'em poker game between all players.

        Uses multi-round betting for all game sizes (2-6 players).

        Args:
            bet_amount: Amount for big blind (uses calculated amount if None)

        Returns:
            True if game completed successfully, False otherwise
        """
        if not self.can_play_poker():
            return False

        # Calculate bet amount (big blind)
        if bet_amount is None:
            bet_amount = self.calculate_bet_amount()
        else:
            bet_amount = self.calculate_bet_amount(bet_amount)

        if bet_amount <= 0:
            return False

        # Create game state
        small_blind = bet_amount / 2
        big_blind = bet_amount
        button_position = 0  # First player has the button

        game_state = MultiplayerGameState(
            num_players=self.num_players,
            small_blind=small_blind,
            big_blind=big_blind,
            button_position=button_position,
        )

        # Create player contexts
        contexts: List[MultiplayerPlayerContext] = []
        for i, player in enumerate(self.players):
            ctx = MultiplayerPlayerContext(
                player=player,
                player_idx=i,
                remaining_energy=self._get_player_energy(player),
                aggression=self._get_player_aggression(player),
                strategy=self._get_player_strategy(player),
            )
            contexts.append(ctx)

        # Post blinds
        sb_pos = (button_position + 1) % self.num_players
        bb_pos = (button_position + 2) % self.num_players

        # Small blind
        sb_amount = min(small_blind, contexts[sb_pos].remaining_energy)
        game_state.player_bet(sb_pos, sb_amount)
        contexts[sb_pos].remaining_energy -= sb_amount
        contexts[sb_pos].current_bet = sb_amount
        self._modify_player_energy(self.players[sb_pos], -sb_amount)

        # Big blind
        bb_amount = min(big_blind, contexts[bb_pos].remaining_energy)
        game_state.player_bet(bb_pos, bb_amount)
        contexts[bb_pos].remaining_energy -= bb_amount
        contexts[bb_pos].current_bet = bb_amount
        self._modify_player_energy(self.players[bb_pos], -bb_amount)

        # Deal hole cards
        game_state.deal_hole_cards()

        # Play betting rounds
        # Pre-flop: action starts after big blind
        start_pos = (bb_pos + 1) % self.num_players

        for round_num in range(4):  # Pre-flop, Flop, Turn, River
            if game_state.get_winner_by_fold() is not None:
                break

            if round_num > 0:
                game_state.advance_round()
                # Reset current bets for new round
                for ctx in contexts:
                    ctx.current_bet = 0.0
                # Post-flop: action starts after button
                start_pos = (button_position + 1) % self.num_players

            # Play the betting round
            if not self._play_betting_round(game_state, contexts, start_pos):
                break  # Only one player remains

        # Evaluate hands and determine winner
        game_state.current_round = MultiplayerBettingRound.SHOWDOWN
        game_state.evaluate_hands()
        self.player_hands = game_state.player_hands

        # Find winner
        winner_by_fold = game_state.get_winner_by_fold()
        won_by_fold = winner_by_fold is not None

        if won_by_fold:
            best_hand_idx = winner_by_fold
            tied_players = [winner_by_fold]
        else:
            # Find best hand among non-folded players
            active_players = [i for i, ctx in enumerate(contexts) if not ctx.folded]
            best_hand_idx = active_players[0]

            for i in active_players[1:]:
                if self.player_hands[i] and self.player_hands[best_hand_idx]:
                    if self.player_hands[i].beats(self.player_hands[best_hand_idx]):
                        best_hand_idx = i

            # Check for ties
            tied_players = [best_hand_idx]
            for i in active_players:
                if i != best_hand_idx:
                    if self.player_hands[i] and self.player_hands[best_hand_idx]:
                        if self.player_hands[i].ties(self.player_hands[best_hand_idx]):
                            tied_players.append(i)

        # Calculate pot and distribute winnings
        total_pot = game_state.pot
        house_cut = 0.0
        energy_transferred = 0.0
        total_rounds = int(game_state.current_round)

        if len(tied_players) == 1:
            # Single winner
            winner = self.players[best_hand_idx]
            winner_id = self._get_player_id(winner)
            winner_type = self._get_player_type(winner)

            # Calculate house cut (keep consistent with fish-vs-fish rules: 8-25% of net_gain)
            winner_size = self._get_player_size(winner)
            winner_bet = game_state.player_total_bets[best_hand_idx]
            net_gain = total_pot - winner_bet

            from core.poker_interaction import calculate_house_cut

            house_cut = calculate_house_cut(winner_size, net_gain)

            # Winner gets pot minus house cut
            winnings = total_pot - house_cut
            self._modify_player_energy(winner, winnings)
            energy_transferred = net_gain - house_cut

            # Get first loser for target info
            first_loser_idx = next((i for i in range(self.num_players) if i != best_hand_idx), None)
            first_loser = self.players[first_loser_idx] if first_loser_idx is not None else None
            first_loser_id = self._get_player_id(first_loser) if first_loser else None
            first_loser_type = self._get_player_type(first_loser) if first_loser else None

            self._set_poker_effect(
                winner,
                won=True,
                amount=energy_transferred,
                target_id=first_loser_id,
                target_type=first_loser_type
            )

            # Collect loser info
            loser_ids = []
            loser_types = []
            loser_hands = []

            # Calculate how much the winner received from each loser
            # Each loser's contribution is proportional to their bet
            total_loser_bets = total_pot - winner_bet

            for i, player in enumerate(self.players):
                if i != best_hand_idx:
                    loser_ids.append(self._get_player_id(player))
                    loser_types.append(self._get_player_type(player))
                    loser_hands.append(self.player_hands[i])

                    # Calculate this loser's contribution to the winner's gain
                    # (proportional to their bet, minus house cut)
                    loser_bet = game_state.player_total_bets[i]
                    if total_loser_bets > 0:
                        loser_contribution = loser_bet * (energy_transferred / total_loser_bets)
                    else:
                        loser_contribution = 0.0

                    self._set_poker_effect(
                        player,
                        won=False,
                        amount=loser_contribution,
                        target_id=winner_id,
                        target_type=winner_type
                    )

            self.result = MixedPokerResult(
                winner_id=winner_id,
                winner_type=winner_type,
                winner_hand=self.player_hands[best_hand_idx],
                loser_ids=loser_ids,
                loser_types=loser_types,
                loser_hands=loser_hands,
                energy_transferred=energy_transferred,
                total_pot=total_pot,
                house_cut=house_cut,
                is_tie=False,
                tied_player_ids=[],
                player_count=self.num_players,
                fish_count=self.fish_count,
                plant_count=self.plant_count,
                won_by_fold=won_by_fold,
                total_rounds=total_rounds,
                players_folded=[ctx.folded for ctx in contexts],
                betting_history=game_state.betting_history,
            )
        else:
            # Tie - split pot among tied players
            tied_ids = [self._get_player_id(self.players[i]) for i in tied_players]
            split_amount = total_pot / len(tied_players)

            for i in tied_players:
                self._modify_player_energy(self.players[i], split_amount)
                # For ties, point to another tied player
                other_tied = next((j for j in tied_players if j != i), i)
                self._set_poker_effect(
                    self.players[i],
                    won=True,
                    amount=0.0,  # No net gain in tie
                    target_id=self._get_player_id(self.players[other_tied]),
                    target_type=self._get_player_type(self.players[other_tied])
                )

            # Non-tied players are losers
            loser_ids = []
            loser_types = []
            loser_hands = []
            first_winner_id = tied_ids[0] if tied_ids else None
            first_winner_type = self._get_player_type(self.players[tied_players[0]]) if tied_players else None

            # Calculate total lost by non-tied players (goes to tied players)
            total_loser_bets = sum(
                game_state.player_total_bets[i]
                for i in range(self.num_players)
                if i not in tied_players
            )

            for i, player in enumerate(self.players):
                if i not in tied_players:
                    loser_ids.append(self._get_player_id(player))
                    loser_types.append(self._get_player_type(player))
                    loser_hands.append(self.player_hands[i])
                    # Show each loser's individual bet (what they lost / contributed to pot)
                    loser_bet = game_state.player_total_bets[i]
                    self._set_poker_effect(
                        player,
                        won=False,
                        amount=loser_bet,
                        target_id=first_winner_id,
                        target_type=first_winner_type
                    )

            self.result = MixedPokerResult(
                winner_id=tied_ids[0],
                winner_type=self._get_player_type(self.players[tied_players[0]]),
                winner_hand=self.player_hands[tied_players[0]],
                loser_ids=loser_ids,
                loser_types=loser_types,
                loser_hands=loser_hands,
                energy_transferred=0.0,
                total_pot=total_pot,
                house_cut=0.0,
                is_tie=True,
                tied_player_ids=tied_ids,
                player_count=self.num_players,
                fish_count=self.fish_count,
                plant_count=self.plant_count,
                won_by_fold=False,
                total_rounds=total_rounds,
                players_folded=[ctx.folded for ctx in contexts],
                betting_history=game_state.betting_history,
            )

        # Set cooldown on all players
        for player in self.players:
            self._set_player_cooldown(player)

        # Update poker stats
        self._update_poker_stats(best_hand_idx, tied_players, bet_amount)

        # Update CFR learning for fish with composable strategies
        self._update_cfr_learning(game_state, contexts, best_hand_idx, tied_players)

        # Log the game
        logger.debug(
            f"Mixed poker game: {self.fish_count} fish + {self.plant_count} plants, "
            f"winner={self.result.winner_type}#{self.result.winner_id}, "
            f"pot={total_pot:.1f}, rounds={total_rounds}, fold={won_by_fold}"
        )

        return True

    def _update_poker_stats(
        self, winner_idx: int, tied_players: List[int], bet_amount: float
    ) -> None:
        """Update poker statistics for fish players."""
        from core.entities import Fish

        for i, player in enumerate(self.players):
            if not isinstance(player, Fish):
                continue

            is_winner = i == winner_idx or i in tied_players
            is_tie = len(tied_players) > 1 and i in tied_players

            # Update fish poker wins/losses
            if hasattr(player, "poker_wins") and hasattr(player, "poker_losses"):
                if is_winner and not is_tie:
                    player.poker_wins = getattr(player, "poker_wins", 0) + 1
                elif not is_winner:
                    player.poker_losses = getattr(player, "poker_losses", 0) + 1

        # Update plant stats
        from core.entities.plant import Plant

        for i, player in enumerate(self.players):
            if not isinstance(player, Plant):
                continue

            is_winner = i == winner_idx or i in tied_players
            is_tie = len(tied_players) > 1 and i in tied_players

            if is_winner and not is_tie:
                player.poker_wins = getattr(player, "poker_wins", 0) + 1
                # Note: update_fitness() removed - fitness_score deprecated
            elif not is_winner:
                player.poker_losses = getattr(player, "poker_losses", 0) + 1

    def _update_cfr_learning(
        self,
        game_state: MultiplayerGameState,
        contexts: List[MultiplayerPlayerContext],
        winner_idx: int,
        tied_players: List[int],
    ) -> None:
        """Update CFR (Counterfactual Regret) learning for fish with composable strategies.

        After each hand, we update the regret tables so fish can learn from experience.
        This implements Lamarckian learning - fish improve during their lifetime.

        Args:
            game_state: The completed game state
            contexts: Player contexts with strategy info
            winner_idx: Index of winning player
            tied_players: Indices of tied players (if tie)
        """
        try:
            from core.poker.strategy.composable_poker import ComposablePokerStrategy
        except ImportError:
            return  # CFR not available

        for i, ctx in enumerate(contexts):
            if ctx.strategy is None:
                continue
            if not isinstance(ctx.strategy, ComposablePokerStrategy):
                continue

            # Skip if this fish hasn't learned an info set yet (no point updating)
            # But we should still process even new fish - they'll create info sets

            # Compute this player's actual outcome (net profit/loss)
            initial_energy = self._initial_player_energies[i]
            final_energy = self._get_player_energy(self.players[i])
            actual_profit = final_energy - initial_energy

            # Compute info set from the hand (using last known hand strength)
            # We use the final board state for simplicity
            hole_cards = game_state.player_hole_cards[i]
            if not hole_cards or len(hole_cards) < 2:
                continue

            # Compute hand strength at showdown
            if game_state.community_cards:
                try:
                    hand = evaluate_hand(hole_cards, game_state.community_cards)
                    hand_strength = hand.rank_value / POKER_MAX_HAND_RANK
                except Exception:
                    hand_strength = 0.5
            else:
                # Pre-flop fold - use starting hand strength
                position_on_button = (i == game_state.button_position)
                hand_strength = evaluate_starting_hand_strength(hole_cards, position_on_button)

            # Pot ratio relative to initial energy
            pot_ratio = game_state.pot / max(1.0, initial_energy)
            position_on_button = (i == game_state.button_position)

            # Get info set
            info_set = ctx.strategy.get_info_set(
                hand_strength, pot_ratio, position_on_button, street=0
            )

            # Determine what action we effectively took (simplified from betting history)
            action_taken = self._infer_action_taken(i, game_state)

            # Compute counterfactual values for each action
            # These are estimates of what we would have won/lost with different actions
            action_values = self._estimate_counterfactual_values(
                i, game_state, contexts, winner_idx, actual_profit
            )

            # Update regret
            ctx.strategy.update_regret(info_set, action_taken, action_values)

    def _infer_action_taken(self, player_idx: int, game_state: MultiplayerGameState) -> str:
        """Infer the primary action taken by a player from betting history.

        Simplifies to one of: fold, call, raise_small, raise_big
        """
        # Look for this player's actions in history
        player_actions = [
            (action, amount) for (idx, action, amount) in game_state.betting_history
            if idx == player_idx
        ]

        if not player_actions:
            return "call"  # Default

        # Find the most aggressive action
        for action, amount in reversed(player_actions):
            if action == BettingAction.FOLD:
                return "fold"
            elif action == BettingAction.RAISE:
                # Determine if small or big raise based on pot
                if amount > game_state.pot * 0.6:
                    return "raise_big"
                else:
                    return "raise_small"
            elif action == BettingAction.CALL:
                continue  # Keep looking for raises

        return "call"

    def _estimate_counterfactual_values(
        self,
        player_idx: int,
        game_state: MultiplayerGameState,
        contexts: List[MultiplayerPlayerContext],
        winner_idx: int,
        actual_profit: float,
    ) -> Dict[str, float]:
        """Estimate what we would have won/lost with each action.

        This is a simplified estimate - true CFR would require re-playing the hand.
        We use heuristics based on the actual outcome.

        Returns:
            Dict mapping action -> estimated counterfactual value
        """
        pot = game_state.pot
        my_bet = game_state.player_total_bets[player_idx]
        i_won = (player_idx == winner_idx)
        i_folded = contexts[player_idx].folded

        # Base values - what we could have won/lost
        if i_folded:
            # We folded - regret not calling/raising if we would have won
            fold_value = -my_bet  # Lost our bet
            # Estimate call/raise values based on hand strength (we don't know outcome)
            # Since we folded, assume call/raise would have been slightly better if we had good hand
            call_value = fold_value * 0.8  # Slightly better than fold on average
            raise_small_value = fold_value * 0.6
            raise_big_value = fold_value * 0.4
        elif i_won:
            # We won - any action that kept us in was good
            fold_value = -my_bet  # Would have lost our bet
            call_value = actual_profit
            raise_small_value = actual_profit * 1.1  # Raising might have won more
            raise_big_value = actual_profit * 1.2  # Big raise might have won even more
        else:
            # We lost - folding would have saved money
            fold_value = -my_bet * 0.3  # Would have lost less (early fold)
            call_value = actual_profit  # What we actually got
            raise_small_value = actual_profit * 0.9  # Raising lost more
            raise_big_value = actual_profit * 0.8  # Big raise lost even more

        return {
            "fold": fold_value,
            "call": call_value,
            "raise_small": raise_small_value,
            "raise_big": raise_big_value,
        }


def check_poker_proximity(
    entity1: Player, entity2: Player, min_distance: float, max_distance: float
) -> bool:
    """Check if two entities are in poker proximity (close but not touching).

    Args:
        entity1: First entity (Fish or Plant)
        entity2: Second entity (Fish or Plant)
        min_distance: Minimum center-to-center distance
        max_distance: Maximum center-to-center distance

    Returns:
        True if entities are in the poker proximity zone
    """
    # Calculate centers
    e1_cx = entity1.pos.x + entity1.width / 2
    e1_cy = entity1.pos.y + entity1.height / 2
    e2_cx = entity2.pos.x + entity2.width / 2
    e2_cy = entity2.pos.y + entity2.height / 2

    dx = e1_cx - e2_cx
    dy = e1_cy - e2_cy
    distance_sq = dx * dx + dy * dy

    min_dist_sq = min_distance * min_distance
    max_dist_sq = max_distance * max_distance

    return min_dist_sq < distance_sq <= max_dist_sq


def should_trigger_plant_poker_asexual_reproduction(fish: "Fish") -> bool:
    """Check if a fish should trigger asexual reproduction after winning against plants.

    When a fish wins a poker hand against only plant opponents (no other fish),
    they get the opportunity to reproduce asexually. This rewards fish that
    successfully "eat" plants through poker.

    Conditions:
    - Fish must have ≥40% of max energy (POST_POKER_REPRODUCTION_ENERGY_THRESHOLD)
    - Fish must not be pregnant
    - Fish must be off reproduction cooldown
    - Fish must be adult life stage

    Args:
        fish: The fish that won the poker game

    Returns:
        True if asexual reproduction should be triggered
    """
    from core.config.fish import POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
    from core.entities.base import LifeStage

    # Check energy threshold
    min_energy_for_reproduction = fish.max_energy * POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
    if fish.energy < min_energy_for_reproduction:
        return False

    # Check off cooldown
    if fish._reproduction_component.reproduction_cooldown > 0:
        return False

    # Check adult life stage (only adults can reproduce)
    if fish._lifecycle_component.life_stage != LifeStage.ADULT:
        return False

    return True
