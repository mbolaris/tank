"""Tests for scheduled soccer minigame evaluation."""

from __future__ import annotations

from typing import Any, Sequence

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import (
    SoccerMinigameOutcome,
    create_soccer_match,
    finalize_soccer_match,
    select_soccer_participants,
)
from core.minigames.soccer.scheduler import SoccerMinigameScheduler


class DummyFish:
    """Minimal fish stub for scheduler tests."""

    def __init__(self, fish_id: int, energy: float, max_energy: float) -> None:
        self.fish_id = fish_id
        self.energy = energy
        self.max_energy = max_energy
        self.genome = None
        self.calls: list[tuple[float, str]] = []

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        applied = min(amount, self.max_energy - self.energy)
        self.energy += applied
        self.calls.append((applied, source))
        return applied


class DummyEngine:
    """Lightweight engine stub for scheduler tests."""

    def __init__(self, fish: Sequence[DummyFish]) -> None:
        self._fish = list(fish)
        self.genome_code_pool = None

    def get_fish_list(self) -> list[DummyFish]:
        return list(self._fish)


def test_scheduler_deterministic_selection() -> None:
    """Same seed + world snapshot yields identical scheduling output."""
    fish = [
        DummyFish(1, energy=10.0, max_energy=100.0),
        DummyFish(2, energy=50.0, max_energy=100.0),
        DummyFish(3, energy=30.0, max_energy=100.0),
        DummyFish(4, energy=20.0, max_energy=100.0),
    ]
    engine = DummyEngine(fish)

    def fake_match_runner(
        candidates: Sequence[Any],
        *,
        num_players: int,
        duration_frames: int,
        code_source: Any | None,
        seed_base: int | None,
        match_counter: int,
        step_batch: int,
    ) -> SoccerMinigameOutcome:
        selected = select_soccer_participants(candidates, num_players)
        half = len(selected) // 2
        left = [player.fish_id for player in selected[:half]]
        right = [player.fish_id for player in selected[half:]]
        seed = None
        if seed_base is not None:
            seed = (int(seed_base) + int(match_counter)) & 0xFFFFFFFF
        match_id = f"soccer_{seed}_{match_counter}"
        return SoccerMinigameOutcome(
            match_id=match_id,
            winner_team=None,
            score_left=0,
            score_right=0,
            frames=duration_frames,
            seed=seed,
            message="",
            rewarded={},
            teams={"left": left, "right": right},
        )

    config = SoccerConfig(
        enabled=True,
        interval_frames=2,
        min_players=2,
        num_players=4,
        duration_frames=1,
    )

    scheduler_a = SoccerMinigameScheduler(config, match_runner=fake_match_runner)
    scheduler_b = SoccerMinigameScheduler(config, match_runner=fake_match_runner)

    outcome_a = scheduler_a.tick(engine, seed_base=123, cycle=2)
    outcome_b = scheduler_b.tick(engine, seed_base=123, cycle=2)

    assert outcome_a is not None
    assert outcome_b is not None
    assert outcome_a.match_id == outcome_b.match_id
    assert outcome_a.teams == outcome_b.teams
    assert outcome_a.teams["left"] + outcome_a.teams["right"] == [2, 3, 4, 1]


def test_scheduler_applies_rewards_to_winners() -> None:
    """Scheduler outcomes use the energy ledger for winners."""
    left = DummyFish(10, energy=25.0, max_energy=100.0)
    right = DummyFish(20, energy=20.0, max_energy=100.0)
    engine = DummyEngine([left, right])

    def forced_win_runner(
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
        match.winner_team = "left"
        match.game_over = True
        return finalize_soccer_match(match, seed=setup.seed)

    config = SoccerConfig(
        enabled=True,
        interval_frames=1,
        min_players=2,
        num_players=2,
        duration_frames=1,
    )

    scheduler = SoccerMinigameScheduler(config, match_runner=forced_win_runner)
    outcome = scheduler.tick(engine, seed_base=7, cycle=1)

    assert outcome is not None
    assert outcome.winner_team == "left"
    assert left.energy == 100.0
    assert right.energy == 20.0
    assert left.calls == [(75.0, "soccer_win")]
    assert right.calls == []
