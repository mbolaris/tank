"""Opponent Modeling for composable poker strategy.

This module contains the SimpleOpponentModel dataclass.
"""

from dataclasses import dataclass

@dataclass
class SimpleOpponentModel:
    """Lightweight opponent tracking for composable strategy."""

    opponent_id: str = ""
    games_played: int = 0
    times_folded: int = 0
    times_raised: int = 0
    times_called: int = 0
    total_aggression: float = 0.0

    def update(self, folded: bool, raised: bool, called: bool, aggression: float) -> None:
        """Update model based on observed action."""
        self.games_played += 1
        if folded:
            self.times_folded += 1
        if raised:
            self.times_raised += 1
        if called:
            self.times_called += 1
        self.total_aggression += aggression

    @property
    def fold_rate(self) -> float:
        """Estimated fold frequency."""
        return self.times_folded / max(1, self.games_played)

    @property
    def aggression_factor(self) -> float:
        """Average aggression (raise frequency relative to call)."""
        if self.times_called == 0:
            return 1.0
        return self.times_raised / max(1, self.times_called)

    @property
    def avg_aggression(self) -> float:
        """Average reported aggression level."""
        return self.total_aggression / max(1, self.games_played)
