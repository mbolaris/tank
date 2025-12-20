"""Fish poker statistics component.

This module tracks individual fish poker performance for leaderboards and analysis.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


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
        games_non_button: Games played when not on the button
        wins_non_button: Wins when not on the button
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
    games_non_button: int = 0
    wins_non_button: int = 0

    # Private fields for tracking
    _hand_rank_sum: float = field(default=0.0, repr=False)
    # Track recent game results for skill progression (1 = win, 0 = loss/tie)
    # Using last 10 games for recent performance
    _recent_results: Deque[int] = field(default_factory=lambda: deque(maxlen=10), repr=False)

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

    def get_non_button_win_rate(self) -> float:
        """Calculate win rate when off the button."""
        if self.games_non_button == 0:
            return 0.0
        return self.wins_non_button / self.games_non_button

    def get_positional_advantage(self) -> float:
        """Calculate positional advantage (button win rate - off button win rate)."""
        return self.get_button_win_rate() - self.get_non_button_win_rate()

    def get_recent_win_rate(self) -> float:
        """Calculate win rate for recent games (last 10 games).

        Returns:
            Win rate for recent games (0.0 to 1.0), or 0.0 if no recent games
        """
        if len(self._recent_results) == 0:
            return 0.0
        return sum(self._recent_results) / len(self._recent_results)

    def get_skill_trend(self) -> str:
        """Get skill trend indicator based on recent vs overall performance.

        Returns:
            "improving" if recent win rate > overall win rate
            "declining" if recent win rate < overall win rate
            "stable" if similar or insufficient data
        """
        if len(self._recent_results) < 5:  # Need at least 5 games to assess trend
            return "stable"

        overall_wr = self.get_win_rate()
        recent_wr = self.get_recent_win_rate()

        # Use 10% threshold to avoid noise
        if recent_wr > overall_wr + 0.1:
            return "improving"
        elif recent_wr < overall_wr - 0.1:
            return "declining"
        else:
            return "stable"

    def record_win(
        self,
        energy_won: float,
        house_cut: float,
        hand_rank: int,
        won_at_showdown: bool,
        on_button: bool,
    ) -> None:
        """Record a poker win."""
        self.total_games += 1
        self.wins += 1
        self.total_energy_won += energy_won
        self.total_house_cuts_paid += house_cut
        self.best_hand_rank = max(self.best_hand_rank, hand_rank)
        self._hand_rank_sum += hand_rank

        # Track recent result
        self._recent_results.append(1)  # 1 for win

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
            self.games_non_button += 1
            self.wins_non_button += 1

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

        # Track recent result
        self._recent_results.append(0)  # 0 for loss

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
            self.games_non_button += 1

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

        # Track recent result
        self._recent_results.append(0)  # 0 for tie (not a win)

        # Reset streak
        self.current_streak = 0

        # Track positional stats
        if on_button:
            self.games_on_button += 1
        else:
            self.games_non_button += 1

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
            "non_button_win_rate": self.get_non_button_win_rate(),
            "positional_advantage": self.get_positional_advantage(),
            "recent_win_rate": self.get_recent_win_rate(),
            "skill_trend": self.get_skill_trend(),
        }
