"""
Fish poker interaction system.

This module handles poker games between two fish when they collide.
The outcome determines energy transfer between the fish.

Features:
- Multi-round betting and folding
- Genome-based poker aggression: Each fish's poker playing style is determined
  by their genome's aggression trait, which evolves over generations
- Evolutionary pressure: Fish with optimal poker aggression levels win more energy,
  survive longer, and reproduce more, spreading their poker genes
"""

from typing import Optional, TYPE_CHECKING, List, Tuple
from dataclasses import dataclass
from core.poker_interaction import PokerEngine, PokerHand, PokerGameState, BettingAction
import random

if TYPE_CHECKING:
    from core.entities import Fish


@dataclass
class PokerResult:
    """Result of a poker game between two fish."""
    hand1: PokerHand
    hand2: PokerHand
    energy_transferred: float
    winner_id: int
    loser_id: int
    won_by_fold: bool  # True if winner won because opponent folded
    total_rounds: int  # Number of betting rounds completed
    final_pot: float  # Final pot size
    button_position: int  # Which player had the button (1 or 2)
    player1_folded: bool  # Did player 1 fold
    player2_folded: bool  # Did player 2 fold
    reached_showdown: bool  # Did game reach showdown
    betting_history: List[Tuple[int, 'BettingAction', float]]  # Betting actions taken
    reproduction_occurred: bool = False  # True if fish reproduced after poker
    offspring: Optional['Fish'] = None  # The baby fish created (if reproduction occurred)


