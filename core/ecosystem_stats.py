"""Dataclasses for ecosystem statistics and tracking.

This module contains all the statistics dataclasses used by the EcosystemManager.
Extracted from ecosystem.py to improve code organization and maintainability.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from core.constants import TOTAL_ALGORITHM_COUNT, TOTAL_SPECIES_COUNT


@dataclass
class AlgorithmStats:
    """Performance statistics for a behavior algorithm.

    Attributes:
        algorithm_id: Unique identifier for the algorithm (0-47)
        algorithm_name: Human-readable name
        total_births: Total fish born with this algorithm
        total_deaths: Total fish died with this algorithm
        deaths_starvation: Deaths due to starvation
        deaths_old_age: Deaths due to old age
        deaths_predation: Deaths due to predation
        total_reproductions: Number of times fish with this algorithm reproduced
        current_population: Current living fish with this algorithm
        total_lifespan: Sum of lifespans for averaging
        total_food_eaten: Total food items consumed by fish with this algorithm
    """

    algorithm_id: int
    algorithm_name: str = ""
    total_births: int = 0
    total_deaths: int = 0
    deaths_starvation: int = 0
    deaths_old_age: int = 0
    deaths_predation: int = 0
    total_reproductions: int = 0
    current_population: int = 0
    total_lifespan: int = 0
    total_food_eaten: int = 0

    def get_avg_lifespan(self) -> float:
        return self.total_lifespan / self.total_deaths if self.total_deaths > 0 else 0.0

    def get_survival_rate(self) -> float:
        return self.current_population / self.total_births if self.total_births > 0 else 0.0

    def get_reproduction_rate(self) -> float:
        return self.total_reproductions / self.total_births if self.total_births > 0 else 0.0


@dataclass
class GenerationStats:
    """Statistics for a generation of fish.

    Attributes:
        generation: Generation number
        population: Number of fish alive
        births: Number of births this generation
        deaths: Number of deaths this generation
        avg_age: Average age at death
        avg_speed: Average speed modifier
        avg_size: Average size modifier
        avg_energy: Average max energy
    """

    generation: int
    population: int = 0
    births: int = 0
    deaths: int = 0
    avg_age: float = 0.0
    avg_speed: float = 1.0
    avg_size: float = 1.0
    avg_energy: float = 1.0


@dataclass
class PokerStats:
    """Poker game statistics for an algorithm.

    Attributes:
        algorithm_id: Unique identifier for the algorithm
        total_games: Total poker games played
        total_wins: Total games won
        total_losses: Total games lost
        total_ties: Total games tied
        total_energy_won: Total energy gained from poker
        total_energy_lost: Total energy lost from poker
        total_house_cuts: Total energy taken by house
        best_hand_rank: Best hand rank achieved (0-9)
        avg_hand_rank: Average hand rank
        folds: Number of times folded
        won_at_showdown: Number of wins at showdown (vs fold)
        won_by_fold: Number of wins because opponent folded
        showdown_count: Number of times reached showdown
        button_wins: Wins when on the button
        button_games: Games played on the button
        non_button_wins: Wins when not on the button
        non_button_games: Games played when not on the button
        preflop_folds: Folds during pre-flop
        postflop_folds: Folds after seeing flop
        avg_pot_size: Average pot size
        total_raises: Total number of raises made
        total_calls: Total number of calls made
    """

    algorithm_id: int
    total_games: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_ties: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0
    total_house_cuts: float = 0.0
    best_hand_rank: int = 0
    avg_hand_rank: float = 0.0
    _total_hand_rank: float = field(default=0.0, repr=False)  # For averaging

    # New detailed stats
    folds: int = 0
    won_at_showdown: int = 0
    won_by_fold: int = 0
    showdown_count: int = 0
    button_wins: int = 0
    button_games: int = 0
    non_button_wins: int = 0
    non_button_games: int = 0
    preflop_folds: int = 0
    postflop_folds: int = 0
    avg_pot_size: float = 0.0
    _total_pot_size: float = field(default=0.0, repr=False)
    total_raises: int = 0
    total_calls: int = 0

    def get_win_rate(self) -> float:
        return self.total_wins / self.total_games if self.total_games > 0 else 0.0

    def get_net_energy(self) -> float:
        return self.total_energy_won - self.total_energy_lost - self.total_house_cuts

    def get_showdown_win_rate(self) -> float:
        return self.won_at_showdown / self.showdown_count if self.showdown_count > 0 else 0.0

    def get_fold_rate(self) -> float:
        return self.folds / self.total_games if self.total_games > 0 else 0.0

    def get_button_win_rate(self) -> float:
        return self.button_wins / self.button_games if self.button_games > 0 else 0.0

    def get_non_button_win_rate(self) -> float:
        return self.non_button_wins / self.non_button_games if self.non_button_games > 0 else 0.0

    def get_aggression_factor(self) -> float:
        return self.total_raises / self.total_calls if self.total_calls > 0 else 0.0

    def get_roi(self) -> float:
        return self.get_net_energy() / self.total_games if self.total_games > 0 else 0.0

    def get_vpip(self) -> float:
        """Calculate VPIP (Voluntarily Put money In Pot) percentage.

        VPIP measures how often a player plays a hand (doesn't fold pre-flop).
        Higher VPIP = looser play, Lower VPIP = tighter play.
        """
        return (
            (self.total_games - self.preflop_folds) / self.total_games
            if self.total_games > 0
            else 0.0
        )

    def get_bluff_success_rate(self) -> float:
        """Calculate bluff success rate (wins by fold / total folds by opponent).

        This estimates how often the player successfully bluffs opponents into folding.
        """
        total_fold_opportunities = self.won_by_fold + self.folds
        return self.won_by_fold / total_fold_opportunities if total_fold_opportunities > 0 else 0.0

    def get_positional_advantage(self) -> float:
        """Calculate positional advantage (button win rate - off-button win rate).

        Positive values indicate better performance on the button (as expected).
        Larger positive values suggest good exploitation of position.
        """
        return self.get_button_win_rate() - self.get_off_button_win_rate()

    def get_showdown_percentage(self) -> float:
        """Calculate percentage of games that went to showdown."""
        return self.showdown_count / self.total_games if self.total_games > 0 else 0.0

    def get_postflop_fold_rate(self) -> float:
        """Calculate percentage of folds that occurred post-flop.

        Higher values suggest better pre-flop selection but weaker post-flop play.
        """
        return self.postflop_folds / self.folds if self.folds > 0 else 0.0


@dataclass
class EcosystemEvent:
    """Represents an event in the ecosystem.

    Attributes:
        frame: Frame number when event occurred
        event_type: Type of event ('birth', 'death', 'starvation', 'old_age', 'predation', 'poker')
        fish_id: ID of the fish involved
        details: Additional details about the event
    """

    frame: int
    event_type: str
    fish_id: int
    details: str = ""


@dataclass
class PokerOutcomeRecord:
    """Encapsulates poker game outcome data for stats recording.

    This is a Parameter Object that groups the many parameters needed
    to record a poker outcome. Using this dataclass instead of many
    individual parameters provides:

    - Self-documenting code (field names explain meaning)
    - Easier extension (add fields without changing method signatures)
    - Type safety (IDE autocomplete and type checking)
    - Default values for optional fields

    Design Note:
        This is distinct from PokerResult (in fish_poker.py) which represents
        the full game result including hands, betting history, etc. This record
        contains only what's needed for statistics tracking.

    Example:
        record = PokerOutcomeRecord(
            winner_id=fish1.id,
            loser_id=fish2.id,
            amount=25.5,
            winner_hand=winner_hand,
            loser_hand=loser_hand,
        )
        ecosystem.record_poker_outcome(record)
    """

    # Required fields - who won and lost
    winner_id: int
    loser_id: int

    # Energy transfer
    amount: float
    house_cut: float = 0.0

    # Algorithm IDs for tracking performance by behavior
    winner_algo_id: Optional[int] = None
    loser_algo_id: Optional[int] = None

    # Hand information (imported types would create circular deps, use Any)
    winner_hand: object = None  # PokerHand
    loser_hand: object = None  # PokerHand

    # Full game result for detailed stats (optional)
    result: object = None  # PokerResult

    # Player algorithm IDs for positional stats (for multiplayer)
    player1_algo_id: Optional[int] = None
    player2_algo_id: Optional[int] = None

    @property
    def is_tie(self) -> bool:
        """Check if this was a tie (winner_id == -1)."""
        return self.winner_id == -1

    @property
    def net_amount(self) -> float:
        """Net energy transferred (amount minus house cut)."""
        return self.amount - self.house_cut


@dataclass
class ReproductionStats:
    """Statistics for reproduction dynamics.

    Attributes:
        total_reproductions: Total successful reproductions
        total_mating_attempts: Total mating attempts (successful + failed)
        total_failed_attempts: Total failed mating attempts
        current_pregnant_fish: Current number of pregnant fish
        total_offspring: Total offspring produced
    """

    total_reproductions: int = 0
    total_mating_attempts: int = 0
    total_failed_attempts: int = 0
    current_pregnant_fish: int = 0
    total_offspring: int = 0
    total_sexual_reproductions: int = 0
    total_asexual_reproductions: int = 0

    def get_success_rate(self) -> float:
        """Calculate mating success rate."""
        return (
            self.total_reproductions / self.total_mating_attempts
            if self.total_mating_attempts > 0
            else 0.0
        )

    def get_offspring_per_reproduction(self) -> float:
        """Calculate average offspring per reproduction."""
        return (
            self.total_offspring / self.total_reproductions if self.total_reproductions > 0 else 0.0
        )


@dataclass
class GeneticDiversityStats:
    """Statistics for genetic diversity in the population.

    Attributes:
        unique_algorithms: Number of unique behavior algorithms present
        unique_species: Number of unique species present
        color_variance: Variance in color hue (0-1)
        trait_variances: Dict of trait name to variance
        avg_genome_similarity: Average genetic similarity (0-1, optional)
    """

    unique_algorithms: int = 0
    unique_species: int = 0
    color_variance: float = 0.0
    trait_variances: Dict[str, float] = field(default_factory=dict)
    avg_genome_similarity: float = 0.0

    def get_diversity_score(self) -> float:
        """Calculate overall diversity score (0-1, higher is more diverse)."""
        # Combine multiple diversity metrics
        # More algorithms and species = better, higher variance = better
        algo_score = min(self.unique_algorithms / float(TOTAL_ALGORITHM_COUNT), 1.0)
        species_score = min(self.unique_species / float(TOTAL_SPECIES_COUNT), 1.0)
        color_score = min(self.color_variance * 3.0, 1.0)  # Normalize variance

        # Average the scores
        return (algo_score + species_score + color_score) / 3.0


@dataclass
class FishOpponentPokerStats:
    """Statistics for a fish's performance against non-fish opponents (plants).

    This tracks how well each fish performs in poker games against
    non-fish opponents like fractal plants.

    Attributes:
        fish_id: Unique identifier for the fish
        fish_name: Display name for the fish
        total_games: Total games played against opponents
        wins: Games won against opponents
        losses: Games lost against opponents
        total_energy_won: Total energy gained from opponents
        total_energy_lost: Total energy lost to opponents
        best_hand_rank: Best hand rank achieved (0-9)
        avg_hand_rank: Average hand rank
        wins_by_fold: Wins because opponent folded
        losses_by_fold: Losses because fish folded
    """

    fish_id: int
    fish_name: str = ""
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0
    best_hand_rank: int = 0
    avg_hand_rank: float = 0.0
    _total_hand_rank: float = field(default=0.0, repr=False)
    wins_by_fold: int = 0
    losses_by_fold: int = 0

    def get_win_rate(self) -> float:
        """Calculate win rate against opponents."""
        return self.wins / self.total_games if self.total_games > 0 else 0.0

    def get_net_energy(self) -> float:
        """Calculate net energy gained/lost against opponents."""
        return self.total_energy_won - self.total_energy_lost

    def get_avg_energy_per_game(self) -> float:
        """Calculate average energy per game."""
        return self.get_net_energy() / self.total_games if self.total_games > 0 else 0.0

    def get_fold_win_rate(self) -> float:
        """Calculate rate of wins by fold (bluffing success)."""
        return self.wins_by_fold / self.wins if self.wins > 0 else 0.0

    def get_score(self) -> float:
        """Calculate overall performance score for leaderboard ranking.

        Combines win rate (60%), net energy (30%), and games played (10%).
        """
        if self.total_games == 0:
            return 0.0

        # Win rate component (0-60 points)
        win_rate_score = self.get_win_rate() * 60.0

        # Net energy component (0-30 points, normalized)
        # Assume typical range is -500 to +500 energy
        net_energy_normalized = max(-1.0, min(1.0, self.get_net_energy() / 500.0))
        energy_score = (net_energy_normalized + 1.0) / 2.0 * 30.0

        # Games played component (0-10 points, more games = more reliable)
        # Cap at 50 games for full points
        games_score = min(self.total_games / 50.0, 1.0) * 10.0

        return win_rate_score + energy_score + games_score
