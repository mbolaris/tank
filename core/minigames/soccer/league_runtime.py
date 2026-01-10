"""Incremental soccer league runtime for continuous matches."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import (
    SelectionStrategy,
    SoccerMinigameOutcome,
    create_soccer_match_from_participants,
    finalize_soccer_match,
    select_soccer_participants,
)
from core.minigames.soccer.seeds import derive_soccer_seed


def _parse_selection_strategy(value: str) -> SelectionStrategy:
    value = value.lower().strip()
    for strat in SelectionStrategy:
        if strat.value == value:
            return strat
    return SelectionStrategy.STRATIFIED


@dataclass
class SoccerLeagueRuntime:
    """Runs soccer league matches incrementally with bounded per-frame work."""

    config: SoccerConfig
    _match_counter: int = 0
    _cooldown_map: dict[int, int] = field(default_factory=dict)
    _active_match: Any | None = None
    _active_setup: Any | None = None
    _active_selection_seed: int | None = None
    _active_match_seed: int | None = None
    _pending_events: list[SoccerMinigameOutcome] = field(default_factory=list)

    def tick(self, world_state: Any, seed_base: int | None, cycle: int) -> None:
        """Advance the league by one world frame."""
        if not self.config.enabled:
            self._clear_active_match()
            return

        if self._active_match is None:
            if not self._should_start_match(cycle):
                return
            self._start_match(world_state, seed_base)

        if self._active_match is None:
            return

        cycles_per_frame = max(1, int(getattr(self.config, "cycles_per_frame", 1)))
        self._active_match.step(num_steps=cycles_per_frame)

        if self._active_match.game_over:
            self._finalize_active_match()

    def get_live_state(self) -> dict[str, Any] | None:
        """Return live match state for rendering."""
        if self._active_match is None:
            return None
        return self._active_match.get_state()

    def drain_events(self) -> list[SoccerMinigameOutcome]:
        """Return completed match outcomes and clear the buffer."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def _should_start_match(self, cycle: int) -> bool:
        matches_per_tick = int(getattr(self.config, "matches_per_tick", 1))
        if matches_per_tick <= 0:
            return False
        match_every_frames = getattr(self.config, "match_every_frames", None)
        if match_every_frames is None:
            match_every_frames = self.config.interval_frames
        if match_every_frames <= 0:
            return False
        return cycle % match_every_frames == 0

    def _start_match(self, world_state: Any, seed_base: int | None) -> None:
        candidates = self._get_candidates(world_state)
        has_min_candidates = len(candidates) >= self.config.min_players

        strategy = _parse_selection_strategy(
            getattr(self.config, "selection_strategy", "stratified")
        )

        effective_seed_base = getattr(self.config, "seed_base", None)
        if effective_seed_base is None:
            effective_seed_base = seed_base
        if effective_seed_base is None:
            effective_seed_base = 0

        selection_seed = derive_soccer_seed(
            int(effective_seed_base), self._match_counter, "selection"
        )
        match_seed = derive_soccer_seed(int(effective_seed_base), self._match_counter, "match")
        match_id = f"soccer_{match_seed}_{self._match_counter}"

        cooldown_ids = self._get_cooldown_ids()
        if not has_min_candidates:
            self._pending_events.append(
                self._build_skip_outcome(
                    match_id=match_id,
                    match_counter=self._match_counter,
                    match_seed=match_seed,
                    selection_seed=selection_seed,
                    reason="not_enough_candidates",
                )
            )
            self._match_counter += 1
            self._cleanup_cooldown()
            return

        num_players = self._get_num_players()
        try:
            selected = select_soccer_participants(
                candidates,
                num_players,
                strategy=strategy,
                cooldown_ids=cooldown_ids,
                seed=selection_seed,
                allow_repeat_within_match=getattr(self.config, "allow_repeat_within_match", False),
                entry_fee_energy=getattr(self.config, "entry_fee_energy", 0.0),
            )
        except ValueError:
            selected = []

        if len(selected) != num_players:
            self._pending_events.append(
                self._build_skip_outcome(
                    match_id=match_id,
                    match_counter=self._match_counter,
                    match_seed=match_seed,
                    selection_seed=selection_seed,
                    reason="selection_failed",
                )
            )
            self._match_counter += 1
            self._cleanup_cooldown()
            return

        setup = create_soccer_match_from_participants(
            selected,
            duration_frames=self.config.duration_frames,
            code_source=getattr(world_state, "genome_code_pool", None),
            seed=match_seed,
            match_id=match_id,
            match_counter=self._match_counter,
            selection_seed=selection_seed,
            entry_fee_energy=getattr(self.config, "entry_fee_energy", 0.0),
        )
        self._active_match = setup.match
        self._active_setup = setup
        self._active_selection_seed = selection_seed
        self._active_match_seed = match_seed

    def _finalize_active_match(self) -> None:
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
        self._pending_events.append(outcome)

        played_ids = []
        for team in outcome.teams.values():
            played_ids.extend(team)
        self._add_to_cooldown(played_ids)

        self._match_counter += 1
        self._cleanup_cooldown()
        self._clear_active_match()

    def _clear_active_match(self) -> None:
        self._active_match = None
        self._active_setup = None
        self._active_selection_seed = None
        self._active_match_seed = None

    def _get_num_players(self) -> int:
        team_size = getattr(self.config, "team_size", None)
        if team_size is not None and team_size > 0:
            return int(team_size) * 2
        return int(self.config.num_players)

    def _get_candidates(self, world_state: Any) -> list[Any]:
        fish_list = []
        if hasattr(world_state, "get_fish_list"):
            fish_list = list(world_state.get_fish_list())
        alive = []
        for fish in fish_list:
            is_dead = getattr(fish, "is_dead", None)
            if callable(is_dead) and is_dead():
                continue
            alive.append(fish)
        return alive

    def _get_cooldown_ids(self) -> frozenset[int]:
        return frozenset(
            fish_id
            for fish_id, eligible_at in self._cooldown_map.items()
            if self._match_counter < eligible_at
        )

    def _add_to_cooldown(self, fish_ids: list[int]) -> None:
        cooldown_matches = getattr(self.config, "cooldown_matches", 3)
        if cooldown_matches <= 0:
            return
        eligible_at = self._match_counter + cooldown_matches
        for fish_id in fish_ids:
            self._cooldown_map[fish_id] = eligible_at

    def _cleanup_cooldown(self) -> None:
        self._cooldown_map = {
            fish_id: eligible_at
            for fish_id, eligible_at in self._cooldown_map.items()
            if self._match_counter < eligible_at
        }

    def _build_skip_outcome(
        self,
        *,
        match_id: str,
        match_counter: int,
        match_seed: int | None,
        selection_seed: int | None,
        reason: str,
    ) -> SoccerMinigameOutcome:
        return SoccerMinigameOutcome(
            match_id=match_id,
            match_counter=match_counter,
            winner_team=None,
            score_left=0,
            score_right=0,
            frames=0,
            seed=match_seed,
            selection_seed=selection_seed,
            message="match_skipped",
            rewarded={},
            entry_fees={},
            energy_deltas={},
            repro_credit_deltas={},
            teams={"left": [], "right": []},
            skipped=True,
            skip_reason=reason,
        )