class PokerInteraction:
    """Handles poker encounters between two fish."""

    # Minimum energy required to play poker
    MIN_ENERGY_TO_PLAY = 10.0

    # Default bet amount (can be overridden)
    DEFAULT_BET_AMOUNT = 5.0

    # House cut percentage (taken from total pot)
    HOUSE_CUT_PERCENTAGE = 0.05  # 5% house cut

    # Cooldown between poker games for the same fish (in frames)
    POKER_COOLDOWN = 60  # 2 seconds at 30fps

    def __init__(self, fish1: 'Fish', fish2: 'Fish'):
        """
        Initialize a poker interaction between two fish.

        Args:
            fish1: First fish
            fish2: Second fish
        """
        self.fish1 = fish1
        self.fish2 = fish2
        self.hand1: Optional[PokerHand] = None
        self.hand2: Optional[PokerHand] = None
        self.result: Optional[PokerResult] = None

        # Add poker cooldown tracking to fish if not present
        if not hasattr(fish1, 'poker_cooldown'):
            fish1.poker_cooldown = 0
        if not hasattr(fish2, 'poker_cooldown'):
            fish2.poker_cooldown = 0

        # Add button position tracking for positional play
        # Button rotates between players in consecutive games
        if not hasattr(fish1, 'last_button_position'):
            fish1.last_button_position = 2  # Start with button position 2
        if not hasattr(fish2, 'last_button_position'):
            fish2.last_button_position = 2

    def can_play_poker(self) -> bool:
        """
        Check if both fish are willing and able to play poker.

        Returns:
            True if poker game can proceed
        """
        # Both fish must exist
        if self.fish1 is None or self.fish2 is None:
            return False

        # Can't play poker with yourself
        if self.fish1.fish_id == self.fish2.fish_id:
            return False

        # Both must have minimum energy
        if self.fish1.energy < self.MIN_ENERGY_TO_PLAY:
            return False
        if self.fish2.energy < self.MIN_ENERGY_TO_PLAY:
            return False

        # Both must be off cooldown
        if self.fish1.poker_cooldown > 0:
            return False
        if self.fish2.poker_cooldown > 0:
            return False

        # Don't interrupt pregnant fish
        if hasattr(self.fish1, 'is_pregnant') and self.fish1.is_pregnant:
            return False
        if hasattr(self.fish2, 'is_pregnant') and self.fish2.is_pregnant:
            return False

        return True

    def calculate_bet_amount(self, base_bet: float = DEFAULT_BET_AMOUNT) -> float:
        """
        Calculate the bet amount based on fish energies.

        The bet is capped at the minimum of:
        - base_bet amount
        - 20% of either fish's current energy

        Args:
            base_bet: Base bet amount

        Returns:
            Actual bet amount to use
        """
        max_bet_fish1 = self.fish1.energy * 0.2
        max_bet_fish2 = self.fish2.energy * 0.2
        return min(base_bet, max_bet_fish1, max_bet_fish2)

    def try_post_poker_reproduction(self, winner_fish: 'Fish', loser_fish: 'Fish',
                                   energy_transferred: float) -> Optional['Fish']:
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
        from core.constants import (
            POST_POKER_CROSSOVER_WINNER_WEIGHT,
            POST_POKER_MATING_DISTANCE,
        )
        from core.genetics import Genome

        # Check distance (fish must still be close enough)
        distance = (winner_fish.pos - loser_fish.pos).length()
        if distance > POST_POKER_MATING_DISTANCE:
            return None

        # Check if winner wants to reproduce
        winner_wants = winner_fish.should_offer_post_poker_reproduction(
            loser_fish, is_winner=True, energy_gained=energy_transferred
        )

        # Check if loser wants to reproduce
        loser_wants = loser_fish.should_offer_post_poker_reproduction(
            winner_fish, is_winner=False, energy_gained=-energy_transferred
        )

        # Both must agree to reproduce
        if not (winner_wants and loser_wants):
            return None

        # Calculate population stress for adaptive mutations
        population_stress = 0.0
        if winner_fish.ecosystem is not None:
            from core.entities import Fish
            fish_count = len([e for e in winner_fish.environment.agents if isinstance(e, Fish)])
            target_population = 15
            population_ratio = fish_count / target_population if target_population > 0 else 1.0

            if population_ratio < 1.0:
                population_stress = (1.0 - population_ratio) * 0.8

            if hasattr(winner_fish.ecosystem, 'recent_death_rate'):
                death_rate_stress = min(0.4, winner_fish.ecosystem.recent_death_rate)
                population_stress = min(1.0, population_stress + death_rate_stress)

        # Create offspring genome using WEIGHTED crossover (winner contributes more DNA)
        offspring_genome = Genome.from_parents_weighted(
            parent1=winner_fish.genome,
            parent2=loser_fish.genome,
            parent1_weight=POST_POKER_CROSSOVER_WINNER_WEIGHT,  # Winner contributes 60%
            mutation_rate=0.1,
            mutation_strength=0.1,
            population_stress=population_stress
        )

        # Energy transfer for baby (both parents contribute)
        winner_energy_contribution = 0.15  # Winner gives 15% of energy
        loser_energy_contribution = 0.15   # Loser gives 15% of energy

        winner_energy_transfer = winner_fish.energy * winner_energy_contribution
        loser_energy_transfer = loser_fish.energy * loser_energy_contribution
        total_baby_energy = winner_energy_transfer + loser_energy_transfer

        # Parents pay the energy cost
        winner_fish.energy -= winner_energy_transfer
        loser_fish.energy -= loser_energy_transfer

        # Set reproduction cooldown for both parents
        winner_fish.reproduction_cooldown = winner_fish.REPRODUCTION_COOLDOWN
        loser_fish.reproduction_cooldown = loser_fish.REPRODUCTION_COOLDOWN

        # Both parents become pregnant (simulate gestation)
        # In this case we'll just create the baby immediately
        # (Could make one parent pregnant for realism, but immediate birth is simpler)

        # Create baby position (between parents)
        baby_x = (winner_fish.pos.x + loser_fish.pos.x) / 2.0
        baby_y = (winner_fish.pos.y + loser_fish.pos.y) / 2.0

        # Add some randomness
        baby_x += random.uniform(-20, 20)
        baby_y += random.uniform(-20, 20)

        # Clamp to screen
        baby_x = max(0, min(winner_fish.screen_width - 50, baby_x))
        baby_y = max(0, min(winner_fish.screen_height - 50, baby_y))

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
            initial_energy=total_baby_energy
        )

        # Record reproduction in ecosystem for both parents
        if winner_fish.ecosystem is not None:
            from core.behavior_algorithms import get_algorithm_index

            if winner_fish.genome.behavior_algorithm is not None:
                winner_algo_id = get_algorithm_index(winner_fish.genome.behavior_algorithm)
                if winner_algo_id >= 0:
                    winner_fish.ecosystem.record_reproduction(winner_algo_id)

            if loser_fish.genome.behavior_algorithm is not None:
                loser_algo_id = get_algorithm_index(loser_fish.genome.behavior_algorithm)
                if loser_algo_id >= 0:
                    loser_fish.ecosystem.record_reproduction(loser_algo_id)

        return baby

    def play_poker(self, bet_amount: Optional[float] = None) -> bool:
        """
        Play a multi-round poker game between the two fish with folding.

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

        # Determine aggression levels for each fish based on their genome
        # Map genome aggression (0.0-1.0) to poker aggression range (0.3-0.9)
        fish1_aggression = PokerEngine.AGGRESSION_LOW + (
            self.fish1.genome.aggression * (PokerEngine.AGGRESSION_HIGH - PokerEngine.AGGRESSION_LOW)
        )
        fish2_aggression = PokerEngine.AGGRESSION_LOW + (
            self.fish2.genome.aggression * (PokerEngine.AGGRESSION_HIGH - PokerEngine.AGGRESSION_LOW)
        )

        # Rotate button position for positional play
        # Button alternates between 1 and 2
        button_position = 2 if self.fish1.last_button_position == 1 else 1
        self.fish1.last_button_position = button_position
        self.fish2.last_button_position = button_position

        # Simulate multi-round Texas Hold'em game with blinds and position
        game_state = PokerEngine.simulate_multi_round_game(
            initial_bet=bet_amount,
            player1_energy=self.fish1.energy,
            player2_energy=self.fish2.energy,
            player1_aggression=fish1_aggression,
            player2_aggression=fish2_aggression,
            button_position=button_position
        )

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

        # Calculate energy transfer
        house_cut = 0.0
        if winner_id != -1:
            # Winner takes pot minus house cut
            house_cut = game_state.pot * self.HOUSE_CUT_PERCENTAGE
            energy_transferred = game_state.pot - house_cut

            # Apply energy changes
            if winner_id == self.fish1.fish_id:
                # Fish 1 wins
                self.fish1.energy = max(0, self.fish1.energy - game_state.player1_total_bet + energy_transferred)
                self.fish2.energy = max(0, self.fish2.energy - game_state.player2_total_bet)
            else:
                # Fish 2 wins
                self.fish1.energy = max(0, self.fish1.energy - game_state.player1_total_bet)
                self.fish2.energy = max(0, self.fish2.energy - game_state.player2_total_bet + energy_transferred)
        else:
            # Tie - return bets
            energy_transferred = 0.0
            self.fish1.energy = max(0, self.fish1.energy - game_state.player1_total_bet + game_state.player1_total_bet)
            self.fish2.energy = max(0, self.fish2.energy - game_state.player2_total_bet + game_state.player2_total_bet)

        # Set cooldowns
        self.fish1.poker_cooldown = self.POKER_COOLDOWN
        self.fish2.poker_cooldown = self.POKER_COOLDOWN

        # Count rounds played
        total_rounds = int(game_state.current_round) if game_state.current_round < 4 else 4

        # Determine if game reached showdown
        reached_showdown = not won_by_fold

        # Try post-poker reproduction (voluntary sexual reproduction)
        offspring = None
        reproduction_occurred = False
        if winner_id != -1:  # Only if there was a winner (not a tie)
            winner_fish = self.fish1 if winner_id == self.fish1.fish_id else self.fish2
            loser_fish = self.fish2 if winner_id == self.fish1.fish_id else self.fish1

            offspring = self.try_post_poker_reproduction(
                winner_fish=winner_fish,
                loser_fish=loser_fish,
                energy_transferred=energy_transferred
            )
            reproduction_occurred = offspring is not None

        # Create result
        self.result = PokerResult(
            hand1=self.hand1,
            hand2=self.hand2,
            energy_transferred=abs(energy_transferred),
            winner_id=winner_id,
            loser_id=loser_id,
            won_by_fold=won_by_fold,
            total_rounds=total_rounds,
            final_pot=game_state.pot,
            button_position=button_position,
            player1_folded=game_state.player1_folded,
            player2_folded=game_state.player2_folded,
            reached_showdown=reached_showdown,
            betting_history=game_state.betting_history,
            reproduction_occurred=reproduction_occurred,
            offspring=offspring
        )

        # Record in ecosystem if available (including ties)
        if self.fish1.ecosystem is not None:
            # Get algorithm IDs from fish genomes
            fish1_algo_id = None
            if self.fish1.genome.behavior_algorithm is not None:
                from core.behavior_algorithms import get_algorithm_index
                fish1_algo_id = get_algorithm_index(self.fish1.genome.behavior_algorithm)

            fish2_algo_id = None
            if self.fish2.genome.behavior_algorithm is not None:
                from core.behavior_algorithms import get_algorithm_index
                fish2_algo_id = get_algorithm_index(self.fish2.genome.behavior_algorithm)

            # Determine which fish is player 1 and player 2 for stats
            player1_algo_id = fish1_algo_id
            player2_algo_id = fish2_algo_id

            self.fish1.ecosystem.record_poker_outcome(
                winner_id=winner_id,
                loser_id=loser_id,
                winner_algo_id=fish1_algo_id if winner_id == self.fish1.fish_id else fish2_algo_id,
                loser_algo_id=fish2_algo_id if winner_id == self.fish1.fish_id else fish1_algo_id,
                amount=energy_transferred,
                winner_hand=self.hand1 if winner_id == self.fish1.fish_id else self.hand2,
                loser_hand=self.hand2 if winner_id == self.fish1.fish_id else self.hand1,
                house_cut=house_cut,
                result=self.result,
                player1_algo_id=player1_algo_id,
                player2_algo_id=player2_algo_id
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
        rounds_text = f"after {round_names[self.result.total_rounds]}" if self.result.total_rounds < 4 else "at Showdown"

        if self.result.winner_id == -1:
            return (f"Tie {rounds_text}! Fish {self.fish1.fish_id} had {self.result.hand1.description}, "
                   f"Fish {self.fish2.fish_id} had {self.result.hand2.description}")

        winner_fish = self.fish1 if self.result.winner_id == self.fish1.fish_id else self.fish2
        loser_fish = self.fish2 if self.result.winner_id == self.fish1.fish_id else self.fish1
        winner_hand = self.result.hand1 if self.result.winner_id == self.fish1.fish_id else self.result.hand2
        loser_hand = self.result.hand2 if self.result.winner_id == self.fish1.fish_id else self.result.hand1

        if self.result.won_by_fold:
            return (f"Fish {winner_fish.fish_id} wins {self.result.energy_transferred:.1f} energy {rounds_text}! "
                   f"Fish {loser_fish.fish_id} folded ({loser_hand.description})")
        else:
            return (f"Fish {winner_fish.fish_id} wins {self.result.energy_transferred:.1f} energy {rounds_text}! "
                   f"({winner_hand.description} beats {loser_hand.description})")


# Helper function for easy integration
def try_poker_interaction(fish1: 'Fish', fish2: 'Fish', bet_amount: Optional[float] = None) -> bool:
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
