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

    # Ranking weights. The hierarchy is deliberate:
    #
    #   goal (3.0)  >  assist (2.0)  >  win (1.5)  >  draw (0.5)
    #
    # Scoring outranks setting up, which outranks being on the winning side,
    # because the first two are things this fish did and the third is
    # substantially the team's doing - but a win is still worth half a goal,
    # not nothing. The previous weight of 0.001 made it pure decoration:
    # a fish would have needed a thousand wins to outrank one goal.
    #
    # net_energy is scaled down hard. It is a *consequence* of playing well
    # rather than a measure of it, it is already displayed on its own in the
    # leaderboard row, and on its raw scale it would otherwise swamp
    # everything else.
    #
    # Matches played is deliberately absent. Participation is chosen by the
    # league's selection strategy, not by the fish, so ranking on it measures
    # the scheduler. Ties break on fish_id for determinism.
    GOAL_WEIGHT = 3.0
    ASSIST_WEIGHT = 2.0
    WIN_WEIGHT = 1.5
    DRAW_WEIGHT = 0.5
    NET_ENERGY_WEIGHT = 0.01

    @property
    def contribution_score(self) -> float:
        """Calculate a deterministic soccer contribution score."""
        return (
            self.goals * self.GOAL_WEIGHT
            + self.assists * self.ASSIST_WEIGHT
            + self.wins * self.WIN_WEIGHT
            + self.draws * self.DRAW_WEIGHT
            + self.net_energy * self.NET_ENERGY_WEIGHT
        )


@dataclass
class SoccerFishStatsTracker:
    """Aggregates per-fish soccer stats from completed match outcomes.

    Storage is bounded: when more than ``max_tracked`` fish accumulate (dead
    fish keep their rows until pruned), the weakest rows are dropped.
    """

    max_tracked: int = 200
    _stats: dict[int, SoccerFishStats] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the bounded career table for world persistence."""
        return {
            "max_tracked": self.max_tracked,
            "stats": [
                {
                    "fish_id": row.fish_id,
                    "matches": row.matches,
                    "wins": row.wins,
                    "draws": row.draws,
                    "losses": row.losses,
                    "goals": row.goals,
                    "assists": row.assists,
                    "net_energy": row.net_energy,
                    "tank_name": row.tank_name,
                    "tank_id": row.tank_id,
                    "offspring_count": row.offspring_count,
                }
                for row in self._stats.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: Any) -> SoccerFishStatsTracker:
        """Restore a tracker while ignoring malformed rows from old saves."""
        max_tracked = int(data.get("max_tracked", 200)) if isinstance(data, dict) else 200
        tracker = cls(max_tracked=max_tracked)
        rows = data.get("stats", []) if isinstance(data, dict) else []
        for raw in rows:
            if not isinstance(raw, dict) or "fish_id" not in raw:
                continue
            try:
                row = SoccerFishStats(
                    fish_id=int(raw["fish_id"]),
                    matches=int(raw.get("matches", 0)),
                    wins=int(raw.get("wins", 0)),
                    draws=int(raw.get("draws", 0)),
                    losses=int(raw.get("losses", 0)),
                    goals=int(raw.get("goals", 0)),
                    assists=int(raw.get("assists", 0)),
                    net_energy=float(raw.get("net_energy", 0.0)),
                    tank_name=str(raw.get("tank_name", "Unknown Tank")),
                    tank_id=str(raw.get("tank_id", "unknown")),
                    offspring_count=int(raw.get("offspring_count", 0)),
                )
            except (TypeError, ValueError):
                continue
            tracker._stats[row.fish_id] = row
        tracker._prune()
        return tracker

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
        """Rank by contribution score, ties broken by fish_id for determinism.

        This used to be a lexicographic tuple
        ``(-goals, -assists, -net_energy, -wins, -matches, fish_id)``, which
        made every field after the first continuous one dead weight: two fish
        practically never tie on ``net_energy``, so ``wins`` decided nothing.
        Worse, it disagreed with ``contribution_score`` - published in the same
        payload, and the number the UI shows - about the direction of
        ``matches``: the tuple ranked more matches higher, the score ranked
        them lower. Ordering now comes from that one published score.
        """
        return (-row.contribution_score, row.fish_id)

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
