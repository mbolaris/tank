"""
Fish poker interaction system.

This module handles poker games between fish when they collide.
The outcome determines energy transfer between the fish.

Features:
- Full Texas Hold'em with betting rounds for all player counts (2+)
- Genome-based poker aggression: Each fish's poker playing style is determined
  by their genome's aggression trait, which evolves over generations
- Evolutionary pressure: Fish with optimal poker aggression levels win more energy,
  survive longer, and reproduce more, spreading their poker genes
- Bluffing, folding, and position play
- Strategy learning and behavioral adaptation
"""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from core.entities import LifeStage
from core.poker.betting import AGGRESSION_HIGH, AGGRESSION_LOW, BettingAction
from core.poker.core import PokerHand
from core.poker.simulation import simulate_multi_round_game, simulate_multiplayer_game
from core.poker.strategy.base import PokerStrategyEngine

if TYPE_CHECKING:
    from core.entities import Fish
    from core.fish.poker_stats_component import FishPokerStats


@dataclass
class PokerResult:
    """Result of a poker game between multiple fish."""

    player_hands: List[PokerHand]  # Hands of all players
    player_ids: List[int]  # IDs of all players
    energy_transferred: float  # Amount loser(s) lost combined
    winner_actual_gain: float  # Amount winner gained (losers' bets minus house cut)
    winner_id: int  # ID of the winning fish
    loser_ids: List[int]  # IDs of all losing fish
    won_by_fold: bool  # True if winner won because all opponents folded
    total_rounds: int  # Number of betting rounds completed
    final_pot: float  # Final pot size
    button_position: int  # Which player had the button (0-indexed)
    players_folded: List[bool]  # Did each player fold
    reached_showdown: bool  # Did game reach showdown
    betting_history: List[Tuple[int, "BettingAction", float]]  # Betting actions taken
    reproduction_occurred: bool = False  # True if fish reproduced after poker
    offspring: Optional["Fish"] = None  # The baby fish created (if reproduction occurred)

    # Legacy fields for backwards compatibility with 2-player games
    @property
    def hand1(self) -> Optional[PokerHand]:
        return self.player_hands[0] if len(self.player_hands) > 0 else None

    @property
    def hand2(self) -> Optional[PokerHand]:
        return self.player_hands[1] if len(self.player_hands) > 1 else None

    @property
    def loser_id(self) -> int:
        return self.loser_ids[0] if len(self.loser_ids) > 0 else -1

    @property
    def player1_folded(self) -> bool:
        return self.players_folded[0] if len(self.players_folded) > 0 else False

    @property
    def player2_folded(self) -> bool:
        return self.players_folded[1] if len(self.players_folded) > 1 else False


@dataclass
class PokerParticipant:
    """Tracks poker-specific state for a fish without storing it on the fish."""

    fish: "Fish"
    strategy: PokerStrategyEngine
    stats: "FishPokerStats"
    cooldown: int = 0
    last_button_position: int = 0
    last_cooldown_age: int = 0

    def sync_with_age(self) -> None:
        """Reduce cooldown based on the fish's current age."""

        age = getattr(self.fish, "age", 0)
        if age > self.last_cooldown_age:
            self.cooldown = max(0, self.cooldown - (age - self.last_cooldown_age))
            self.last_cooldown_age = age

    def start_cooldown(self, frames: int) -> None:
        self.sync_with_age()
        self.cooldown = max(self.cooldown, frames)
        self.last_cooldown_age = getattr(self.fish, "age", self.last_cooldown_age)


_POKER_PARTICIPANTS: Dict[int, PokerParticipant] = {}


def _get_participant(fish: "Fish") -> PokerParticipant:
    """Return cached poker state for a fish, creating it if needed."""

    from core.fish.poker_stats_component import FishPokerStats

    # Ensure fish has poker_stats
    if not hasattr(fish, "poker_stats") or fish.poker_stats is None:
        fish.poker_stats = FishPokerStats()

    participant = _POKER_PARTICIPANTS.get(fish.fish_id)
    if participant is None or participant.fish is not fish:
        participant = PokerParticipant(
            fish=fish,
            strategy=PokerStrategyEngine(fish),
            stats=fish.poker_stats,  # Use the fish's actual stats object
            last_cooldown_age=getattr(fish, "age", 0),
        )
        _POKER_PARTICIPANTS[fish.fish_id] = participant

    # Always update the stats reference in case the fish object was recreated/reloaded
    participant.stats = fish.poker_stats
    participant.fish = fish
    participant.sync_with_age()
    return participant


def should_offer_post_poker_reproduction(
    fish: "Fish", opponent: "Fish", is_winner: bool, energy_gained: float = 0.0
) -> bool:
    """Decide whether to offer reproduction after a poker game.

    DETERMINISTIC reproduction trigger:
    - Fish must have ≥90% of their max energy (proving successful resource acquisition)
    - Fish must not be pregnant
    - Fish must be off reproduction cooldown
    - Fish must be adult
    - Fish must be same species as opponent

    No probabilities - if conditions are met, reproduction occurs. This creates strong
    selection pressure: only successful fish (high energy = good at resource acquisition) reproduce.
    """

    # Require 90% of max energy (high energy threshold for reproduction)
    min_energy_for_reproduction = fish.max_energy * 0.9
    if fish.energy < min_energy_for_reproduction:
        return False

    if fish.is_pregnant or fish.reproduction_cooldown > 0:
        return False

    if fish.life_stage.value < LifeStage.ADULT.value:
        return False

    if fish.species != opponent.species:
        return False

    # Deterministic: all conditions met, reproduction occurs
    return True


