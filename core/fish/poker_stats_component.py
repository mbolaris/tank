"""Fish poker statistics component.

This module tracks individual fish poker performance for leaderboards and analysis.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class FishPokerStats:
    """Tracks poker statistics for an individual fish.

    This component maintains lifetime poker statistics for each fish,
    enabling leaderboards and performance tracking.

    Attributes:
        total_games: Total poker games played
        wins: Number of games won
        losses: Number of games lost
        ties: Number of tied games
        total_energy_won: Cumulative energy won from poker
        total_energy_lost: Cumulative energy lost from poker
        net_energy: Net profit/loss (won - lost)
        current_streak: Current winning streak (negative if losing)
        best_streak: Best winning streak achieved
        worst_streak: Worst losing streak experienced
        hands_won_at_showdown: Wins at showdown (vs fold)
        hands_won_by_fold: Wins by opponent folding
        times_folded: Number of times this fish folded
        showdown_count: Games that reached showdown
        best_hand_rank: Best hand rank achieved (0-9)
        total_house_cuts_paid: Total house cut paid from winnings
        games_on_button: Games played on the button
        wins_on_button: Wins when on the button
        games_off_button: Games played off the button
        wins_off_button: Wins when off the button
    """

    total_games: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    total_energy_won: float = 0.0
    total_energy_lost: float = 0.0
    current_streak: int = 0
    best_streak: int = 0
    worst_streak: int = 0
    hands_won_at_showdown: int = 0
    hands_won_by_fold: int = 0
    times_folded: int = 0
    showdown_count: int = 0
    best_hand_rank: int = 0
    total_house_cuts_paid: float = 0.0
    games_on_button: int = 0
    wins_on_button: int = 0
    games_off_button: int = 0
    wins_off_button: int = 0

    # Private fields for tracking
    _hand_rank_sum: float = field(default=0.0, repr=False)

    def get_net_energy(self) -> float:
        """Calculate net energy profit/loss."""
        return self.total_energy_won - self.total_energy_lost - self.total_house_cuts_paid

    def get_win_rate(self) -> float:
        """Calculate win rate percentage (0.0 to 1.0)."""
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games

    def get_roi(self) -> float:
        """Calculate Return on Investment (net energy per game)."""
        if self.total_games == 0:
            return 0.0
        return self.get_net_energy() / self.total_games

    def get_avg_hand_rank(self) -> float:
        """Calculate average hand rank achieved."""
        if self.total_games == 0:
            return 0.0
        return self._hand_rank_sum / self.total_games

    def get_showdown_win_rate(self) -> float:
        """Calculate win rate when reaching showdown."""
        if self.showdown_count == 0:
            return 0.0
        return self.hands_won_at_showdown / self.showdown_count

    def get_fold_rate(self) -> float:
        """Calculate how often this fish folds."""
        if self.total_games == 0:
            return 0.0
        return self.times_folded / self.total_games

    def get_button_win_rate(self) -> float:
        """Calculate win rate when on the button."""
        if self.games_on_button == 0:
            return 0.0
        return self.wins_on_button / self.games_on_button

    def get_off_button_win_rate(self) -> float:
        """Calculate win rate when off the button."""
        if self.games_off_button == 0:
            return 0.0
        return self.wins_off_button / self.games_off_button

    def get_positional_advantage(self) -> float:
        """Calculate positional advantage (button win rate - off button win rate)."""
        return self.get_button_win_rate() - self.get_off_button_win_rate()

    def record_win(
        self,
        energy_won: float,
        house_cut: float,
        hand_rank: int,
        won_at_showdown: bool,
        on_button: bool,
    ) -> None:
        """Record a poker win.

        Args:
            energy_won: Energy gained from winning
            house_cut: House cut paid from winnings
            hand_rank: Rank of the winning hand (0-9)
            won_at_showdown: True if won at showdown, False if opponent folded
            on_button: True if this fish was on the button
        """
        self.total_games += 1
        self.wins += 1
        self.total_energy_won += energy_won
        self.total_house_cuts_paid += house_cut
        self.best_hand_rank = max(self.best_hand_rank, hand_rank)
        self._hand_rank_sum += hand_rank

        # Update streak
        if self.current_streak >= 0:
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.best_streak = max(self.best_streak, self.current_streak)

        # Track showdown vs fold wins
        if won_at_showdown:
            self.hands_won_at_showdown += 1
            self.showdown_count += 1
        else:
            self.hands_won_by_fold += 1

        # Track positional stats
        if on_button:
            self.games_on_button += 1
            self.wins_on_button += 1
        else:
            self.games_off_button += 1
            self.wins_off_button += 1

    def record_loss(
        self,
        energy_lost: float,
        hand_rank: int,
        folded: bool,
        reached_showdown: bool,
        on_button: bool,
    ) -> None:
        """Record a poker loss.

        Args:
            energy_lost: Energy lost from losing
            hand_rank: Rank of the hand (0-9)
            folded: True if this fish folded
            reached_showdown: True if game reached showdown
            on_button: True if this fish was on the button
        """
        self.total_games += 1
        self.losses += 1
        self.total_energy_lost += energy_lost
        self._hand_rank_sum += hand_rank

        # Update streak
        if self.current_streak <= 0:
            self.current_streak -= 1
        else:
            self.current_streak = -1
        self.worst_streak = min(self.worst_streak, self.current_streak)

        # Track fold stats
        if folded:
            self.times_folded += 1
        elif reached_showdown:
            self.showdown_count += 1

        # Track positional stats
        if on_button:
            self.games_on_button += 1
        else:
            self.games_off_button += 1

    def record_tie(self, hand_rank: int, on_button: bool) -> None:
        """Record a poker tie.

        Args:
            hand_rank: Rank of the hand (0-9)
            on_button: True if this fish was on the button
        """
        self.total_games += 1
        self.ties += 1
        self._hand_rank_sum += hand_rank
        self.showdown_count += 1  # Ties only happen at showdown

        # Reset streak
        self.current_streak = 0

        # Track positional stats
        if on_button:
            self.games_on_button += 1
        else:
            self.games_off_button += 1

    def get_stats_dict(self) -> dict:
        """Get statistics as a dictionary for serialization.

        Returns:
            Dictionary containing all poker statistics
        """
        return {
            "total_games": self.total_games,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "win_rate": self.get_win_rate(),
            "total_energy_won": self.total_energy_won,
            "total_energy_lost": self.total_energy_lost,
            "net_energy": self.get_net_energy(),
            "roi": self.get_roi(),
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "worst_streak": self.worst_streak,
            "showdown_win_rate": self.get_showdown_win_rate(),
            "fold_rate": self.get_fold_rate(),
            "best_hand_rank": self.best_hand_rank,
            "avg_hand_rank": self.get_avg_hand_rank(),
            "button_win_rate": self.get_button_win_rate(),
            "off_button_win_rate": self.get_off_button_win_rate(),
            "positional_advantage": self.get_positional_advantage(),
        }
