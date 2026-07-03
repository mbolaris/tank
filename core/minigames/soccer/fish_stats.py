"""Per-fish soccer career stats aggregated across league matches.

The tracker consumes SoccerMinigameOutcome objects as matches finish and keeps
compact standings: matches, wins, goals, assists, and net energy per fish.
Bots are excluded naturally — participants are identified by the fish ids that
appear in the outcome's entry fees / energy deltas, and bots never pay fees or
receive energy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.minigames.soccer.types import SoccerMinigameOutcome


@dataclass
class SoccerFishStats:
    """Career soccer stats for one fish."""

    fish_id: int
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals: int = 0
    assists: int = 0
    net_energy: float = 0.0


@dataclass
class SoccerFishStatsTracker:
    """Aggregates per-fish soccer stats from completed match outcomes.

    Storage is bounded: when more than ``max_tracked`` fish accumulate (dead
    fish keep their rows until pruned), the weakest rows are dropped.
    """

    max_tracked: int = 200
    _stats: dict[int, SoccerFishStats] = field(default_factory=dict)

    def record(self, outcome: SoccerMinigameOutcome) -> None:
        """Fold one completed match outcome into the standings."""
        if outcome.skipped:
            return

        # Real fish pay entry fees / receive energy; bots do neither.
        participant_ids = set(outcome.entry_fees) | set(outcome.energy_deltas)
        if not participant_ids:
            return

        left = set(outcome.teams.get("left", []))
        right = set(outcome.teams.get("right", []))
        winner = outcome.winner_team

        for fish_id in participant_ids:
            row = self._stats.setdefault(fish_id, SoccerFishStats(fish_id=fish_id))
            row.matches += 1
            row.net_energy += float(outcome.energy_deltas.get(fish_id, 0.0))

            side = "left" if fish_id in left else "right" if fish_id in right else None
            if winner == "draw" or winner is None:
                row.draws += 1
            elif side == winner:
                row.wins += 1
            elif side is not None:
                row.losses += 1

            row.goals += int(outcome.goals_by_fish.get(fish_id, 0))
            row.assists += int(outcome.assists_by_fish.get(fish_id, 0))

        self._prune()

    def _prune(self) -> None:
        if len(self._stats) <= self.max_tracked:
            return
        ranked = sorted(self._stats.values(), key=self._sort_key)
        for row in ranked[self.max_tracked :]:
            del self._stats[row.fish_id]

    @staticmethod
    def _sort_key(row: SoccerFishStats) -> tuple[float, ...]:
        # Best first; fish_id ascending as a deterministic tie-break.
        return (-row.wins, -row.goals, -row.net_energy, -row.matches, row.fish_id)

    def leaders(self, top_n: int = 10) -> list[dict[str, Any]]:
        """Top-N standings as JSON-ready dicts, best first."""
        ranked = sorted(self._stats.values(), key=self._sort_key)
        return [
            {
                "fish_id": row.fish_id,
                "matches": row.matches,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals": row.goals,
                "assists": row.assists,
                "net_energy": round(row.net_energy, 2),
            }
            for row in ranked[: max(0, top_n)]
        ]
