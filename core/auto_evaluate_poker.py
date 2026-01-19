"""Auto-evaluation poker game for testing fish poker skills.

This module manages automated poker games where multiple fish play against
a standard poker evaluation algorithm with variance reduction through
position-rotated duplicate deals.

## Position Rotation (Duplicate Deal Semantics)

For fair evaluation with minimal positional variance:
1. Each "deal set" uses a specific RNG seed to deal cards
2. The same deal is replayed N times (N = number of players)
3. In each replay, players rotate seats so everyone experiences each position
4. This cancels out positional luck - only skill matters

## Statistical Benefits

- Position advantage/disadvantage averages out across rotations
- Card luck still varies between deal sets but is the same within a set
- Results converge much faster than single-pass evaluation
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Import directly from source modules to avoid lazy import issues
from core.poker.betting.actions import BettingRound
from core.poker.core.cards import Card, Deck
from core.poker.simulation.hand_engine import Deal, determine_payouts, simulate_hand_from_deal
from core.poker.strategy.implementations import PokerStrategyAlgorithm

logger = logging.getLogger(__name__)

# Global shutdown flag for graceful termination of long-running loops
# This allows background threads to exit when the main process receives Ctrl+C
_shutdown_requested = False


def request_shutdown() -> None:
    """Request shutdown of all auto-evaluate poker games."""
    global _shutdown_requested
    _shutdown_requested = True


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested


@dataclass
class EvalPlayerState:
    """Represents the state of a player in an auto-evaluation game."""

    player_id: str
    name: str
    energy: float
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: float = 0.0
    total_bet: float = 0.0
    folded: bool = False
    is_standard: bool = False  # True if this is the standard algorithm player
    starting_energy: float = 0.0
    # For fish player
    poker_strategy: Optional[PokerStrategyAlgorithm] = None
    fish_id: Optional[int] = None
    fish_generation: Optional[int] = None
    plant_id: Optional[int] = None
    species: str = "fish"
    # Stats tracking
    hands_won: int = 0
    hands_lost: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0
    showdowns_played: int = 0
    showdowns_won: int = 0


@dataclass
class AutoEvaluateStats:
    """Statistics for the auto-evaluation game."""

    hands_played: int = 0
    hands_remaining: int = 1000
    players: List[Dict[str, Any]] = field(default_factory=list)  # List of player stats
    game_over: bool = False
    winner: Optional[str] = None
    reason: str = ""
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    # For heads-up benchmark evaluation
    net_bb_for_candidate: Optional[float] = None


class AutoEvaluatePokerGame:
    """Manages an automated poker evaluation game between multiple fish and standard algorithm.

    Supports position-rotated duplicate deals for reduced variance evaluation.
    When position_rotation=True, each dealt hand is replayed N times (N = number of players),
    rotating seat assignments so every player experiences every position with the same cards.
    """

    def __init__(
        self,
        game_id: str,
        player_pool: List[Dict[str, Any]],
        standard_energy: float = 500.0,
        max_hands: int = 2000,
        small_blind: float = 5.0,
        big_blind: float = 10.0,
        rng_seed: Optional[int] = None,
        include_standard_player: bool = True,
        position_rotation: bool = True,
    ) -> None:
        """Initialize a new auto-evaluation poker game.

        Args:
            game_id: Unique identifier for this game
            player_pool: Benchmark players (fish and/or plants) containing
                at least a "name" and "poker_strategy" key. Optional metadata
                such as fish_id, plant_id, generation, or species is preserved
                for downstream reporting.
            standard_energy: Starting energy for standard algorithm player
            max_hands: Maximum number of hands to play (default 2000)
            small_blind: Small blind amount
            big_blind: Big blind amount
            rng_seed: Optional RNG seed for deterministic card dealing
            include_standard_player: If True, add standard algorithm player (default True)
            position_rotation: If True, replay each deal with rotated positions for
                fairness. Each unique deal is played N times (N = number of players).
        """
        self.game_id = game_id
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.max_hands = max_hands
        self.hands_played = 0
        self.rng_seed = rng_seed
        self.position_rotation = position_rotation

        # Track current deal set for position rotation
        self._current_deal_seed = rng_seed if rng_seed is not None else 0
        self._rotation_index = 0  # Which rotation we're on for current deal
        self._saved_hole_cards: List[List[Card]] = []  # Cards for each player in base deal
        self._saved_community_cards: List[Card] = []  # Community cards for base deal

        # Create players list
        self.players: List[EvalPlayerState] = []

        # Add fish players - ensure they have enough energy to play all hands
        # With 4 players, blinds rotate, so each player posts SB+BB every 4 hands
        # Minimum energy needed: (SB + BB) * (max_hands / num_players) * 2
        num_players = len(player_pool) + (1 if include_standard_player else 0)
        min_energy_needed = (small_blind + big_blind) * (max_hands / num_players + 1) * 2
        starting_energy = max(standard_energy, min_energy_needed)

        for i, player_data in enumerate(player_pool):
            self.players.append(
                EvalPlayerState(
                    player_id=f"fish_{i}",
                    name=player_data["name"],
                    energy=starting_energy,
                    starting_energy=starting_energy,
                    poker_strategy=player_data["poker_strategy"],
                    fish_id=player_data.get("fish_id"),
                    fish_generation=player_data.get("generation"),
                    plant_id=player_data.get("plant_id"),
                    species=player_data.get("species", "fish"),
                    is_standard=False,
                )
            )

        # Add standard algorithm player (optional for heads-up benchmark mode)
        if include_standard_player:
            self.players.append(
                EvalPlayerState(
                    player_id="standard",
                    name="Standard Algorithm",
                    energy=starting_energy,
                    is_standard=True,
                    starting_energy=starting_energy,
                )
            )

        # Game state
        self.deck = Deck(seed=rng_seed)
        self.community_cards: List[Card] = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP
        self.button_position = 0  # Dealer button position
        self.current_player_index = 0
        self.game_over = False
        self.winner: Optional[str] = None
        self.last_hand_message = ""
        self.performance_history: List[Dict[str, Any]] = []

        # Decision RNG for deterministic standard algorithm decisions
        self._decision_rng = random.Random(rng_seed)

    def get_players(self) -> List[EvalPlayerState]:
        """Get list of players."""
        return self.players

    def _build_deal(self) -> Deal:
        """Create the next deal, applying position rotation when enabled."""
        num_players = len(self.players)

        for player in self.players:
            player.current_bet = 0.0
            player.total_bet = 0.0
            player.folded = False

        self.community_cards = []
        self.pot = 0.0
        self.current_round = BettingRound.PRE_FLOP

        if self.position_rotation:
            if self._rotation_index == 0:
                self._current_deal_seed += 1
                deck = Deck(seed=self._current_deal_seed)
                deck.reset()
                self._saved_hole_cards = [deck.deal(2) for _ in range(num_players)]
                self._saved_community_cards = self._deal_community_cards(deck)

            base_hole_cards = self._saved_hole_cards
            community_cards = list(self._saved_community_cards)
            hole_cards: Dict[int, List[Card]] = {}

            for i, player in enumerate(self.players):
                card_position = (i + self._rotation_index) % num_players
                cards = list(base_hole_cards[card_position])
                player.hole_cards = cards
                hole_cards[i] = cards

            self._rotation_index = (self._rotation_index + 1) % num_players
        else:
            self.deck.reset()
            base_hole_cards = [self.deck.deal(2) for _ in range(num_players)]
            community_cards = self._deal_community_cards(self.deck)
            hole_cards = {}
            for i, player in enumerate(self.players):
                cards = list(base_hole_cards[i])
                player.hole_cards = cards
                hole_cards[i] = cards

        self.button_position = (self.button_position + 1) % num_players
        self.hands_played += 1

        return Deal(
            hole_cards=hole_cards,
            community_cards=community_cards,
            button_position=self.button_position,
        )

    @staticmethod
    def _deal_community_cards(deck: Deck) -> List[Card]:
        """Deal a full board (flop/turn/river) from the given deck."""
        deck.deal(1)
        flop = deck.deal(3)
        deck.deal(1)
        turn = deck.deal_one()
        deck.deal(1)
        river = deck.deal_one()
        return list(flop) + [turn, river]

    def _apply_hand_result(self, game_state, payouts: Dict[int, float]) -> None:
        """Update player stats and energies from a simulated hand."""
        self.community_cards = list(game_state.community_cards)
        self.pot = game_state.pot
        self.current_round = game_state.current_round

        for player_id, player in enumerate(self.players):
            state_player = game_state.players[player_id]
            player.current_bet = state_player.current_bet
            player.total_bet = state_player.total_bet
            player.folded = state_player.folded
            player.energy = state_player.remaining_energy + payouts.get(player_id, 0.0)

        winner_by_fold = game_state.get_winner_by_fold()
        if winner_by_fold is not None:
            winner = self.players[winner_by_fold]
            winner.hands_won += 1
            winner.total_energy_won += self.pot
            for i, player in enumerate(self.players):
                if i != winner_by_fold and player.total_bet > 0:
                    player.hands_lost += 1
                    player.total_energy_lost += player.total_bet
            return

        active_players = [
            player_id for player_id, player in game_state.players.items() if not player.folded
        ]
        for player_id in active_players:
            self.players[player_id].showdowns_played += 1

        winners = [player_id for player_id, payout in payouts.items() if payout > 0.0]
        if len(winners) > 1:
            for player_id in winners:
                self.players[player_id].showdowns_won += 1
                self.players[player_id].total_energy_won += payouts[player_id]
            self.last_hand_message = f"Tie! Pot split among {len(winners)} players."
            return

        if len(winners) == 1:
            winner_id = winners[0]
            winner = self.players[winner_id]
            winner.hands_won += 1
            winner.total_energy_won += payouts[winner_id]
            winner.showdowns_won += 1
            for i, player in enumerate(self.players):
                if i != winner_id and player.total_bet > 0:
                    player.hands_lost += 1
                    player.total_energy_lost += player.total_bet
            winning_hand = game_state.player_hands.get(winner_id)
            if winning_hand is not None:
                self.last_hand_message = f"{winner.name} wins with {winning_hand}!"
            else:
                self.last_hand_message = f"{winner.name} wins!"

    def play_hand(self):
        """Play one complete hand of poker."""
        deal = self._build_deal()
        player_energies = [player.energy for player in self.players]
        player_aggressions = [0.5] * len(self.players)
        player_strategies = [
            None if player.is_standard else player.poker_strategy for player in self.players
        ]

        game_state = simulate_hand_from_deal(
            deal=deal,
            initial_bet=self.big_blind,
            player_energies=player_energies,
            player_aggressions=player_aggressions,
            player_strategies=player_strategies,
            small_blind=self.small_blind,
            rng=self._decision_rng,
        )
        payouts = determine_payouts(game_state)
        self._apply_hand_result(game_state, payouts)

        # Capture performance snapshot after each hand
        self._record_hand_performance()

    def _record_hand_performance(self):
        """Record net energy performance for all players after a hand."""
        snapshot: Dict[str, Any] = {
            "hand": self.hands_played,
            "players": [],
        }

        for player in self.players:
            hands_played = self.hands_played or 1
            win_rate = round((player.hands_won / hands_played) * 100, 1)
            showdown_played = player.showdowns_played
            showdown_win_rate = (
                round((player.showdowns_won / showdown_played) * 100, 1) if showdown_played else 0.0
            )

            net_energy = player.energy - player.starting_energy
            bb_per_100 = (
                round((net_energy / self.big_blind) * (100 / hands_played), 2)
                if self.big_blind > 0 and hands_played
                else 0.0
            )

            snapshot["players"].append(
                {
                    "player_id": player.player_id,
                    "name": player.name,
                    "is_standard": player.is_standard,
                    "species": getattr(player, "species", "fish"),
                    "energy": round(player.energy, 1),
                    "net_energy": round(net_energy, 1),
                    "hands_won": player.hands_won,
                    "hands_lost": player.hands_lost,
                    "win_rate": win_rate,
                    "showdowns_played": player.showdowns_played,
                    "showdowns_won": player.showdowns_won,
                    "showdown_win_rate": showdown_win_rate,
                    "bb_per_100": bb_per_100,
                }
            )

        self.performance_history.append(snapshot)

    def run_evaluation(self) -> AutoEvaluateStats:
        """Run the full evaluation (max_hands or until only one player remains).

        Returns:
            Final evaluation statistics
        """
        # Auto-evaluation runs silently in background

        # Baseline snapshot before any hands are played
        self._record_hand_performance()

        while self.hands_played < self.max_hands:
            # Check for shutdown request (allows Ctrl+C to work)
            if _shutdown_requested:
                logger.debug(f"Poker game {self.game_id}: Shutdown requested, ending early")
                self.game_over = True
                break

            # Check how many players can still play (have energy >= big blind)
            active_players = [p for p in self.players if p.energy >= self.big_blind]

            if len(active_players) <= 1:
                # Only one player left who can afford to play
                self.game_over = True
                if len(active_players) == 1:
                    self.winner = active_players[0].name
                break

            # Play one hand
            self.play_hand()

            # Yield GIL to prevent starving main thread
            time.sleep(0.001)

        # If we completed all hands, determine winner by energy
        if not self.game_over:
            self.game_over = True
            # Find player with most energy
            max_energy = max(p.energy for p in self.players)
            winners = [p for p in self.players if p.energy == max_energy]

            if len(winners) == 1:
                self.winner = winners[0].name
            else:
                self.winner = "Tie"

        return self.get_stats()

    def get_stats(self) -> AutoEvaluateStats:
        """Get current evaluation statistics."""
        # Build player stats list
        players_stats = []
        for player in self.players:
            hands_played = self.hands_played
            net_energy = player.total_energy_won - player.total_energy_lost
            showdown_played = player.showdowns_played
            total_games = player.hands_won + player.hands_lost

            players_stats.append(
                {
                    "player_id": player.player_id,
                    "name": player.name,
                    "is_standard": player.is_standard,
                    "fish_id": player.fish_id,
                    "fish_generation": player.fish_generation,
                    "plant_id": player.plant_id,
                    "species": player.species,
                    "energy": round(player.energy, 1),
                    "hands_won": player.hands_won,
                    "hands_lost": player.hands_lost,
                    "total_energy_won": round(player.total_energy_won, 1),
                    "total_energy_lost": round(player.total_energy_lost, 1),
                    "net_energy": round(net_energy, 1),
                    "win_rate": (
                        round((player.hands_won / total_games) * 100, 1) if total_games else 0.0
                    ),
                    "bb_per_100": (
                        round((net_energy / self.big_blind) * (100 / hands_played), 2)
                        if self.big_blind > 0 and hands_played
                        else 0.0
                    ),
                    "showdowns_played": player.showdowns_played,
                    "showdowns_won": player.showdowns_won,
                    "showdown_win_rate": (
                        round((player.showdowns_won / showdown_played) * 100, 1)
                        if showdown_played
                        else 0.0
                    ),
                }
            )

        return AutoEvaluateStats(
            hands_played=self.hands_played,
            hands_remaining=max(0, self.max_hands - self.hands_played),
            players=players_stats,
            game_over=self.game_over,
            winner=self.winner,
            reason=(
                f"Completed {self.hands_played} hands"
                if self.hands_played >= self.max_hands
                else f"Game ended after {self.hands_played} hands"
            ),
            performance_history=self.performance_history,
        )

    @staticmethod
    def run_heads_up(
        candidate_algo: PokerStrategyAlgorithm,
        benchmark_algo: PokerStrategyAlgorithm,
        candidate_seat: int,
        num_hands: int = 200,
        small_blind: float = 50.0,
        big_blind: float = 100.0,
        starting_stack: float = 10_000.0,
        rng_seed: Optional[int] = None,
    ) -> "AutoEvaluateStats":
        """Run a heads-up match between two algorithms.

        Args:
            candidate_algo: The algorithm being evaluated
            benchmark_algo: The benchmark opponent
            candidate_seat: Which seat (0 or 1) the candidate is in
            num_hands: Number of hands to play
            small_blind: Small blind amount
            big_blind: Big blind amount
            starting_stack: Starting chip stack for each player
            rng_seed: Optional RNG seed for deterministic dealing

        Returns:
            AutoEvaluateStats with net_bb_for_candidate field populated
        """
        # Fast exit during shutdown to keep the process responsive to Ctrl+C.
        if is_shutdown_requested():
            return AutoEvaluateStats(
                hands_played=0,
                hands_remaining=num_hands,
                players=[],
                game_over=True,
                winner=None,
                reason="Shutdown requested",
                performance_history=[],
                net_bb_for_candidate=0.0,
            )

        # Build player pool with candidate in specified seat
        if candidate_seat == 0:
            player_pool = [
                {"name": "Candidate", "poker_strategy": candidate_algo},
                {"name": "Benchmark", "poker_strategy": benchmark_algo},
            ]
        else:
            player_pool = [
                {"name": "Benchmark", "poker_strategy": benchmark_algo},
                {"name": "Candidate", "poker_strategy": candidate_algo},
            ]

        game = AutoEvaluatePokerGame(
            game_id=f"hu_eval_{rng_seed}_{candidate_seat}",
            player_pool=player_pool,
            standard_energy=starting_stack,
            max_hands=num_hands,
            small_blind=small_blind,
            big_blind=big_blind,
            rng_seed=rng_seed,
            include_standard_player=False,  # Pure HU, no standard player
        )

        stats = game.run_evaluation()

        # Verify expected number of hands were played
        if stats.hands_played != num_hands:
            # Early exit is expected when a player busts before `num_hands`.
            # This can be noisy during large benchmark sweeps, so keep it at DEBUG.
            logger.debug(
                f"HU evaluation exited early: expected {num_hands} hands, "
                f"played {stats.hands_played} (all but one player busted)"
            )

        # Use seat-based indexing (candidate is at candidate_seat)
        if candidate_seat < len(stats.players):
            candidate_player_stats = stats.players[candidate_seat]
            net_bb = candidate_player_stats["net_energy"] / big_blind
        else:
            logger.error(f"Candidate seat {candidate_seat} out of range")
            net_bb = 0.0

        stats.net_bb_for_candidate = net_bb
        return stats
