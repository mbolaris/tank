"""Incremental soccer league runtime for continuous matches."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import (
    SoccerMinigameOutcome,
    create_soccer_match_from_participants,
    finalize_soccer_match,
)
from core.minigames.soccer.league.provider import LeagueTeamProvider
from core.minigames.soccer.league.scheduler import LeagueScheduler
from core.minigames.soccer.league.types import (
    LeagueLeaderboardEntry,
    LeagueMatch,
    TeamAvailability,
    TeamSource,
)
from core.minigames.soccer.seeds import derive_soccer_seed


class BotEntity:
    """A generated bot entity for soccer matches."""

    def __init__(self, bot_id: str, team_id: str):
        self.fish_id = abs(hash(bot_id))
        self.team_id = team_id
        self.energy = 1000.0  # Infinite energy

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        return 0.0  # Bots don't consume energy


@dataclass
class SoccerLeagueRuntime:
    """Runs soccer league matches incrementally with bounded per-frame work."""

    config: SoccerConfig
    _match_counter: int = 0

    # Core League Components
    _provider: LeagueTeamProvider = field(init=False)
    _scheduler: LeagueScheduler = field(default_factory=LeagueScheduler)

    # State
    _leaderboard: dict[str, LeagueLeaderboardEntry] = field(default_factory=dict)
    _active_match: Any | None = None
    _active_setup: Any | None = None
    _current_league_match: LeagueMatch | None = None  # Metadata for active match

    # Recent history
    _recent_results: list[LeagueMatch] = field(default_factory=list)
    _team_availability: dict[str, TeamAvailability] = field(default_factory=dict)

    _pending_events: list[SoccerMinigameOutcome] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._provider = LeagueTeamProvider(self.config)

    def tick(self, world_state: Any, seed_base: int | None, cycle: int) -> None:
        """Advance the league by one world frame."""
        if not self.config.enabled:
            self._clear_active_match()
            return

        # 1. Provide Teams & Update Availability
        teams, availability = self._provider.get_teams(world_state)
        self._team_availability = availability

        # Ensure Leaderboard has entries for all known teams
        for team_id, team in teams.items():
            if team_id not in self._leaderboard:
                self._leaderboard[team_id] = LeagueLeaderboardEntry(
                    team_id=team_id,
                    display_name=team.display_name,
                    source=team.source,
                )

        # 2. Manage Active Match
        if self._active_match is None:
            if not self._should_start_match(cycle):
                return

            # Ensure schedule exists
            self._scheduler.ensure_schedule(list(teams.keys()))

            # Find next playable match
            league_match = self._scheduler.get_next_match(availability)

            if league_match:
                self._start_match(world_state, seed_base, league_match, teams)
            else:
                pass

        if self._active_match is None:
            return

        # 3. Step Active Match
        cycles_per_frame = max(1, int(getattr(self.config, "cycles_per_frame", 1)))
        self._active_match.step(num_steps=cycles_per_frame)

        if self._active_match.game_over:
            self._finalize_active_match(teams)

    def get_live_state(self) -> dict[str, Any] | None:
        """Return live match state for rendering."""

        state = {
            "leaderboard": [
                {
                    "team_id": e.team_id,
                    "display_name": e.display_name,
                    "matches_played": e.matches_played,
                    "wins": e.wins,
                    "draws": e.draws,
                    "losses": e.losses,
                    "gf": e.goals_for,
                    "ga": e.goals_against,
                    "points": e.points,
                    "rating": e.rating,
                    "source": e.source,
                }
                for e in sorted(
                    self._leaderboard.values(),
                    key=lambda x: (x.points, x.goal_difference),
                    reverse=True,
                )
            ],
            "availability": {
                tid: {"available": a.is_available, "reason": a.reason, "count": a.eligible_count}
                for tid, a in self._team_availability.items()
            },
            "active_match": None,
        }

        if self._active_match:
            match_state = self._active_match.get_state()
            # Enrich with league metadata
            if self._current_league_match:
                match_state["league_round"] = self._current_league_match.round_index
                match_state["home_id"] = self._current_league_match.home_team_id
                match_state["away_id"] = self._current_league_match.away_team_id

                # Add team names for display
                if self._current_league_match.home_team_id in self._leaderboard:
                    match_state["home_name"] = self._leaderboard[
                        self._current_league_match.home_team_id
                    ].display_name
                if self._current_league_match.away_team_id in self._leaderboard:
                    match_state["away_name"] = self._leaderboard[
                        self._current_league_match.away_team_id
                    ].display_name
            state["active_match"] = match_state

        return state

    def drain_events(self) -> list[SoccerMinigameOutcome]:
        """Return completed match outcomes and clear the buffer."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def _should_start_match(self, cycle: int) -> bool:
        match_every_frames = getattr(self.config, "match_every_frames", None)
        if match_every_frames is None:
            match_every_frames = self.config.interval_frames
        if match_every_frames <= 0:
            return False
        return cycle % match_every_frames == 0

    def _start_match(
        self,
        world_state: Any,
        seed_base: int | None,
        league_match: LeagueMatch,
        teams: dict[str, Any],
    ) -> None:
        home_team = teams[league_match.home_team_id]
        away_team = teams[league_match.away_team_id]

        entity_map = self._provider.find_entities(
            world_state, set(home_team.roster) | set(away_team.roster)
        )

        participants = []

        def add_team_participants(team, prefix):
            if team.source == TeamSource.BOT:
                for i in range(1, 12):  # 11 bots
                    participants.append(BotEntity(f"{prefix}_bot_{i}", team.team_id))
            else:
                for eid in team.roster:
                    if eid in entity_map:
                        participants.append(entity_map[eid])

        add_team_participants(home_team, "home")
        add_team_participants(away_team, "away")

        effective_seed_base = seed_base if seed_base is not None else 0
        selection_seed = derive_soccer_seed(
            int(effective_seed_base), self._match_counter, "selection"
        )
        match_seed = derive_soccer_seed(int(effective_seed_base), self._match_counter, "match")

        try:
            setup = create_soccer_match_from_participants(
                participants,
                duration_frames=self.config.duration_frames,
                code_source=getattr(world_state, "genome_code_pool", None),
                seed=match_seed,
                match_id=league_match.match_id,
                match_counter=self._match_counter,
                selection_seed=selection_seed,
                entry_fee_energy=getattr(self.config, "entry_fee_energy", 0.0),
            )
        except Exception as e:
            # Record a SKIPPED match so the UI has something to show and the league progresses.
            outcome = SoccerMinigameOutcome(
                match_id=f"S{self._match_counter}_{league_match.match_id}",
                match_counter=self._match_counter,
                winner_team=None,
                score_left=0,
                score_right=0,
                frames=0,
                seed=match_seed,
                selection_seed=selection_seed,
                message=f"SKIPPED: {e}",
                rewarded={},
                entry_fees={},
                energy_deltas={},
                repro_credit_deltas={},
                teams={tid: t.roster for tid, t in teams.items()},
                skipped=True,
                skip_reason=str(e),
            )
            self._pending_events.append(outcome)
            self._match_counter += 1
            self._scheduler.advance_match()
            self._clear_active_match()
            return

        self._active_match = setup.match
        self._active_setup = setup
        self._current_league_match = league_match

    def _finalize_active_match(self, teams: dict[str, Any]) -> None:
        if self._active_match is None or self._active_setup is None:
            return

        outcome = finalize_soccer_match(
            self._active_match,
            seed=self._active_setup.seed,
            match_counter=self._active_setup.match_counter,
            selection_seed=self._active_setup.selection_seed,
            entry_fees=self._active_setup.entry_fees,
            reward_mode=getattr(self.config, "reward_mode", "pot_payout"),
            reward_multiplier=getattr(self.config, "reward_multiplier", 1.0),
            repro_reward_mode=getattr(self.config, "repro_reward_mode", "credits"),
            repro_credit_award=getattr(self.config, "repro_credit_award", 0.0),
        )

        if self._current_league_match:
            winner = None
            if outcome.winner_team == "left":
                winner = self._current_league_match.home_team_id
            elif outcome.winner_team == "right":
                winner = self._current_league_match.away_team_id

            self._update_leaderboard(
                self._current_league_match.home_team_id,
                self._current_league_match.away_team_id,
                outcome.score_left,
                outcome.score_right,
            )

            self._current_league_match.home_score = outcome.score_left
            self._current_league_match.away_score = outcome.score_right
            self._current_league_match.winner_team_id = winner
            self._scheduler.advance_match()

            if winner:
                winning_team = teams.get(winner)
                if winning_team and winning_team.source == TeamSource.BOT:
                    outcome.rewarded.clear()
                    outcome.energy_deltas.clear()
                    outcome.repro_credit_deltas.clear()
                    outcome = replace(outcome, message=outcome.message + " (Bot win - no rewards)")

        self._pending_events.append(outcome)
        self._match_counter += 1
        self._clear_active_match()

    def _update_leaderboard(
        self, home_id: str, away_id: str, score_home: int, score_away: int
    ) -> None:
        for team_id, gf, ga in [
            (home_id, score_home, score_away),
            (away_id, score_away, score_home),
        ]:
            if team_id not in self._leaderboard:
                continue

            entry = self._leaderboard[team_id]
            entry.matches_played += 1
            entry.goals_for += gf
            entry.goals_against += ga

            if gf > ga:
                entry.wins += 1
                entry.points += 3
            elif gf == ga:
                entry.draws += 1
                entry.points += 1
            else:
                entry.losses += 1

    def _clear_active_match(self) -> None:
        self._active_match = None
        self._active_setup = None
        self._current_league_match = None
