"""Scheduled soccer minigame evaluator for Tank-like worlds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import (
    SelectionStrategy, SoccerMinigameOutcome,
    create_soccer_match_from_participants, derive_soccer_seed,
    finalize_soccer_match, select_soccer_participants)

MatchRunner = Callable[..., SoccerMinigameOutcome]


def _parse_selection_strategy(value: str) -> SelectionStrategy:
    """Parse strategy string to enum, defaulting to STRATIFIED."""
    value = value.lower().strip()
    for strat in SelectionStrategy:
        if strat.value == value:
            return strat
    return SelectionStrategy.STRATIFIED


@dataclass
class SoccerMinigameScheduler:
    """Runs soccer minigames on a deterministic schedule."""

    config: SoccerConfig
    step_batch: int = 5
    match_runner: MatchRunner | None = None
    _match_counter: int = 0
    _cooldown_map: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.match_runner is None:
            self.match_runner = self._run_match

    def _get_cooldown_ids(self) -> frozenset[int]:
        """Get IDs of fish currently in cooldown."""
        return frozenset(
            fish_id
            for fish_id, eligible_at in self._cooldown_map.items()
            if self._match_counter < eligible_at
        )

    def _add_to_cooldown(self, fish_ids: list[int]) -> None:
        """Add fish to cooldown after a match."""
        cooldown_matches = getattr(self.config, "cooldown_matches", 3)
        if cooldown_matches <= 0:
            return
        eligible_at = self._match_counter + cooldown_matches
        for fish_id in fish_ids:
            self._cooldown_map[fish_id] = eligible_at

    def _cleanup_cooldown(self) -> None:
        """Remove expired cooldown entries to prevent memory growth."""
        self._cooldown_map = {
            fish_id: eligible_at
            for fish_id, eligible_at in self._cooldown_map.items()
            if self._match_counter < eligible_at
        }

    def tick(
        self,
        world_state: Any,
        seed_base: int | None,
        cycle: int,
    ) -> list[SoccerMinigameOutcome]:
        """Run scheduled soccer matches if conditions are met."""
        if not self.config.enabled:
            return []

        match_every_frames = getattr(self.config, "match_every_frames", None)
        if match_every_frames is None:
            match_every_frames = self.config.interval_frames
        if match_every_frames <= 0:
            return []
        if cycle % match_every_frames != 0:
            return []

        matches_per_tick = max(0, int(getattr(self.config, "matches_per_tick", 1)))
        if matches_per_tick <= 0:
            return []

        candidates = self._get_candidates(world_state)
        has_min_candidates = len(candidates) >= self.config.min_players

        # Parse selection strategy from config
        strategy_str = getattr(self.config, "selection_strategy", "stratified")
        strategy = _parse_selection_strategy(strategy_str)

        # Resolve seed base deterministically
        effective_seed_base = getattr(self.config, "seed_base", None)
        if effective_seed_base is None:
            effective_seed_base = seed_base
        if effective_seed_base is None:
            effective_seed_base = 0

        outcomes: list[SoccerMinigameOutcome] = []
        match_runner = self.match_runner or self._run_match

        for _ in range(matches_per_tick):
            num_players = self._get_num_players()
            selection_seed = derive_soccer_seed(
                int(effective_seed_base), self._match_counter, "selection"
            )
            match_seed = derive_soccer_seed(int(effective_seed_base), self._match_counter, "match")
            match_id = f"soccer_{match_seed}_{self._match_counter}"

            cooldown_ids = self._get_cooldown_ids()
            if not has_min_candidates:
                outcome = self._build_skip_outcome(
                    match_id=match_id,
                    match_counter=self._match_counter,
                    match_seed=match_seed,
                    selection_seed=selection_seed,
                    reason="not_enough_candidates",
                )
            else:
                try:
                    outcome = match_runner(
                        candidates,
                        num_players=num_players,
                        duration_frames=self.config.duration_frames,
                        code_source=getattr(world_state, "genome_code_pool", None),
                        seed_base=effective_seed_base,
                        match_counter=self._match_counter,
                        step_batch=self.step_batch,
                        strategy=strategy,
                        cooldown_ids=cooldown_ids,
                        selection_seed=selection_seed,
                        match_seed=match_seed,
                        match_id=match_id,
                        allow_repeat_within_match=getattr(
                            self.config, "allow_repeat_within_match", False
                        ),
                        entry_fee_energy=getattr(self.config, "entry_fee_energy", 0.0),
                        reward_mode=getattr(self.config, "reward_mode", "pot_payout"),
                        reward_multiplier=getattr(self.config, "reward_multiplier", 1.0),
                        repro_reward_mode=getattr(self.config, "repro_reward_mode", "credits"),
                        repro_credit_award=getattr(self.config, "repro_credit_award", 0.0),
                    )
                except ValueError:
                    outcome = self._build_skip_outcome(
                        match_id=match_id,
                        match_counter=self._match_counter,
                        match_seed=match_seed,
                        selection_seed=selection_seed,
                        reason="selection_failed",
                    )

            outcomes.append(outcome)

            # Track which fish played for cooldown
            if not outcome.skipped:
                played_ids = []
                for team in outcome.teams.values():
                    played_ids.extend(team)
                self._add_to_cooldown(played_ids)

            self._match_counter += 1
            self._cleanup_cooldown()

        return outcomes

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

    def _run_match(
        self,
        candidates: Sequence[Any],
        *,
        num_players: int,
        duration_frames: int,
        code_source: Any | None,
        seed_base: int | None,
        match_counter: int,
        step_batch: int,
        strategy: SelectionStrategy = SelectionStrategy.STRATIFIED,
        cooldown_ids: frozenset[int] = frozenset(),
        selection_seed: int | None = None,
        match_seed: int | None = None,
        match_id: str | None = None,
        allow_repeat_within_match: bool = False,
        entry_fee_energy: float = 0.0,
        reward_mode: str = "pot_payout",
        reward_multiplier: float = 1.0,
        repro_reward_mode: str = "credits",
        repro_credit_award: float = 0.0,
    ) -> SoccerMinigameOutcome:
        # Select participants with new strategy
        selected = select_soccer_participants(
            candidates,
            num_players,
            strategy=strategy,
            cooldown_ids=cooldown_ids,
            seed=selection_seed,
            allow_repeat_within_match=allow_repeat_within_match,
            entry_fee_energy=entry_fee_energy,
        )
        if len(selected) != num_players:
            match_id_str = match_id or f"soccer_{match_seed or 0}_{match_counter}"
            return self._build_skip_outcome(
                match_id=match_id_str,
                match_counter=match_counter,
                match_seed=match_seed,
                selection_seed=selection_seed,
                reason="not_enough_eligible",
            )

        setup = create_soccer_match_from_participants(
            selected,
            duration_frames=duration_frames,
            code_source=code_source,
            seed=match_seed,
            match_id=match_id,
            match_counter=match_counter,
            selection_seed=selection_seed,
            entry_fee_energy=entry_fee_energy,
        )
        match = setup.match

        while not match.game_over:
            match.step(num_steps=step_batch)

        return finalize_soccer_match(
            match,
            seed=setup.seed,
            match_counter=match_counter,
            selection_seed=selection_seed,
            entry_fees=setup.entry_fees,
            reward_mode=reward_mode,
            reward_multiplier=reward_multiplier,
            repro_reward_mode=repro_reward_mode,
            repro_credit_award=repro_credit_award,
        )

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
