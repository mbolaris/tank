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
    tank_name: str = "Unknown Tank"
    tank_id: str = "unknown"
    offspring_count: int = 0

    @property
    def contribution_score(self) -> float:
        """Calculate a deterministic soccer contribution score."""
        # goals * 3 + assists * 2 + net_energy * 0.01 + wins * 0.001 - matches * 0.0001
        return (
            self.goals * 3.0
            + self.assists * 2.0
            + self.net_energy * 0.01
            + self.wins * 0.001
            - self.matches * 0.0001
        )


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

        # Extract tank mapping if available on the outcome.
        # Fall back to empty dict if the field is not present (e.g. legacy outcomes)
        tank_names = getattr(outcome, "tank_names_by_fish", {}) or {}
        tank_ids = getattr(outcome, "tank_ids_by_fish", {}) or {}
        offspring_counts = getattr(outcome, "offspring_count_by_fish", {}) or {}

        for fish_id in participant_ids:
            row = self._stats.setdefault(fish_id, SoccerFishStats(fish_id=fish_id))
            row.matches += 1
            row.net_energy += float(outcome.energy_deltas.get(fish_id, 0.0))

            if fish_id in tank_names:
                row.tank_name = tank_names[fish_id]
            if fish_id in tank_ids:
                row.tank_id = tank_ids[fish_id]
            if fish_id in offspring_counts:
                row.offspring_count = max(row.offspring_count, offspring_counts[fish_id])

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
        # Preferred ranking priority: goals, assists, net energy, wins, matches, fish_id (ascending)
        return (-row.goals, -row.assists, -row.net_energy, -row.wins, -row.matches, row.fish_id)

    def leaders(self, top_n: int = 5) -> list[dict[str, Any]]:
        """Top-N standings as JSON-ready dicts, best first."""
        ranked = sorted(self._stats.values(), key=self._sort_key)
        return [
            {
                "fish_id": row.fish_id,
                "name": f"Fish #{row.fish_id}",
                "display_id": f"Fish #{row.fish_id}",
                "tank_id": row.tank_id,
                "tank_name": row.tank_name,
                "matches": row.matches,
                "matches_played": row.matches,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals": row.goals,
                "assists": row.assists,
                "net_energy": round(row.net_energy, 2),
                "net_energy_earned": round(row.net_energy, 2),
                "contribution_score": round(row.contribution_score, 4),
                "offspring_count": row.offspring_count,
            }
            for row in ranked[: max(0, top_n)]
        ]
