"""Mixed Fish-Plant poker interaction system.

This module handles poker games between any combination of fish and plants.
Supports 2-6 players with a mix of species.

Refactoring Note:
-----------------
Core betting logic and learning logic have been moved to separate modules:
- core.mixed_poker.betting_round
- core.mixed_poker.cfr_learning
"""

import logging
from typing import TYPE_CHECKING, Any, List, Optional

from core.config.poker import (
    POKER_AGGRESSION_HIGH,
    POKER_AGGRESSION_LOW,
    POKER_ANTE_AMOUNT,
    POKER_MAX_PLAYERS,
)
from core.mixed_poker.betting_round import play_betting_round
from core.mixed_poker.cfr_learning import update_cfr_learning
from core.mixed_poker.state import (
    MultiplayerBettingRound,
    MultiplayerGameState,
    MultiplayerPlayerContext,
)
from core.mixed_poker.types import MixedPokerResult, Player
from core.poker.core import PokerHand

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


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
    POKER_COOLDOWN = 30  # Reduced from 60 for faster poker turnaround

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

        return (
            hasattr(player, "plant_id")
            and hasattr(player, "gain_energy")
            and hasattr(player, "lose_energy")
        )

    def __init__(self, players: List[Player], rng: Optional[Any] = None):
        """Initialize a mixed poker interaction.

        Args:
            players: List of Fish and/or Plant objects (2-6 players)
            rng: Optional RNG for deterministic shuffling

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
        self.rng = rng
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
        target_type: Optional[str] = None,
    ) -> None:
        """Set visual poker effect on a player."""
        from core.entities import Fish
        from core.entities.plant import Plant

        status = "won" if won else "lost"

        if isinstance(player, Fish):
            # Fish uses set_poker_effect method
            if hasattr(player, "set_poker_effect"):
                player.set_poker_effect(
                    status, amount, target_id=target_id, target_type=target_type
                )
            else:
                player.visual_state.poker_effect_state = {
                    "status": status,
                    "amount": amount,
                    "target_id": target_id,
                    "target_type": target_type,
                }
                if hasattr(player, "visual_state"):
                    player.visual_state.poker_effect_timer = 60
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

        # IMPORTANT: During a poker hand, we must not "kill" fish/players mid-hand
        # just because they temporarily go all-in (energy hits 0 due to a bet).
        # If a player later wins the pot, they should remain alive.
        #
        # To prevent irreversible death state transitions during betting, we queue
        # all per-action energy deltas and settle them once at the end of the hand.
        pending_energy_deltas: List[float] = [0.0] * self.num_players
        player_idx_by_object_id = {id(p): i for i, p in enumerate(self.players)}

        def queue_energy_change(player: Player, amount: float) -> None:
            idx = player_idx_by_object_id.get(id(player))
            if idx is None:
                return
            pending_energy_deltas[idx] += float(amount)

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

        # Randomize button position for fairness
        # This ensures all players get equal positional advantage over many games
        from core.util.rng import require_rng_param

        rng = require_rng_param(self.rng, "play_poker")
        button_position = rng.randint(0, self.num_players - 1)

        game_state = MultiplayerGameState(
            num_players=self.num_players,
            small_blind=small_blind,
            big_blind=big_blind,
            button_position=button_position,
            rng=self.rng,
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

        # Collect antes from ALL players
        # This prevents "always fold" strategies from dominating by ensuring
        # every player has some skin in the game before cards are dealt
        for i, (player, ctx) in enumerate(zip(self.players, contexts)):
            ante_amount = min(POKER_ANTE_AMOUNT, ctx.remaining_energy)
            if ante_amount > 0:
                game_state.player_bet(i, ante_amount)
                ctx.remaining_energy -= ante_amount
                # Keep context betting state consistent with game_state.player_current_bets.
                # Antes contribute to the pot and should count toward the amount "to call"
                # in the first betting round.
                ctx.current_bet += ante_amount
                queue_energy_change(player, -ante_amount)

        # Post blinds (in addition to antes)
        sb_pos = (button_position + 1) % self.num_players
        bb_pos = (button_position + 2) % self.num_players

        # Small blind
        sb_amount = min(small_blind, contexts[sb_pos].remaining_energy)
        game_state.player_bet(sb_pos, sb_amount)
        contexts[sb_pos].remaining_energy -= sb_amount
        contexts[sb_pos].current_bet += sb_amount
        queue_energy_change(self.players[sb_pos], -sb_amount)

        # Big blind
        bb_amount = min(big_blind, contexts[bb_pos].remaining_energy)
        game_state.player_bet(bb_pos, bb_amount)
        contexts[bb_pos].remaining_energy -= bb_amount
        contexts[bb_pos].current_bet += bb_amount
        queue_energy_change(self.players[bb_pos], -bb_amount)

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

            # Play the betting round (delegated to helper module)
            round_active = play_betting_round(
                game_state=game_state,
                contexts=contexts,
                start_position=start_pos,
                num_players=self.num_players,
                players=self.players,
                modify_player_energy=queue_energy_change,
                rng=self.rng,
            )
            if not round_active:
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
            queue_energy_change(winner, winnings)
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
                target_type=first_loser_type,
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
                        target_type=winner_type,
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
                queue_energy_change(self.players[i], split_amount)
                # For ties, point to another tied player
                other_tied = next((j for j in tied_players if j != i), i)
                self._set_poker_effect(
                    self.players[i],
                    won=True,
                    amount=0.0,  # No net gain in tie
                    target_id=self._get_player_id(self.players[other_tied]),
                    target_type=self._get_player_type(self.players[other_tied]),
                )

            # Non-tied players are losers
            loser_ids = []
            loser_types = []
            loser_hands = []
            first_winner_id = tied_ids[0] if tied_ids else None
            first_winner_type = (
                self._get_player_type(self.players[tied_players[0]]) if tied_players else None
            )

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
                        target_type=first_winner_type,
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

        # Settle energy deltas once (prevents mid-hand death that can't be undone)
        for i, delta in enumerate(pending_energy_deltas):
            if delta:
                self._modify_player_energy(self.players[i], delta)

        # Set cooldown on all players
        for player in self.players:
            self._set_player_cooldown(player)

        # Update poker stats (pass actual button position for correct stats)
        self._update_poker_stats(
            best_hand_idx, tied_players, game_state.player_total_bets, game_state.button_position
        )

        # Update CFR learning for fish with composable strategies (delegated)
        update_cfr_learning(
            game_state=game_state,
            contexts=contexts,
            winner_idx=best_hand_idx,
            tied_players=tied_players,
            players=self.players,
            get_player_energy=self._get_player_energy,
            initial_player_energies=self._initial_player_energies,
        )

        # Log the game
        logger.debug(
            f"Mixed poker game: {self.fish_count} fish + {self.plant_count} plants, "
            f"winner={self.result.winner_type}#{self.result.winner_id}, "
            f"pot={total_pot:.1f}, rounds={total_rounds}, fold={won_by_fold}"
        )

        return True

    def _update_poker_stats(
        self,
        winner_idx: int,
        tied_players: List[int],
        player_bets: List[float],
        button_position: int = 0,
    ) -> None:
        """Update poker statistics for fish players."""
        from core.entities import Fish
        from core.entities.plant import Plant
        from core.fish.poker_stats_component import FishPokerStats

        # Get context from result if available, otherwise estimate
        house_cut = 0.0
        won_by_fold = False
        players_folded = [False] * self.num_players

        if self.result:
            house_cut = self.result.house_cut
            won_by_fold = self.result.won_by_fold
            players_folded = self.result.players_folded

        active_players_count = sum(1 for f in players_folded if not f)
        reached_showdown = not won_by_fold and active_players_count >= 2

        for i, player in enumerate(self.players):
            # 1. Update Fish Stats
            if isinstance(player, Fish):
                # Ensure component exists
                if not hasattr(player, "poker_stats") or player.poker_stats is None:
                    player.poker_stats = FishPokerStats()

                stats = player.poker_stats
                is_winner = i == winner_idx or i in tied_players
                is_tie = len(tied_players) > 1 and i in tied_players

                # Determine hand rank
                hand_rank = 0
                if self.player_hands[i]:
                    hand_rank = self.player_hands[i].rank_value

                # Use actual button position from the game state
                on_button = i == button_position

                if is_winner and not is_tie:
                    # Winner
                    energy_won = 0.0
                    if self.result:
                        # If single winner, they got energy_transferred
                        # Note: energy_transferred in result is net gain from other players (after cut)
                        # But record_win expects gross or net? FishPokerStats uses it for total_energy_won
                        # Let's use the net gain recorded in result
                        energy_won = self.result.energy_transferred

                    won_at_showdown = not won_by_fold

                    stats.record_win(
                        energy_won=energy_won,
                        house_cut=house_cut,
                        hand_rank=hand_rank,
                        won_at_showdown=won_at_showdown,
                        on_button=on_button,
                    )

                    # Also update legacy/simple stats if they exist
                    if hasattr(player, "poker_wins"):
                        player.poker_wins = getattr(player, "poker_wins", 0) + 1

                elif is_tie:
                    # Tie
                    stats.record_tie(hand_rank=hand_rank, on_button=on_button)

                else:
                    # Loser
                    energy_lost = player_bets[i] if i < len(player_bets) else 0.0

                    stats.record_loss(
                        energy_lost=energy_lost,
                        hand_rank=hand_rank,
                        folded=players_folded[i],
                        reached_showdown=reached_showdown,
                        on_button=on_button,
                    )

                    if hasattr(player, "poker_losses"):
                        player.poker_losses = getattr(player, "poker_losses", 0) + 1

            # 2. Update Plant Stats
            elif isinstance(player, Plant):
                is_winner = i == winner_idx or i in tied_players
                is_tie = len(tied_players) > 1 and i in tied_players

                if is_winner and not is_tie:
                    player.poker_wins += 1
                elif not is_winner:
                    player.poker_losses += 1
