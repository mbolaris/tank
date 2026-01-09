"""Scheduled soccer minigame evaluator for Tank-like worlds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import (
    SoccerMinigameOutcome,
    create_soccer_match,
    finalize_soccer_match,
)

MatchRunner = Callable[..., SoccerMinigameOutcome]


@dataclass
class SoccerMinigameScheduler:
    """Runs soccer minigames on a deterministic schedule."""

    config: SoccerConfig
    step_batch: int = 5
    match_runner: MatchRunner | None = None
    _match_counter: int = 0

    def __post_init__(self) -> None:
        if self.match_runner is None:
            self.match_runner = self._run_match

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

        try:
            outcome = self.match_runner(
                candidates,
                num_players=self.config.num_players,
                duration_frames=self.config.duration_frames,
                code_source=getattr(world_state, "genome_code_pool", None),
                seed_base=seed_base,
                match_counter=self._match_counter,
                step_batch=self.step_batch,
            )
        except ValueError:
            return None

        self._match_counter += 1
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
    ) -> SoccerMinigameOutcome:
        setup = create_soccer_match(
            candidates,
            num_players=num_players,
            duration_frames=duration_frames,
            code_source=code_source,
            seed_base=seed_base,
            match_counter=match_counter,
        )
        match = setup.match

        while not match.game_over:
            match.step(num_steps=step_batch)

        return finalize_soccer_match(match, seed=setup.seed)
