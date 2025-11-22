"""
Fractal Plant-Fish poker interaction system.

This module handles poker games between fish and fractal plants.
Fish can "eat" plants by playing poker - if the fish wins, they take
energy from the plant. If the plant wins, it takes energy from the fish.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from core.poker.core import PokerEngine, PokerHand

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.fractal_plant import FractalPlant


@dataclass
class PlantPokerResult:
    """Result of a poker game between a fish and fractal plant."""

    fish_hand: PokerHand
    plant_hand: PokerHand
    energy_transferred: float
    fish_won: bool
    won_by_fold: bool
    total_rounds: int
    final_pot: float
    button_position: int
    fish_folded: bool
    plant_folded: bool
    reached_showdown: bool
    fish_id: int
    plant_id: int


class PlantPokerInteraction:
    """Handles poker encounters between fish and fractal plants.

    When a fish collides with a fractal plant, they can play poker.
    The winner takes energy from the loser. This allows fish to
    "eat" plants by winning poker games.
    """

    # Minimum energy required to play poker
    MIN_ENERGY_TO_PLAY = 10.0

    # Default bet amount
    DEFAULT_BET_AMOUNT = 8.0

    # House cut percentage (slightly lower than fish-fish poker)
    HOUSE_CUT_PERCENTAGE = 0.05

    # Cooldown between poker games (in frames)
    POKER_COOLDOWN = 90  # 3 seconds at 30fps

    def __init__(self, fish: "Fish", plant: "FractalPlant"):
        """Initialize a poker interaction between a fish and plant.

        Args:
            fish: The fish player
            plant: The fractal plant player
        """
        self.fish = fish
        self.plant = plant
        self.fish_hand: Optional[PokerHand] = None
        self.plant_hand: Optional[PokerHand] = None
        self.result: Optional[PlantPokerResult] = None

        # Add poker cooldown tracking to fish if not present
        if not hasattr(fish, "poker_cooldown"):
            fish.poker_cooldown = 0

        # Add button position tracking
        if not hasattr(fish, "last_button_position"):
            fish.last_button_position = 2

    def can_play_poker(self) -> bool:
        """Check if fish and plant can play poker.

        Returns:
            True if poker game can proceed
        """
        # Both must exist
        if self.fish is None or self.plant is None:
            return False

        # Plant must be alive
        if self.plant.is_dead():
            return False

        # Both must have minimum energy
        if self.fish.energy < self.MIN_ENERGY_TO_PLAY:
            return False
        if self.plant.energy < self.MIN_ENERGY_TO_PLAY:
            return False

        # Both must be off cooldown
        if self.fish.poker_cooldown > 0:
            return False
        if self.plant.poker_cooldown > 0:
            return False

        # Don't interrupt pregnant fish
        if hasattr(self.fish, "is_pregnant") and self.fish.is_pregnant:
            return False

        return True

    def calculate_bet_amount(self, base_bet: float = DEFAULT_BET_AMOUNT) -> float:
        """Calculate the bet amount based on fish and plant energies.

        Args:
            base_bet: Base bet amount

        Returns:
            Actual bet amount to use
        """
        # Fish can bet up to 25% of energy
        max_bet_fish = self.fish.energy * 0.25
        # Plants are more conservative - 15% of energy
        max_bet_plant = self.plant.energy * 0.15
        return min(base_bet, max_bet_fish, max_bet_plant)

    def play_poker(self, bet_amount: Optional[float] = None) -> bool:
        """Play a multi-round poker game between fish and plant.

        Args:
            bet_amount: Amount to wager (uses calculated amount if None)

        Returns:
            True if game completed successfully, False otherwise
        """
        if not self.can_play_poker():
            return False

        # Calculate bet amount
        if bet_amount is None:
            bet_amount = self.calculate_bet_amount()
        else:
            bet_amount = self.calculate_bet_amount(bet_amount)

        # Fish uses genome-based aggression
        fish_aggression = PokerEngine.AGGRESSION_LOW + (
            self.fish.genome.aggression
            * (PokerEngine.AGGRESSION_HIGH - PokerEngine.AGGRESSION_LOW)
        )

        # Plant uses its genome-based aggression
        plant_aggression = PokerEngine.AGGRESSION_LOW + (
            self.plant.get_poker_aggression()
            * (PokerEngine.AGGRESSION_HIGH - PokerEngine.AGGRESSION_LOW)
        )

        # Rotate button position
        button_position = 1 if self.fish.last_button_position == 2 else 2
        self.fish.last_button_position = button_position

        # Play the poker game
        game_state = PokerEngine.simulate_multi_round_game(
            initial_bet=bet_amount,
            player1_energy=self.fish.energy,
            player2_energy=self.plant.energy,
            player1_aggression=fish_aggression,
            player2_aggression=plant_aggression,
            button_position=button_position,
        )

        # Assign hands based on button position
        if button_position == 1:
            # Fish is player1
            self.fish_hand = game_state.player1_hand
            self.plant_hand = game_state.player2_hand
        else:
            # Plant is player1
            self.fish_hand = game_state.player2_hand
            self.plant_hand = game_state.player1_hand

        # Determine winner
        if game_state.player1_folded:
            fish_won = button_position != 1
            won_by_fold = True
        elif game_state.player2_folded:
            fish_won = button_position == 1
            won_by_fold = True
        else:
            # Showdown - compare hands
            won_by_fold = False
            if button_position == 1:
                fish_won = game_state.player1_hand.beats(
                    game_state.player2_hand
                ) or (
                    not game_state.player2_hand.beats(game_state.player1_hand)
                )
            else:
                fish_won = game_state.player2_hand.beats(
                    game_state.player1_hand
                ) or (
                    not game_state.player1_hand.beats(game_state.player2_hand)
                )

        # Calculate energy transfer
        total_pot = game_state.pot
        house_cut = total_pot * self.HOUSE_CUT_PERCENTAGE
        winnings = total_pot - house_cut

        # Transfer energy
        if fish_won:
            # Fish wins - takes energy from plant
            energy_transferred = winnings / 2
            self.fish.energy += energy_transferred
            self.plant.lose_energy(total_pot / 2)
            self.plant.poker_losses += 1
        else:
            # Plant wins - takes energy from fish
            energy_transferred = -(total_pot / 2)
            self.fish.energy += energy_transferred
            self.plant.gain_energy(winnings / 2)
            self.plant.poker_wins += 1
            self.plant.genome.update_fitness(poker_won=1)

        # Set poker cooldown for both
        self.fish.poker_cooldown = self.POKER_COOLDOWN
        self.plant.poker_cooldown = self.POKER_COOLDOWN

        # Store result
        self.result = PlantPokerResult(
            fish_hand=self.fish_hand,
            plant_hand=self.plant_hand,
            energy_transferred=energy_transferred if fish_won else -energy_transferred,
            fish_won=fish_won,
            won_by_fold=won_by_fold,
            total_rounds=game_state.current_round.value,
            final_pot=total_pot,
            button_position=button_position,
            fish_folded=(
                game_state.player1_folded
                if button_position == 1
                else game_state.player2_folded
            ),
            plant_folded=(
                game_state.player2_folded
                if button_position == 1
                else game_state.player1_folded
            ),
            reached_showdown=not won_by_fold,
            fish_id=self.fish.fish_id,
            plant_id=self.plant.plant_id,
        )

        # Record in ecosystem if available
        if self.fish.ecosystem is not None:
            # Get hand ranks (may be None if folded early)
            fish_hand_rank = (
                self.result.fish_hand.rank_value
                if self.result.fish_hand is not None
                else 0
            )
            plant_hand_rank = (
                self.result.plant_hand.rank_value
                if self.result.plant_hand is not None
                else 0
            )
            self.fish.ecosystem.record_plant_poker_game(
                fish_id=self.fish.fish_id,
                plant_id=self.plant.plant_id,
                fish_won=fish_won,
                energy_transferred=abs(energy_transferred),
                fish_hand_rank=fish_hand_rank,
                plant_hand_rank=plant_hand_rank,
                won_by_fold=won_by_fold,
            )

        return True


def check_fish_plant_poker_collision(
    fish: "Fish", plant: "FractalPlant", collision_distance: float = 50.0
) -> bool:
    """Check if a fish and plant are close enough for poker.

    Args:
        fish: The fish
        plant: The fractal plant
        collision_distance: Distance threshold for collision

    Returns:
        True if they can interact
    """
    dx = fish.pos.x - plant.pos.x
    dy = fish.pos.y - plant.pos.y
    distance_sq = dx * dx + dy * dy
    return distance_sq <= collision_distance * collision_distance
