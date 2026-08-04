"""Incremental soccer league runtime for continuous matches."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, ClassVar

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
    LeagueTeam,
    TeamAvailability,
    TeamSource,
)
from core.minigames.soccer.presentation import (
    PRESENTATION_MATCH_HOLD_TICKS,
    build_presentation_snapshot,
)
from core.minigames.soccer.reconciliation import build_world_source_resolver
from core.minigames.soccer.seeds import derive_soccer_seed


def _target_pursuit_module_enabled(world_state: Any) -> bool:
    """Whether league matches should evaluate each fish's shared pursuit module.

    ``world_state`` is the :class:`~core.simulation.engine.SimulationEngine`
    (``tick`` is called with the engine). The engine carries ``view_mode`` and
    ``genome_code_pool`` directly, but **not** ``simulation_config`` - that
    lives on ``engine.environment``. Reading it off the engine silently
    returned None and pinned this flag to False forever, so the league arm of
    the shared Target Pursuit Module never ran and tank-ball pursuit skill
    could not transfer into league play. Check the engine first (so a future
    engine-level config, or a test double, still works), then the environment.

    Only the two genuinely optional hops are dynamic. ``SimulationConfig.tank``
    and ``TankConfig.target_pursuit_module_enabled`` are declared dataclass
    fields that always exist, so those are read directly rather than through
    getattr defaults - a missing one is a bug worth raising, not a silent
    False, which is exactly the failure mode being fixed here.
    """
    for holder in (world_state, getattr(world_state, "environment", None)):
        config = getattr(holder, "simulation_config", None)
        if config is not None:
            return bool(config.tank.target_pursuit_module_enabled)
    return False


class BotEntity:
    """A generated bot entity for soccer matches."""

    def __init__(self, bot_id: str, team_id: str):
        self.fish_id = abs(hash(bot_id))
        self.team_id = team_id
        self.energy = 1000.0  # Infinite energy
        self.genome: Any | None = None

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        return 0.0  # Bots don't consume energy


@dataclass
class SoccerLeagueRuntime:
    """Runs soccer league matches incrementally with bounded per-frame work."""

    # Defensive cap to prevent unbounded leaderboard growth.
    MAX_LEADERBOARD_SIZE: ClassVar[int] = 50

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

    # Detached full-time snapshot kept only so the arena can present a result
    # instead of the match vanishing. Never a live match - see presentation.py.
    _presentation_match: dict[str, Any] | None = None
    _presentation_ticks_remaining: int = 0

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
            self._clear_presentation_match()
            return

        # Age out the retained full-time snapshot. Only while nothing is
        # executing: a live match already takes presentation priority.
        if self._active_match is None:
            self._expire_presentation_match()

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
                    world_id=team.world_id,
                )
            elif self._leaderboard[team_id].world_id is None and team.world_id is not None:
                # Entries created before the provider knew the origin world
                # (or by an older payload) get backfilled rather than stranded.
                self._leaderboard[team_id].world_id = team.world_id

        # Defensive: prune leaderboard if it exceeds the cap
        if len(self._leaderboard) > self.MAX_LEADERBOARD_SIZE:
            sorted_entries = sorted(
                self._leaderboard.items(),
                key=lambda item: (item[1].points, item[1].goal_difference),
            )
            excess = len(self._leaderboard) - self.MAX_LEADERBOARD_SIZE
            for team_id, _ in sorted_entries[:excess]:
                del self._leaderboard[team_id]

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

        # 3. Dynamic View Mode Update
        # Allow hot-swapping avatars even if match started in a different mode
        current_view_mode = getattr(world_state, "view_mode", "side")
        if (
            hasattr(self._active_match, "view_mode")
            and self._active_match.view_mode != current_view_mode
        ):
            self._active_match.view_mode = current_view_mode

        # 4. Step Active Match
        cycles_per_frame = max(1, int(getattr(self.config, "cycles_per_frame", 1)))
        self._active_match.step(num_steps=cycles_per_frame)

        if self._active_match.game_over:
            self._finalize_active_match(teams)

    def get_live_state(self) -> dict[str, Any] | None:
        """Return live match state for rendering."""

        ordered_entries = sorted(
            self._leaderboard.values(),
            key=lambda x: (x.points, x.goal_difference),
            reverse=True,
        )
        team_positions = {entry.team_id: index + 1 for index, entry in enumerate(ordered_entries)}
        team_form: dict[str, list[str]] = {}
        for result in self._recent_results:
            if result.skipped or not result.played:
                continue
            if result.winner_team_id == result.home_team_id:
                home_form, away_form = "W", "L"
            elif result.winner_team_id == result.away_team_id:
                home_form, away_form = "L", "W"
            else:
                home_form = away_form = "D"
            team_form.setdefault(result.home_team_id, []).append(home_form)
            team_form.setdefault(result.away_team_id, []).append(away_form)
        team_form = {team_id: values[-5:] for team_id, values in team_form.items()}

        # Authoritative team -> origin world mapping. Only tank teams have one,
        # and it comes from the provider rather than from splitting team_id or
        # reading a display name.
        team_world_ids = {
            entry.team_id: entry.world_id for entry in ordered_entries if entry.world_id is not None
        }

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
                    "world_id": e.world_id,
                }
                for e in ordered_entries
            ],
            "team_positions": team_positions,
            "team_form": team_form,
            "team_world_ids": team_world_ids,
            "availability": {
                tid: {"available": a.is_available, "reason": a.reason, "count": a.eligible_count}
                for tid, a in self._team_availability.items()
            },
            "active_match": None,
            "presentation_match": (
                self._presentation_match if self._presentation_ticks_remaining > 0 else None
            ),
        }

        if self._active_match:
            match_state = self._active_match.get_state()
            match_state.update(self._league_metadata())
            state["active_match"] = match_state

        return state

    def _league_metadata(self) -> dict[str, Any]:
        """League identity fields layered onto a match state for the UI.

        Shared by ``active_match`` and the retained ``presentation_match`` so a
        finished match is labelled exactly like it was while it played.
        """
        league_match = self._current_league_match
        if league_match is None:
            return {}
        home_id = league_match.home_team_id
        away_id = league_match.away_team_id
        home_entry = self._leaderboard.get(home_id)
        away_entry = self._leaderboard.get(away_id)
        return {
            "league_round": league_match.round_index,
            "home_id": home_id,
            "away_id": away_id,
            "home_name": home_entry.display_name if home_entry else home_id,
            "away_name": away_entry.display_name if away_entry else away_id,
        }

    def drain_events(self) -> list[SoccerMinigameOutcome]:
        """Return completed match outcomes and clear the buffer."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def _should_start_match(self, cycle: int) -> bool:
        match_every_frames_raw = getattr(self.config, "match_every_frames", None)
        if match_every_frames_raw is None:
            match_every_frames_raw = getattr(self.config, "interval_frames", 0)
        if match_every_frames_raw is None:
            match_every_frames = 0
        else:
            try:
                match_every_frames = int(match_every_frames_raw)
            except (TypeError, ValueError):
                match_every_frames = 0
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

        # Collect all entity IDs needed for both teams
        needed_ids: set[int] = set()
        for team in [home_team, away_team]:
            if team.source == TeamSource.TANK:
                needed_ids.update(team.roster)

        # Use provider to find entities across ALL connected worlds
        entity_map = self._provider.find_entities(world_state, needed_ids)

        # Validate and balance participants
        home_participants: list[Any] = []
        away_participants: list[Any] = []

        team_size = self._provider._get_team_size()

        def collect_team_participants(
            team: LeagueTeam, prefix: str, target_list: list[Any]
        ) -> None:
            if team.source == TeamSource.BOT:
                for i in range(1, team_size + 1):
                    target_list.append(BotEntity(f"{prefix}_bot_{i}", team.team_id))
            else:
                for eid in team.roster:
                    if eid in entity_map:
                        target_list.append(entity_map[eid])

        collect_team_participants(home_team, "home", home_participants)
        collect_team_participants(away_team, "away", away_participants)

        # Drop participants that cannot afford the entry fee. create_soccer_match_*
        # raises if a fee is unaffordable, so filtering here keeps a nonzero fee from
        # crashing the league tick. Bots report a zero-energy delta and never pay, so
        # they pass the affordability check unconditionally.
        entry_fee = float(getattr(self.config, "entry_fee_energy", 0.0) or 0.0)
        if entry_fee > 0:
            home_participants = [p for p in home_participants if self._can_afford_fee(p, entry_fee)]
            away_participants = [p for p in away_participants if self._can_afford_fee(p, entry_fee)]

        # Balance teams to ensure equal numbers (and thus even total for evaluator)
        common_count = min(len(home_participants), len(away_participants))
        if common_count < 1:
            # Cannot start match with empty team
            # We skip this tick; scheduler will keep retrying until players are available
            # or availability check catches it next frame
            return

        participants = home_participants[:common_count] + away_participants[:common_count]

        effective_seed_base = seed_base if seed_base is not None else 0
        selection_seed = derive_soccer_seed(
            int(effective_seed_base), self._match_counter, "selection"
        )
        match_seed = derive_soccer_seed(int(effective_seed_base), self._match_counter, "match")

        # Determine view mode from world state (default to side/tank)
        view_mode = getattr(world_state, "view_mode", "side")

        target_pursuit_enabled = _target_pursuit_module_enabled(world_state)

        setup = create_soccer_match_from_participants(
            participants,
            duration_frames=self.config.duration_frames,
            code_source=getattr(world_state, "genome_code_pool", None),
            seed=match_seed,
            match_id=league_match.match_id,
            match_counter=self._match_counter,
            selection_seed=selection_seed,
            entry_fee_energy=getattr(self.config, "entry_fee_energy", 0.0),
            view_mode=view_mode,
            target_pursuit_module_enabled=target_pursuit_enabled,
            source_resolver=build_world_source_resolver(world_state),
            reconciliation_store=getattr(
                getattr(world_state, "soccer_events", None), "reconciliation_store", None
            ),
        )

        # A new fixture takes presentation priority immediately.
        self._clear_presentation_match()
        self._active_match = setup.match
        self._active_setup = setup
        self._current_league_match = league_match

    @staticmethod
    def _can_afford_fee(entity: Any, entry_fee: float) -> bool:
        """Whether an entity can pay the entry fee (mirrors evaluator's guard)."""
        from core.minigames.soccer.selection import get_entity_energy

        if not hasattr(entity, "modify_energy"):
            return False
        return get_entity_energy(entity) > entry_fee

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
            source_resolver=self._active_setup.source_resolver,
            reconciliation_store=self._active_setup.reconciliation_store,
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
            self._current_league_match.played = True
            self._recent_results.append(replace(self._current_league_match))
            self._recent_results = self._recent_results[-50:]
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

        # Detach a full-time snapshot for the arena *before* the live match is
        # dropped. build_presentation_snapshot deep-copies, so nothing below
        # keeps a reference to the match, engine, roster, or any fish.
        self._presentation_match = build_presentation_snapshot(
            self._active_match.get_state(),
            **self._league_metadata(),
        )
        self._presentation_ticks_remaining = PRESENTATION_MATCH_HOLD_TICKS

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

    def _clear_presentation_match(self) -> None:
        """Drop the retained full-time snapshot immediately."""
        self._presentation_match = None
        self._presentation_ticks_remaining = 0

    def _expire_presentation_match(self) -> None:
        """Age the retained snapshot by one world tick, dropping it at zero."""
        if self._presentation_ticks_remaining <= 0:
            return
        self._presentation_ticks_remaining -= 1
        if self._presentation_ticks_remaining <= 0:
            self._presentation_match = None
