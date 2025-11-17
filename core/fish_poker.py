"""
Fish poker interaction system.

This module handles poker games between two fish when they collide.
The outcome determines energy transfer between the fish.

Updated to support multi-round betting and folding.
"""

from typing import Optional, TYPE_CHECKING
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

        # Determine aggression levels for each fish based on their behavior
        # Use random aggression for now, could be tied to fish genome later
        fish1_aggression = random.uniform(PokerEngine.AGGRESSION_LOW, PokerEngine.AGGRESSION_HIGH)
        fish2_aggression = random.uniform(PokerEngine.AGGRESSION_LOW, PokerEngine.AGGRESSION_HIGH)

        # Simulate multi-round game
        game_state = PokerEngine.simulate_multi_round_game(
            initial_bet=bet_amount,
            player1_energy=self.fish1.energy,
            player2_energy=self.fish2.energy,
            player1_aggression=fish1_aggression,
            player2_aggression=fish2_aggression
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

        # Create result
        self.result = PokerResult(
            hand1=self.hand1,
            hand2=self.hand2,
            energy_transferred=abs(energy_transferred),
            winner_id=winner_id,
            loser_id=loser_id,
            won_by_fold=won_by_fold,
            total_rounds=total_rounds,
            final_pot=game_state.pot
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

            self.fish1.ecosystem.record_poker_outcome(
                winner_id=winner_id,
                loser_id=loser_id,
                winner_algo_id=fish1_algo_id if winner_id == self.fish1.fish_id else fish2_algo_id,
                loser_algo_id=fish2_algo_id if winner_id == self.fish1.fish_id else fish1_algo_id,
                amount=energy_transferred,
                winner_hand=self.hand1 if winner_id == self.fish1.fish_id else self.hand2,
                loser_hand=self.hand2 if winner_id == self.fish1.fish_id else self.hand1,
                house_cut=house_cut
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


if __name__ == "__main__":
    """Test poker interactions with mock fish objects."""
    print("Fish Poker Interaction Test")
    print("=" * 50)

    # Create mock fish for testing
    class MockFish:
        def __init__(self, fish_id, energy):
            self.fish_id = fish_id
            self.energy = energy
            self.is_pregnant = False
            self.poker_cooldown = 0
            self.ecosystem = None

    # Test 1: Normal poker game
    print("\nTest 1: Normal poker game")
    fish1 = MockFish(1, 50.0)
    fish2 = MockFish(2, 50.0)

    poker = PokerInteraction(fish1, fish2)
    if poker.play_poker():
        print(f"  Initial energies: Fish 1 = 50.0, Fish 2 = 50.0")
        print(f"  Final energies: Fish 1 = {fish1.energy:.1f}, Fish 2 = {fish2.energy:.1f}")
        print(f"  {poker.get_result_description()}")
    else:
        print("  Poker game could not be played")

    # Test 2: Insufficient energy
    print("\nTest 2: Insufficient energy")
    fish3 = MockFish(3, 5.0)  # Too low energy
    fish4 = MockFish(4, 50.0)

    poker2 = PokerInteraction(fish3, fish4)
    if poker2.play_poker():
        print("  Game played (unexpected!)")
    else:
        print("  Game prevented: Fish 3 has insufficient energy")

    # Test 3: Cooldown prevents immediate replay
    print("\nTest 3: Cooldown system")
    print(f"  Fish 1 cooldown: {fish1.poker_cooldown} frames")
    poker3 = PokerInteraction(fish1, fish2)
    if poker3.play_poker():
        print("  Game played (unexpected!)")
    else:
        print("  Game prevented: Fish are on cooldown")

    print("\n" + "=" * 50)
