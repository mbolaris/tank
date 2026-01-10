"""Scheduled soccer minigame evaluator for Tank-like worlds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import (
    SelectionStrategy,
    SoccerMinigameOutcome,
    create_soccer_match,
    finalize_soccer_match,
    select_soccer_participants,
    _get_entity_id,
)

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
    ) -> SoccerMinigameOutcome | None:
        """Run a scheduled soccer match if conditions are met."""
        if not self.config.enabled:
            return None
        if self.config.interval_frames <= 0:
            return None
        if cycle % self.config.interval_frames != 0:
            return None

        candidates = self._get_candidates(world_state)
        if len(candidates) < self.config.min_players:
            return None

        # Parse selection strategy from config
        strategy_str = getattr(self.config, "selection_strategy", "stratified")
        strategy = _parse_selection_strategy(strategy_str)

        # Compute selection seed deterministically
        selection_seed = None
        if seed_base is not None:
            selection_seed = (int(seed_base) + self._match_counter * 7919) & 0xFFFFFFFF

        # Get cooldown exclusions
        cooldown_ids = self._get_cooldown_ids()

        try:
            outcome = self.match_runner(
                candidates,
                num_players=self.config.num_players,
                duration_frames=self.config.duration_frames,
                code_source=getattr(world_state, "genome_code_pool", None),
                seed_base=seed_base,
                match_counter=self._match_counter,
                step_batch=self.step_batch,
                strategy=strategy,
                cooldown_ids=cooldown_ids,
                selection_seed=selection_seed,
            )
        except ValueError:
            return None

        # Track which fish played for cooldown
        if outcome is not None:
            played_ids = []
            for team in outcome.teams.values():
                played_ids.extend(team)
            self._add_to_cooldown(played_ids)

        self._match_counter += 1
        self._cleanup_cooldown()
        return outcome

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
    ) -> SoccerMinigameOutcome:
        # Select participants with new strategy
        selected = select_soccer_participants(
            candidates,
            num_players,
            strategy=strategy,
            cooldown_ids=cooldown_ids,
            seed=selection_seed,
        )
        if len(selected) < 2:
            raise ValueError("Not enough participants after selection")

        setup = create_soccer_match(
            selected,
            num_players=len(selected),  # Use actual selected count
            duration_frames=duration_frames,
            code_source=code_source,
            seed_base=seed_base,
            match_counter=match_counter,
        )
        match = setup.match

        while not match.game_over:
            match.step(num_steps=step_batch)

        return finalize_soccer_match(match, seed=setup.seed)