class PokerInteraction:
    """Handles poker encounters between multiple fish."""

    # Minimum energy required to play poker
    MIN_ENERGY_TO_PLAY = 10.0

    # Default bet amount (used for blind sizing, not actual energy transfer)
    DEFAULT_BET_AMOUNT = 5.0

    # Energy transfer is pot-based: winner takes the pot from losers
    # Then winner pays house cut based on winner's size (8-25% of pot)

    # Cooldown between poker games for the same fish (in frames)
    POKER_COOLDOWN = 60  # 2 seconds at 30fps
    
    # Maximum players per game (limited by 52-card deck: 2 hole cards per player + 8 community/burns)
    # With 52 cards: max = (52 - 8) / 2 = 22, but we use 6 for gameplay balance
    MAX_PLAYERS = 6

    @staticmethod
    def calculate_house_cut(winner_size: float, net_gain: float) -> float:
        """Calculate house cut based on winner's size.
        
        Larger winners pay more: Size 0.35: 8%, Size 1.0: ~20%, Size 1.3: ~25%
        """
        from core.constants import (
            POKER_BET_MIN_SIZE,
            POKER_HOUSE_CUT_MIN_PERCENTAGE,
            POKER_HOUSE_CUT_SIZE_MULTIPLIER,
        )
        
        house_cut_percentage = POKER_HOUSE_CUT_MIN_PERCENTAGE + max(
            0, (winner_size - POKER_BET_MIN_SIZE) * POKER_HOUSE_CUT_SIZE_MULTIPLIER
        )
        # Clamp to 8-25% range
        house_cut_percentage = min(house_cut_percentage, 0.25)
        # Never exceed the winner's profit
        return min(net_gain * house_cut_percentage, net_gain)

    @staticmethod
    def _set_visual_effects(
        winner_fish: "Fish",
        loser_fish_list: List["Fish"],
        winner_gain: float,
        is_tie: bool = False,
    ) -> None:
        """Set poker visual effects for all participants.
        
        Args:
            winner_fish: The fish that won (or None for ties)
            loser_fish_list: List of losing fish (empty for ties)
            winner_gain: Total energy the winner gained (after house cut)
            is_tie: Whether the game was a tie
        """
        from core.constants import FISH_ID_OFFSET
        
        if is_tie:
            # Tie - all fish show tie effect
            if winner_fish:
                winner_fish.set_poker_effect("tie")
            for fish in loser_fish_list:
                fish.set_poker_effect("tie")
            return
        
        winner_stable_id = winner_fish.fish_id + FISH_ID_OFFSET
        num_losers = len(loser_fish_list)
        
        # Calculate per-loser contribution for display
        per_loser_contribution = winner_gain / num_losers if num_losers > 0 else 0.0
        
        # Winner shows gain, pointing to first loser
        if loser_fish_list:
            first_loser_stable_id = loser_fish_list[0].fish_id + FISH_ID_OFFSET
            winner_fish.set_poker_effect(
                "won", winner_gain, target_id=first_loser_stable_id, target_type="fish"
            )
        
        # Each loser shows their contribution
        for loser in loser_fish_list:
            loser.set_poker_effect(
                "lost", per_loser_contribution, target_id=winner_stable_id, target_type="fish"
            )

    def _record_ecosystem_stats(
        self,
        winner_id: int,
        loser_ids: List[int],
        winner_fish: Optional["Fish"],
        loser_fish_list: List["Fish"],
        winner_hand: Optional["PokerHand"],
        loser_hands: List[Optional["PokerHand"]],
        energy_per_loser: float,
        house_cut: float,
    ) -> None:
        """Record poker outcome in ecosystem for stats tracking.
        
        Args:
            winner_id: ID of winner fish (-1 for tie)
            loser_ids: List of loser fish IDs
            winner_fish: Winner fish object
            loser_fish_list: List of loser fish objects
            winner_hand: Winner's poker hand
            loser_hands: List of loser hands (parallel to loser_fish_list)
            energy_per_loser: Energy transferred per loser
            house_cut: Total house cut
        """
        # Need at least one fish with ecosystem
        ecosystem = None
        for fish in self.fish_list:
            if fish.ecosystem is not None:
                ecosystem = fish.ecosystem
                break
        
        if ecosystem is None:
            return
        
        from core.algorithms import get_algorithm_index
        
        # Get winner's algorithm ID
        winner_algo_id = None
        if winner_fish and winner_fish.genome.behavior_algorithm is not None:
            winner_algo_id = get_algorithm_index(winner_fish.genome.behavior_algorithm)
        
        # Record as winner vs each loser
        num_losers = len(loser_fish_list)
        house_cut_per_loser = house_cut / num_losers if num_losers > 0 else 0.0
        
        for i, loser_fish in enumerate(loser_fish_list):
            loser_algo_id = None
            if loser_fish.genome.behavior_algorithm is not None:
                loser_algo_id = get_algorithm_index(loser_fish.genome.behavior_algorithm)
            
            loser_hand = loser_hands[i] if i < len(loser_hands) else None
            
            ecosystem.record_poker_outcome(
                winner_id=winner_id,
                loser_id=loser_fish.fish_id,
                winner_algo_id=winner_algo_id,
                loser_algo_id=loser_algo_id,
                amount=energy_per_loser,
                winner_hand=winner_hand,
                loser_hand=loser_hand,
                house_cut=house_cut_per_loser,
                result=self.result,
                player1_algo_id=winner_algo_id,
                player2_algo_id=loser_algo_id,
            )

    def __init__(self, *fish: "Fish"):
        """
        Initialize a poker interaction between multiple fish.

        Args:
            *fish: Variable number of Fish objects (minimum 2, maximum MAX_PLAYERS)
        """
        if len(fish) < 2:
            raise ValueError("Poker requires at least 2 fish")
        if len(fish) > self.MAX_PLAYERS:
            # Truncate to max players instead of raising error
            fish = fish[:self.MAX_PLAYERS]

        self.fish_list = list(fish)
        self.participants = [_get_participant(f) for f in self.fish_list]
        self.num_players = len(self.fish_list)
        self.player_hands: List[Optional[PokerHand]] = [None] * self.num_players
        self.result: Optional[PokerResult] = None

    # Legacy properties for backwards compatibility
    @property
    def fish1(self) -> "Fish":
        return self.fish_list[0]

    @property
    def fish2(self) -> "Fish":
        return self.fish_list[1] if self.num_players > 1 else self.fish_list[0]

    @property
    def hand1(self) -> Optional[PokerHand]:
        return self.player_hands[0]

    @hand1.setter
    def hand1(self, value: Optional[PokerHand]) -> None:
        self.player_hands[0] = value

    @property
    def hand2(self) -> Optional[PokerHand]:
        return self.player_hands[1] if self.num_players > 1 else None

    @hand2.setter
    def hand2(self, value: Optional[PokerHand]) -> None:
        if self.num_players > 1:
            self.player_hands[1] = value

    @classmethod
    def get_ready_players(cls, fish_list: List["Fish"]) -> List["Fish"]:
        """Return fish that are eligible to play poker right now."""

        ready_players = []

        for fish in fish_list:
            participant = _get_participant(fish)
            participant.sync_with_age()

            if fish.energy < cls.MIN_ENERGY_TO_PLAY:
                continue

            if participant.cooldown > 0:
                continue

            if hasattr(fish, "is_pregnant") and fish.is_pregnant:
                continue

            ready_players.append(fish)

        return ready_players

    def can_play_poker(self) -> bool:
        """
        Check if all fish are willing and able to play poker.

        Returns:
            True if poker game can proceed
        """
        # Need at least 2 fish
        if len(self.fish_list) < 2:
            return False

        # Check for duplicate fish IDs
        fish_ids = [f.fish_id for f in self.fish_list]
        if len(fish_ids) != len(set(fish_ids)):
            return False

        # All fish must have minimum energy
        for fish in self.fish_list:
            if fish.energy < self.MIN_ENERGY_TO_PLAY:
                return False

        # All fish must be off cooldown
        for participant in self.participants:
            participant.sync_with_age()
            if participant.cooldown > 0:
                return False

        # Don't interrupt pregnant fish
        for fish in self.fish_list:
            if hasattr(fish, "is_pregnant") and fish.is_pregnant:
                return False

        return True

    def calculate_bet_amount(self, base_bet: float = DEFAULT_BET_AMOUNT) -> float:
        """
        Calculate the bet amount based on fish energies and sizes.

        The bet is capped at the minimum of:
        - base_bet amount
        - size-adjusted percentage of any fish's current energy
        - Larger fish can bet more (15% at size 0.35, 25% at size 1.0, 30% at size 1.3)

        Args:
            base_bet: Base bet amount

        Returns:
            Actual bet amount to use
        """
        from core.constants import (
            POKER_BET_MIN_PERCENTAGE,
            POKER_BET_MIN_SIZE,
            POKER_BET_SIZE_MULTIPLIER,
        )

        # Calculate max bet for each fish based on size and energy
        max_bets = []
        for fish in self.fish_list:
            # Larger fish can bet a higher percentage of their energy
            # Size 0.35: 15%, Size 1.0: 25%, Size 1.3: 30%
            # Formula: 15% + (size - 0.35) * 15.8% gives range of 15-30%
            bet_percentage = (
                POKER_BET_MIN_PERCENTAGE
                + (fish.size - POKER_BET_MIN_SIZE) * POKER_BET_SIZE_MULTIPLIER
            )
            max_bets.append(fish.energy * bet_percentage)

        # Return the minimum of base_bet and all fish max bets
        return min(base_bet, *max_bets)

    def try_post_poker_reproduction(
        self, winner_fish: "Fish", loser_fish: "Fish", energy_transferred: float
    ) -> Optional["Fish"]:
        """Attempt voluntary sexual reproduction after poker game.

        This is the core of the post-poker evolution system. Both fish can decide
        whether to reproduce based on their energy, fitness, and opponent's traits.

        Args:
            winner_fish: The fish that won the poker game
            loser_fish: The fish that lost the poker game
            energy_transferred: Energy won in the poker game

        Returns:
            Baby fish if reproduction occurred, None otherwise
        """
        # If the fish are not in an environment (e.g., unit tests), skip reproduction.
        # This prevents post-poker mating energy costs from turning a winning fish's
        # net energy change negative, which violates gameplay expectations and tests
        # that require winners to gain energy.
        if winner_fish.environment is None or loser_fish.environment is None:
            return None

        from core.constants import (
            POST_POKER_CROSSOVER_WINNER_WEIGHT,
            POST_POKER_MATING_DISTANCE,
            REPRODUCTION_COOLDOWN,
        )
        from core.genetics import Genome

        # Check distance (fish must still be close enough)
        distance = (winner_fish.pos - loser_fish.pos).length()
        if distance > POST_POKER_MATING_DISTANCE:
            return None

        # Check if winner wants to reproduce
        winner_wants = should_offer_post_poker_reproduction(
            winner_fish, loser_fish, is_winner=True, energy_gained=energy_transferred
        )

        # Check if loser wants to reproduce
        loser_wants = should_offer_post_poker_reproduction(
            loser_fish, winner_fish, is_winner=False, energy_gained=-energy_transferred
        )

        # Both must agree to reproduce
        if not (winner_wants and loser_wants):
            return None

        # Calculate population stress for adaptive mutations
        from core.constants import (
            POPULATION_STRESS_DEATH_RATE_MAX,
            POPULATION_STRESS_MAX_MULTIPLIER,
            POPULATION_STRESS_MAX_TOTAL,
            TARGET_POPULATION,
        )

        population_stress = 0.0
        if winner_fish.ecosystem is not None:
            from core.entities import Fish

            fish_count = len([e for e in winner_fish.environment.agents if isinstance(e, Fish)])
            population_ratio = fish_count / TARGET_POPULATION if TARGET_POPULATION > 0 else 1.0

            if population_ratio < 1.0:
                population_stress = (1.0 - population_ratio) * POPULATION_STRESS_MAX_MULTIPLIER

            if hasattr(winner_fish.ecosystem, "recent_death_rate"):
                death_rate_stress = min(
                    POPULATION_STRESS_DEATH_RATE_MAX, winner_fish.ecosystem.recent_death_rate
                )
                population_stress = min(
                    POPULATION_STRESS_MAX_TOTAL, population_stress + death_rate_stress
                )

        # Create offspring genome using WEIGHTED crossover (winner contributes more DNA)
        from core.constants import (
            POST_POKER_MUTATION_RATE,
            POST_POKER_MUTATION_STRENGTH,
            POST_POKER_PARENT_ENERGY_CONTRIBUTION,
        )

        offspring_genome = Genome.from_parents_weighted(
            parent1=winner_fish.genome,
            parent2=loser_fish.genome,
            parent1_weight=POST_POKER_CROSSOVER_WINNER_WEIGHT,  # Winner contributes 60%
            mutation_rate=POST_POKER_MUTATION_RATE,
            mutation_strength=POST_POKER_MUTATION_STRENGTH,
            population_stress=population_stress,
        )

        # Energy transfer for baby (both parents contribute)
        winner_energy_contribution = POST_POKER_PARENT_ENERGY_CONTRIBUTION
        loser_energy_contribution = POST_POKER_PARENT_ENERGY_CONTRIBUTION

        winner_energy_transfer = winner_fish.energy * winner_energy_contribution
        loser_energy_transfer = loser_fish.energy * loser_energy_contribution
        total_baby_energy = winner_energy_transfer + loser_energy_transfer

        # Parents pay the energy cost
        winner_fish.modify_energy(-winner_energy_transfer)
        loser_fish.modify_energy(-loser_energy_transfer)

        # Set reproduction cooldown for both parents
        winner_fish.reproduction_cooldown = REPRODUCTION_COOLDOWN
        loser_fish.reproduction_cooldown = REPRODUCTION_COOLDOWN

        # Both parents become pregnant (simulate gestation)
        # In this case we'll just create the baby immediately
        # (Could make one parent pregnant for realism, but immediate birth is simpler)

        # Create baby position (between parents)
        from core.constants import BABY_POSITION_RANDOM_RANGE, BABY_SPAWN_MARGIN

        baby_x = (winner_fish.pos.x + loser_fish.pos.x) / 2.0
        baby_y = (winner_fish.pos.y + loser_fish.pos.y) / 2.0

        # Add some randomness
        baby_x += random.uniform(-BABY_POSITION_RANDOM_RANGE, BABY_POSITION_RANDOM_RANGE)
        baby_y += random.uniform(-BABY_POSITION_RANDOM_RANGE, BABY_POSITION_RANDOM_RANGE)

        # Clamp to screen
        baby_x = max(0, min(winner_fish.screen_width - BABY_SPAWN_MARGIN, baby_x))
        baby_y = max(0, min(winner_fish.screen_height - BABY_SPAWN_MARGIN, baby_y))

        # Create baby fish with combined energy from both parents
        from core.entities import Fish

        baby = Fish(
            environment=winner_fish.environment,
            movement_strategy=winner_fish.movement_strategy.__class__(),
            species=winner_fish.species,
            x=baby_x,
            y=baby_y,
            speed=winner_fish.speed / winner_fish.genome.speed_modifier,  # Base speed
            genome=offspring_genome,
            generation=max(winner_fish.generation, loser_fish.generation) + 1,
            ecosystem=winner_fish.ecosystem,
            screen_width=winner_fish.screen_width,
            screen_height=winner_fish.screen_height,
            initial_energy=total_baby_energy,
            parent_id=winner_fish.fish_id,  # Track lineage for phylogenetic tree
        )

        # Record reproduction in ecosystem for both parents
        if winner_fish.ecosystem is not None:
            from core.algorithms import get_algorithm_index

            if winner_fish.genome.behavior_algorithm is not None:
                winner_algo_id = get_algorithm_index(winner_fish.genome.behavior_algorithm)
                if winner_algo_id >= 0:
                    winner_fish.ecosystem.record_reproduction(winner_algo_id)

            if loser_fish.genome.behavior_algorithm is not None:
                loser_algo_id = get_algorithm_index(loser_fish.genome.behavior_algorithm)
                if loser_algo_id >= 0:
                    loser_fish.ecosystem.record_reproduction(loser_algo_id)

        return baby

    def play_poker_multiplayer(self, bet_amount: float) -> bool:
        """
        Play a full Texas Hold'em multiplayer poker game (3+ players).

        Features full betting rounds, bluffing, position play, and strategy learning
        just like the 2-player version.

        Args:
            bet_amount: Base bet amount (used for big blind)

        Returns:
            True if game completed successfully, False otherwise
        """
        # Gather player data for simulation
        player_energies = [fish.energy for fish in self.fish_list]
        
        # Map genome aggression to poker aggression range
        player_aggressions = [
            AGGRESSION_LOW + (fish.genome.aggression * (AGGRESSION_HIGH - AGGRESSION_LOW))
            for fish in self.fish_list
        ]
        
        # Get poker strategy algorithms from fish genomes (if available)
        player_strategies = [
            fish.genome.poker_strategy_algorithm
            if hasattr(fish.genome, "poker_strategy_algorithm")
            else None
            for fish in self.fish_list
        ]
        
        # Rotate button position among participants
        # Use first participant's last position as reference
        button_position = (self.participants[0].last_button_position + 1) % self.num_players
        for participant in self.participants:
            participant.last_button_position = button_position
        
        # Run the full multiplayer poker simulation
        game_state = simulate_multiplayer_game(
            num_players=self.num_players,
            initial_bet=bet_amount,
            player_energies=player_energies,
            player_aggressions=player_aggressions,
            player_strategies=player_strategies,
            button_position=button_position,
        )
        
        # Store hands from game state
        self.player_hands = [
            game_state.player_hands.get(i) for i in range(self.num_players)
        ]
        
        # Determine winner
        winner_by_fold = game_state.get_winner_by_fold()
        won_by_fold = winner_by_fold is not None
        
        if won_by_fold:
            # Someone won by fold
            winner_idx = winner_by_fold
            winner_fish = self.fish_list[winner_idx]
            winner_id = winner_fish.fish_id
        else:
            # Find winner at showdown (best hand among non-folded players)
            active_players = [
                i for i in range(self.num_players) 
                if not game_state.players[i].folded
            ]
            
            if not active_players:
                return False  # Should never happen
            
            best_idx = active_players[0]
            for i in active_players[1:]:
                if self.player_hands[i] and self.player_hands[best_idx]:
                    if self.player_hands[i].beats(self.player_hands[best_idx]):
                        best_idx = i
            
            # Check for ties
            tied_players = [best_idx]
            for i in active_players:
                if i != best_idx and self.player_hands[i] and self.player_hands[best_idx]:
                    if self.player_hands[i].ties(self.player_hands[best_idx]):
                        tied_players.append(i)
            
            if len(tied_players) > 1:
                # Tie - split pot
                winner_idx = -1
                winner_id = -1
            else:
                winner_idx = best_idx
                winner_fish = self.fish_list[winner_idx]
                winner_id = winner_fish.fish_id
        
        # Apply energy changes based on game results
        total_pot = game_state.pot
        house_cut = 0.0
        winner_actual_gain = 0.0
        loser_ids = []
        players_folded = [game_state.players[i].folded for i in range(self.num_players)]
        
        # Deduct bets from each player
        for i, fish in enumerate(self.fish_list):
            player_total_bet = game_state.players[i].total_bet
            fish.energy = max(0, fish.energy - player_total_bet)
        
        if winner_id != -1:
            winner_fish = self.fish_list[winner_idx]
            winner_total_bet = game_state.players[winner_idx].total_bet
            
            # Calculate house cut based on winner's size
            net_gain = total_pot - winner_total_bet
            house_cut = self.calculate_house_cut(winner_fish.size, net_gain)
            
            # Winner receives pot minus house cut
            winner_fish.modify_energy(total_pot - house_cut)
            winner_actual_gain = net_gain - house_cut
            
            # Collect loser IDs
            loser_ids = [
                self.fish_list[i].fish_id 
                for i in range(self.num_players) 
                if i != winner_idx
            ]
        else:
            # Tie - split pot among tied players (no house cut on ties)
            split_amount = total_pot / len(tied_players)
            for player_idx in tied_players:
                self.fish_list[player_idx].modify_energy(split_amount)
        
        # Set cooldowns for all players
        for participant in self.participants:
            participant.start_cooldown(self.POKER_COOLDOWN)
        
        # Visual effects using helper method
        if winner_id != -1:
            loser_fish_list = [self.fish_list[i] for i in range(self.num_players) if i != winner_idx]
            self._set_visual_effects(
                winner_fish=self.fish_list[winner_idx],
                loser_fish_list=loser_fish_list,
                winner_gain=winner_actual_gain,
                is_tie=False,
            )
        else:
            # Tie - show tie effects for all
            self._set_visual_effects(
                winner_fish=self.fish_list[0],
                loser_fish_list=self.fish_list[1:],
                winner_gain=0.0,
                is_tie=True,
            )
        
        # Update poker strategy learning for all players (like 2-player version)
        if winner_id != -1 and not won_by_fold:
            from core.constants import POKER_MAX_HAND_RANK, POKER_WEAK_HAND_THRESHOLD
            from core.behavioral_learning import LearningEvent, LearningType
            
            winner_hand_strength = (
                self.player_hands[winner_idx].rank_value / POKER_MAX_HAND_RANK
                if self.player_hands[winner_idx] else 0.5
            )
            
            for i, fish in enumerate(self.fish_list):
                participant = self.participants[i]
                is_winner = (i == winner_idx)
                on_button = (i == button_position)
                
                hand_strength = (
                    self.player_hands[i].rank_value / POKER_MAX_HAND_RANK
                    if self.player_hands[i] else 0.5
                )
                
                # Check if player bluffed (won with weak hand)
                bluffed = is_winner and won_by_fold and hand_strength < POKER_WEAK_HAND_THRESHOLD
                
                # Strategy learning
                participant.strategy.learn_from_poker_outcome(
                    won=is_winner,
                    hand_strength=hand_strength,
                    position_on_button=on_button,
                    bluffed=bluffed,
                    opponent_id=winner_fish.fish_id if not is_winner else self.fish_list[0].fish_id,
                )
                
                # Behavioral learning
                energy_change = winner_actual_gain if is_winner else -game_state.players[i].total_bet
                poker_event = LearningEvent(
                    learning_type=LearningType.POKER_STRATEGY,
                    success=is_winner,
                    reward=energy_change / 10.0,
                    context={
                        "hand_strength": hand_strength,
                        "position": 0 if on_button else 1,
                        "bluffed": 1.0 if bluffed else 0.0,
                    },
                )
                fish.learning_system.learn_from_event(poker_event)
        
        # Try post-poker reproduction
        offspring = None
        reproduction_occurred = False
        if winner_id != -1:
            # Find the highest-placing loser for reproduction
            non_winners = [i for i in range(self.num_players) if i != winner_idx and not game_state.players[i].folded]
            
            if non_winners:
                # Find best hand among non-winners
                second_place_idx = non_winners[0]
                for i in non_winners[1:]:
                    if self.player_hands[i] and self.player_hands[second_place_idx]:
                        if self.player_hands[i].beats(self.player_hands[second_place_idx]):
                            second_place_idx = i
                
                offspring = self.try_post_poker_reproduction(
                    winner_fish=self.fish_list[winner_idx],
                    loser_fish=self.fish_list[second_place_idx],
                    energy_transferred=winner_actual_gain,
                )
                reproduction_occurred = offspring is not None
        
        # Count rounds played
        total_rounds = game_state.current_round if game_state.current_round < 4 else 4
        reached_showdown = not won_by_fold
        
        # Create result
        self.result = PokerResult(
            player_hands=self.player_hands,
            player_ids=[f.fish_id for f in self.fish_list],
            energy_transferred=sum(game_state.players[i].total_bet for i in range(self.num_players) if i != winner_idx) if winner_id != -1 else 0.0,
            winner_actual_gain=winner_actual_gain,
            winner_id=winner_id,
            loser_ids=loser_ids,
            won_by_fold=won_by_fold,
            total_rounds=total_rounds,
            final_pot=total_pot,
            button_position=button_position,
            players_folded=players_folded,
            reached_showdown=reached_showdown,
            betting_history=[(p, a.value if hasattr(a, 'value') else a, amt) for p, a, amt in game_state.betting_history],
            reproduction_occurred=reproduction_occurred,
            offspring=offspring,
        )
        
        # Record stats for each player
        for i, fish in enumerate(self.fish_list):
            participant = self.participants[i]
            on_button = (i == button_position)
            player_bet = game_state.players[i].total_bet
            
            if fish.fish_id == winner_id:
                participant.stats.record_win(
                    energy_won=winner_actual_gain,
                    house_cut=house_cut,
                    hand_rank=self.player_hands[i].rank_value if self.player_hands[i] else 0,
                    won_at_showdown=reached_showdown,
                    on_button=on_button,
                )
            elif winner_id == -1:
                participant.stats.record_tie(
                    hand_rank=self.player_hands[i].rank_value if self.player_hands[i] else 0,
                    on_button=on_button,
                )
            else:
                participant.stats.record_loss(
                    energy_lost=player_bet,
                    hand_rank=self.player_hands[i].rank_value if self.player_hands[i] else 0,
                    folded=game_state.players[i].folded,
                    reached_showdown=reached_showdown,
                    on_button=on_button,
                )
        
        # Record in ecosystem using helper method
        if winner_id != -1:
            loser_fish_list = [self.fish_list[i] for i in range(self.num_players) if i != winner_idx]
            loser_hands = [self.player_hands[i] for i in range(self.num_players) if i != winner_idx]
            energy_per_loser = winner_actual_gain / len(loser_fish_list) if loser_fish_list else 0
            self._record_ecosystem_stats(
                winner_id=winner_id,
                loser_ids=loser_ids,
                winner_fish=self.fish_list[winner_idx],
                loser_fish_list=loser_fish_list,
                winner_hand=self.player_hands[winner_idx],
                loser_hands=loser_hands,
                energy_per_loser=energy_per_loser,
                house_cut=house_cut,
            )
        
        return True

    def play_poker(self, bet_amount: Optional[float] = None) -> bool:
        """
        Play a poker game between all fish.

        Full Texas Hold'em with betting rounds, bluffing, position play,
        and strategy learning for all player counts (2+).

        Args:
            bet_amount: Amount to wager (uses calculated amount if None)

        Returns:
            True if game completed successfully, False otherwise
        """
        # Check if poker can be played
        if not self.can_play_poker():
            return False

        # Calculate bet amount if not provided
        if bet_amount is None:
            bet_amount = self.calculate_bet_amount()
        else:
            # Ensure bet doesn't exceed what fish can afford
            bet_amount = self.calculate_bet_amount(bet_amount)

        # For 3+ players, use multiplayer poker engine
        if self.num_players > 2:
            return self.play_poker_multiplayer(bet_amount)

        # For 2 players, use heads-up Texas Hold'em poker
        # Determine aggression levels for each fish based on their genome
        # Map genome aggression (0.0-1.0) to poker aggression range (0.3-0.9)
        participant1 = self.participants[0]
        participant2 = self.participants[1]

        fish1_aggression = AGGRESSION_LOW + (
            self.fish1.genome.aggression
            * (AGGRESSION_HIGH - AGGRESSION_LOW)
        )
        fish2_aggression = AGGRESSION_LOW + (
            self.fish2.genome.aggression
            * (AGGRESSION_HIGH - AGGRESSION_LOW)
        )

        # Rotate button position for positional play
        # Button alternates between 1 and 2
        button_position = 2 if participant1.last_button_position == 1 else 1
        participant1.last_button_position = button_position
        participant2.last_button_position = button_position

        # Get poker strategy algorithms from fish genomes (if available)
        player1_strategy = (
            self.fish1.genome.poker_strategy_algorithm
            if hasattr(self.fish1.genome, "poker_strategy_algorithm")
            else None
        )
        player2_strategy = (
            self.fish2.genome.poker_strategy_algorithm
            if hasattr(self.fish2.genome, "poker_strategy_algorithm")
            else None
        )

        # Simulate multi-round Texas Hold'em game with blinds and position
        # Use evolved poker strategies if available, otherwise fall back to aggression
        game_state = simulate_multi_round_game(
            initial_bet=bet_amount,
            player1_energy=self.fish1.energy,
            player2_energy=self.fish2.energy,
            player1_aggression=fish1_aggression,  # Fallback if no strategy
            player2_aggression=fish2_aggression,  # Fallback if no strategy
            button_position=button_position,
            player1_strategy=player1_strategy,  # Evolving poker strategy
            player2_strategy=player2_strategy,  # Evolving poker strategy
        )

        # Play the poker game


        # Store hands
        self.hand1 = game_state.player1_hand
        self.hand2 = game_state.player2_hand

        # Determine winner
        winner_by_fold = game_state.get_winner_by_fold()
        won_by_fold = winner_by_fold is not None

        if won_by_fold:
            # Someone folded
            winner_id = self.fish1.fish_id if winner_by_fold == 1 else self.fish2.fish_id
            loser_id = self.fish2.fish_id if winner_by_fold == 1 else self.fish1.fish_id
        else:
            # Compare hands at showdown
            if self.hand1.beats(self.hand2):
                winner_id = self.fish1.fish_id
                loser_id = self.fish2.fish_id
            elif self.hand2.beats(self.hand1):
                winner_id = self.fish2.fish_id
                loser_id = self.fish1.fish_id
            else:
                # Tie - return bets to players
                winner_id = -1
                loser_id = -1

        # Calculate energy transfer based on pot
        house_cut = 0.0
        if winner_id != -1:
            # Determine winner and loser fish
            winner_fish = self.fish1 if winner_id == self.fish1.fish_id else self.fish2
            loser_fish = self.fish2 if winner_id == self.fish1.fish_id else self.fish1

            # Get total bets for each player
            winner_total_bet = (
                game_state.player1_total_bet
                if winner_id == self.fish1.fish_id
                else game_state.player2_total_bet
            )
            loser_total_bet = (
                game_state.player1_total_bet
                if loser_id == self.fish1.fish_id
                else game_state.player2_total_bet
            )

            # Both players pay their bets
            winner_fish.energy = max(0, winner_fish.energy - winner_total_bet)
            loser_fish.energy = max(0, loser_fish.energy - loser_total_bet)

            # Calculate actual pot from the bets (more reliable than game_state.pot)
            total_pot = winner_total_bet + loser_total_bet

            # House cut using helper method
            net_gain = total_pot - winner_total_bet  # Winner's profit (loser's bet)
            house_cut = self.calculate_house_cut(winner_fish.size, net_gain)

            # Winner receives the pot minus house cut
            winner_fish.modify_energy(total_pot - house_cut)

            # For reporting purposes, energy_transferred is the loser's loss (what they bet)
            # This is used for display and statistics tracking
            energy_transferred = loser_total_bet
            # Also calculate the winner's actual gain (less than loser's loss due to house cut)
            winner_actual_gain = net_gain - house_cut
        else:
            # Tie - no energy transfer
            energy_transferred = 0.0
            winner_actual_gain = 0.0

        # Set visual effects using helper method
        if winner_id != -1:
            winner_fish = self.fish1 if winner_id == self.fish1.fish_id else self.fish2
            loser_fish = self.fish2 if winner_id == self.fish1.fish_id else self.fish1
            self._set_visual_effects(
                winner_fish=winner_fish,
                loser_fish_list=[loser_fish],
                winner_gain=winner_actual_gain,
                is_tie=False,
            )
        else:
            self._set_visual_effects(
                winner_fish=self.fish1,
                loser_fish_list=[self.fish2],
                winner_gain=0.0,
                is_tie=True,
            )

        # Set cooldowns
        # NEW: Update poker strategy learning for both fish
        if winner_id != -1:  # Not a tie
            winner_fish = self.fish1 if winner_id == self.fish1.fish_id else self.fish2
            loser_fish = self.fish2 if winner_id == self.fish1.fish_id else self.fish1

            # Ensure hands are valid before learning (hands can be None if fold happened very early)
            if self.hand1 is None or self.hand2 is None:
                # Skip learning if hands are not available
                pass
            else:
                # Determine positions and hand strengths
                winner_on_button = (winner_id == self.fish1.fish_id and button_position == 1) or (
                    winner_id == self.fish2.fish_id and button_position == 2
                )
                loser_on_button = not winner_on_button

                # Get hand rankings (normalized 0-1)
                from core.constants import POKER_MAX_HAND_RANK, POKER_WEAK_HAND_THRESHOLD

                winner_hand_strength = (
                    self.hand1.rank_value
                    if winner_id == self.fish1.fish_id
                    else self.hand2.rank_value
                ) / POKER_MAX_HAND_RANK
                loser_hand_strength = (
                    self.hand2.rank_value
                    if winner_id == self.fish1.fish_id
                    else self.hand1.rank_value
                ) / POKER_MAX_HAND_RANK

                # Check if fish bluffed (won with weak hand or lost with weak hand)
                winner_bluffed = won_by_fold and winner_hand_strength < POKER_WEAK_HAND_THRESHOLD
                loser_bluffed = False  # Loser didn't bluff if they lost

                winner_participant = participant1 if winner_id == self.fish1.fish_id else participant2
                loser_participant = participant2 if winner_participant is participant1 else participant1

                # Winner learns from victory
                winner_participant.strategy.learn_from_poker_outcome(
                    won=True,
                    hand_strength=winner_hand_strength,
                    position_on_button=winner_on_button,
                    bluffed=winner_bluffed,
                    opponent_id=loser_fish.fish_id,
                )

                # Loser learns from defeat
                loser_participant.strategy.learn_from_poker_outcome(
                    won=False,
                    hand_strength=loser_hand_strength,
                    position_on_button=loser_on_button,
                    bluffed=loser_bluffed,
                    opponent_id=winner_fish.fish_id,
                )

                # Update opponent models for both fish
                winner_participant.strategy.update_opponent_model(
                    opponent_id=loser_fish.fish_id,
                    won=False,  # From winner's perspective, opponent lost
                    folded=(
                        game_state.player2_folded
                        if winner_id == self.fish1.fish_id
                        else game_state.player1_folded
                    ),
                    raised=False,  # Simplified - would need betting history
                    called=True,  # Simplified
                    aggression=(
                        fish2_aggression if winner_id == self.fish1.fish_id else fish1_aggression
                    ),
                    frame=winner_fish.ecosystem.frame_count if winner_fish.ecosystem else 0,
                )

                loser_participant.strategy.update_opponent_model(
                    opponent_id=winner_fish.fish_id,
                    won=True,  # From loser's perspective, opponent won
                    folded=False,
                    raised=False,
                    called=True,
                    aggression=(
                        fish1_aggression if winner_id == self.fish1.fish_id else fish2_aggression
                    ),
                    frame=loser_fish.ecosystem.frame_count if loser_fish.ecosystem else 0,
                )

                # NEW: Trigger learning events for behavioral learning system
                from core.behavioral_learning import LearningEvent, LearningType

                # Winner's learning event
                winner_poker_event = LearningEvent(
                    learning_type=LearningType.POKER_STRATEGY,
                    success=True,
                    reward=energy_transferred / 10.0,  # Normalize reward
                    context={
                        "hand_strength": winner_hand_strength,
                        "position": 0 if winner_on_button else 1,
                        "bluffed": 1.0 if winner_bluffed else 0.0,
                    },
                )
                winner_fish.learning_system.learn_from_event(winner_poker_event)

                # Loser's learning event
                loser_poker_event = LearningEvent(
                    learning_type=LearningType.POKER_STRATEGY,
                    success=False,
                    reward=-energy_transferred / 10.0,  # Negative reward for loss
                    context={
                        "hand_strength": loser_hand_strength,
                        "position": 0 if loser_on_button else 1,
                        "bluffed": 0.0,
                    },
                )
                loser_fish.learning_system.learn_from_event(loser_poker_event)

        # Try post-poker reproduction (voluntary sexual reproduction)
        offspring = None
        reproduction_occurred = False
        if winner_id != -1:  # Only if there was a winner (not a tie)
            winner_fish = self.fish1 if winner_id == self.fish1.fish_id else self.fish2
            loser_fish = self.fish2 if winner_id == self.fish1.fish_id else self.fish1

            offspring = self.try_post_poker_reproduction(
                winner_fish=winner_fish,
                loser_fish=loser_fish,
                energy_transferred=energy_transferred,
            )
            reproduction_occurred = offspring is not None

        # Count rounds played
        total_rounds = int(game_state.current_round) if game_state.current_round < 4 else 4

        # Determine if game reached showdown
        reached_showdown = not won_by_fold

        # Create result (using new format with backwards compatibility)
        # Use calculated total_pot if winner exists, otherwise use game_state.pot
        final_pot_value = (
            winner_total_bet + loser_total_bet
            if winner_id != -1
            else game_state.pot
        )
        self.result = PokerResult(
            player_hands=[self.hand1, self.hand2],
            player_ids=[self.fish1.fish_id, self.fish2.fish_id],
            energy_transferred=abs(energy_transferred),
            winner_actual_gain=abs(winner_actual_gain) if winner_id != -1 else 0.0,
            winner_id=winner_id,
            loser_ids=[loser_id] if loser_id != -1 else [],
            won_by_fold=won_by_fold,
            total_rounds=total_rounds,
            final_pot=final_pot_value,
            button_position=button_position,
            players_folded=[game_state.player1_folded, game_state.player2_folded],
            reached_showdown=reached_showdown,
            betting_history=game_state.betting_history,
            reproduction_occurred=reproduction_occurred,
            offspring=offspring,
        )

        # Update player_hands list for consistency
        self.player_hands = [self.hand1, self.hand2]

        # Record individual fish poker statistics
        if winner_id == -1:
            # Tie - both fish record tie
            fish1_on_button = button_position == 1
            fish2_on_button = button_position == 2
            if self.hand1 is not None:
                participant1.stats.record_tie(
                    hand_rank=self.hand1.rank_value, on_button=fish1_on_button
                )
            if self.hand2 is not None:
                participant2.stats.record_tie(
                    hand_rank=self.hand2.rank_value, on_button=fish2_on_button
                )
        else:
            # Someone won
            winner_fish = self.fish1 if winner_id == self.fish1.fish_id else self.fish2
            loser_fish = self.fish2 if winner_id == self.fish1.fish_id else self.fish1
            winner_hand = self.hand1 if winner_id == self.fish1.fish_id else self.hand2
            loser_hand = self.hand2 if winner_id == self.fish1.fish_id else self.hand1
            winner_participant = participant1 if winner_id == self.fish1.fish_id else participant2
            loser_participant = participant2 if winner_participant is participant1 else participant1

            # Determine button positions
            winner_on_button = (
                button_position == 1 if winner_id == self.fish1.fish_id else button_position == 2
            )
            loser_on_button = not winner_on_button

            # Record winner stats
            # Even if hand is None, record the win
            winner_hand_rank = winner_hand.rank_value if winner_hand is not None else 0
            winner_participant.stats.record_win(
                energy_won=winner_actual_gain,
                house_cut=house_cut,
                hand_rank=winner_hand_rank,
                won_at_showdown=reached_showdown,
                on_button=winner_on_button,
            )

            # Record loser stats
            # Even if hand is None, record the loss
            loser_hand_rank = loser_hand.rank_value if loser_hand is not None else 0
            loser_participant.stats.record_loss(
                energy_lost=energy_transferred,
                hand_rank=loser_hand_rank,
                folded=(
                    game_state.player1_folded
                    if loser_id == self.fish1.fish_id
                    else game_state.player2_folded
                ),
                reached_showdown=reached_showdown,
                on_button=loser_on_button,
            )

        # Record in ecosystem using helper method
        if winner_id != -1:
            winner_fish = self.fish1 if winner_id == self.fish1.fish_id else self.fish2
            loser_fish = self.fish2 if winner_id == self.fish1.fish_id else self.fish1
            winner_hand = self.hand1 if winner_id == self.fish1.fish_id else self.hand2
            loser_hand = self.hand2 if winner_id == self.fish1.fish_id else self.hand1
            self._record_ecosystem_stats(
                winner_id=winner_id,
                loser_ids=[loser_id],
                winner_fish=winner_fish,
                loser_fish_list=[loser_fish],
                winner_hand=winner_hand,
                loser_hands=[loser_hand],
                energy_per_loser=energy_transferred,
                house_cut=house_cut,
            )

        return True

    def get_result_description(self) -> str:
        """
        Get a human-readable description of the poker game result.

        Returns:
            String describing the game outcome
        """
        if self.result is None:
            return "No poker game has been played"

        round_names = ["Pre-flop", "Flop", "Turn", "River", "Showdown"]
        rounds_text = (
            f"after {round_names[self.result.total_rounds]}"
            if self.result.total_rounds < 4
            else "at Showdown"
        )

        if self.result.winner_id == -1:
            return (
                f"Tie {rounds_text}! Fish {self.fish1.fish_id} had {self.result.hand1.description}, "
                f"Fish {self.fish2.fish_id} had {self.result.hand2.description}"
            )

        winner_fish = self.fish1 if self.result.winner_id == self.fish1.fish_id else self.fish2
        loser_fish = self.fish2 if self.result.winner_id == self.fish1.fish_id else self.fish1
        winner_hand = (
            self.result.hand1 if self.result.winner_id == self.fish1.fish_id else self.result.hand2
        )
        loser_hand = (
            self.result.hand2 if self.result.winner_id == self.fish1.fish_id else self.result.hand1
        )

        if self.result.won_by_fold:
            return (
                f"Fish {winner_fish.fish_id} wins {self.result.energy_transferred:.1f} energy {rounds_text}! "
                f"Fish {loser_fish.fish_id} folded ({loser_hand.description})"
            )
        else:
            return (
                f"Fish {winner_fish.fish_id} wins {self.result.energy_transferred:.1f} energy {rounds_text}! "
                f"({winner_hand.description} beats {loser_hand.description})"
            )


# Helper function for easy integration
def try_poker_interaction(fish1: "Fish", fish2: "Fish", bet_amount: Optional[float] = None) -> bool:
    """
    Convenience function to attempt a poker interaction between two fish.

    Args:
        fish1: First fish
        fish2: Second fish
        bet_amount: Optional bet amount (uses default if None)

    Returns:
        True if poker game was played, False otherwise
    """
    poker = PokerInteraction(fish1, fish2)
    return poker.play_poker(bet_amount)
