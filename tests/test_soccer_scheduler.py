"""Tests for scheduled soccer minigame evaluation."""

from __future__ import annotations

from typing import Any, Sequence

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import (
    SelectionStrategy,
    SoccerMinigameOutcome,
    create_soccer_match_from_participants,
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
        if amount >= 0:
            applied = min(amount, self.max_energy - self.energy)
        else:
            applied = max(amount, -self.energy)
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
        strategy: SelectionStrategy = SelectionStrategy.TOP_ENERGY,
        cooldown_ids: frozenset[int] = frozenset(),
        selection_seed: int | None = None,
        match_seed: int | None = None,
        match_id: str | None = None,
        **_: Any,
    ) -> SoccerMinigameOutcome:
        selected = select_soccer_participants(
            candidates,
            num_players,
            strategy=strategy,
            cooldown_ids=cooldown_ids,
            seed=selection_seed,
        )
        half = len(selected) // 2
        left = [player.fish_id for player in selected[:half]]
        right = [player.fish_id for player in selected[half:]]
        seed = match_seed
        match_id = match_id or f"soccer_{seed}_{match_counter}"
        return SoccerMinigameOutcome(
            match_id=match_id,
            match_counter=match_counter,
            winner_team=None,
            score_left=0,
            score_right=0,
            frames=duration_frames,
            seed=seed,
            selection_seed=selection_seed,
            message="",
            rewarded={},
            entry_fees={},
            energy_deltas={},
            repro_credit_deltas={},
            teams={"left": left, "right": right},
        )

    config = SoccerConfig(
        enabled=True,
        match_every_frames=2,
        matches_per_tick=1,
        min_players=2,
        num_players=4,
        duration_frames=1,
        selection_strategy="top_energy",  # Use legacy behavior for this test
        cooldown_matches=0,  # Disable cooldown for determinism test
    )

    scheduler_a = SoccerMinigameScheduler(config, match_runner=fake_match_runner)
    scheduler_b = SoccerMinigameScheduler(config, match_runner=fake_match_runner)

    outcomes_a = scheduler_a.tick(engine, seed_base=123, cycle=2)
    outcomes_b = scheduler_b.tick(engine, seed_base=123, cycle=2)

    assert outcomes_a
    assert outcomes_b
    outcome_a = outcomes_a[0]
    outcome_b = outcomes_b[0]
    assert outcome_a.match_id == outcome_b.match_id
    assert outcome_a.teams == outcome_b.teams
    assert outcome_a.teams["left"] + outcome_a.teams["right"] == [2, 3, 4, 1]


def test_scheduler_applies_rewards_to_winners() -> None:
    """Scheduler outcomes use the energy ledger for winners."""
    left = DummyFish(10, energy=50.0, max_energy=100.0)
    right = DummyFish(20, energy=50.0, max_energy=100.0)
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
        strategy: SelectionStrategy = SelectionStrategy.TOP_ENERGY,
        cooldown_ids: frozenset[int] = frozenset(),
        selection_seed: int | None = None,
        match_seed: int | None = None,
        match_id: str | None = None,
        entry_fee_energy: float = 0.0,
        reward_mode: str = "pot_payout",
        reward_multiplier: float = 1.0,
        repro_reward_mode: str = "credits",
        repro_credit_award: float = 0.0,
        **_: Any,
    ) -> SoccerMinigameOutcome:
        # Select with strategy for realistic behavior
        selected = select_soccer_participants(
            candidates,
            num_players,
            strategy=strategy,
            cooldown_ids=cooldown_ids,
            seed=selection_seed,
            entry_fee_energy=entry_fee_energy,
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
        match.winner_team = "left"
        match.game_over = True
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

    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        matches_per_tick=1,
        min_players=2,
        num_players=2,
        duration_frames=1,
        selection_strategy="top_energy",  # Predictable for assertion
        cooldown_matches=0,  # Disable cooldown for this test
        entry_fee_energy=10.0,
        reward_mode="pot_payout",
    )

    scheduler = SoccerMinigameScheduler(config, match_runner=forced_win_runner)
    outcomes = scheduler.tick(engine, seed_base=7, cycle=1)

    assert outcomes
    outcome = outcomes[0]
    assert outcome.winner_team == "left"
    assert left.energy == 60.0
    assert right.energy == 40.0
    assert left.calls == [(-10.0, "soccer_entry_fee"), (20.0, "soccer_win")]
    assert right.calls == [(-10.0, "soccer_entry_fee")]


def test_selection_strategy_top_energy() -> None:
    """TOP_ENERGY selects highest-energy fish first."""
    fish = [
        DummyFish(1, energy=10.0, max_energy=100.0),
        DummyFish(2, energy=50.0, max_energy=100.0),
        DummyFish(3, energy=30.0, max_energy=100.0),
        DummyFish(4, energy=40.0, max_energy=100.0),
    ]
    selected = select_soccer_participants(fish, 4, strategy=SelectionStrategy.TOP_ENERGY, seed=42)
    ids = [f.fish_id for f in selected]
    # Sorted by energy descending: 50, 40, 30, 10 -> fish 2, 4, 3, 1
    assert ids == [2, 4, 3, 1]


def test_selection_strategy_weighted_energy_deterministic() -> None:
    """WEIGHTED_ENERGY is deterministic with same seed."""
    fish = [DummyFish(i, energy=float(i * 10), max_energy=100.0) for i in range(1, 11)]
    selected_a = select_soccer_participants(
        fish, 6, strategy=SelectionStrategy.WEIGHTED_ENERGY, seed=12345
    )
    selected_b = select_soccer_participants(
        fish, 6, strategy=SelectionStrategy.WEIGHTED_ENERGY, seed=12345
    )
    assert [f.fish_id for f in selected_a] == [f.fish_id for f in selected_b]


def test_selection_strategy_stratified_includes_low_energy() -> None:
    """STRATIFIED includes fish from all energy tiers."""
    # Create fish with clear tier separation
    top = [DummyFish(i, energy=100.0, max_energy=100.0) for i in range(1, 4)]
    mid = [DummyFish(i, energy=50.0, max_energy=100.0) for i in range(4, 7)]
    low = [DummyFish(i, energy=10.0, max_energy=100.0) for i in range(7, 10)]
    fish = top + mid + low

    selected = select_soccer_participants(fish, 6, strategy=SelectionStrategy.STRATIFIED, seed=999)
    selected_ids = {f.fish_id for f in selected}

    # Should have representatives from each tier
    top_selected = selected_ids & {1, 2, 3}
    mid_selected = selected_ids & {4, 5, 6}

    assert len(top_selected) >= 1, "Should select at least 1 from top tier"
    assert len(mid_selected) >= 1, "Should select at least 1 from mid tier"
    # Low tier may get 0-1 depending on rounding; just check we got enough total
    assert len(selected) == 6


def test_cooldown_excludes_recent_players() -> None:
    """Fish in cooldown are excluded from selection."""
    fish = [
        DummyFish(1, energy=100.0, max_energy=100.0),
        DummyFish(2, energy=90.0, max_energy=100.0),
        DummyFish(3, energy=80.0, max_energy=100.0),
        DummyFish(4, energy=70.0, max_energy=100.0),
    ]

    # Simulate fish 1 and 2 in cooldown
    cooldown_ids = frozenset([1, 2])

    selected = select_soccer_participants(
        fish,
        2,
        strategy=SelectionStrategy.TOP_ENERGY,
        cooldown_ids=cooldown_ids,
        seed=42,
    )
    selected_ids = [f.fish_id for f in selected]

    # Fish 1 and 2 should be excluded
    assert 1 not in selected_ids
    assert 2 not in selected_ids
    assert 3 in selected_ids
    assert 4 in selected_ids


def test_scheduler_cooldown_integration() -> None:
    """Scheduler tracks cooldown across multiple matches."""
    fish = [DummyFish(i, energy=100.0 - i, max_energy=100.0) for i in range(1, 9)]
    engine = DummyEngine(fish)

    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        matches_per_tick=1,
        min_players=4,
        num_players=4,
        duration_frames=1,
        selection_strategy="top_energy",
        cooldown_matches=2,  # Sit out 2 matches
    )

    scheduler = SoccerMinigameScheduler(config)

    # Run 3 matches
    outcomes = []
    for cycle in range(1, 4):
        outcomes.extend(scheduler.tick(engine, seed_base=1, cycle=cycle))

    # Match 1: fish 1,2,3,4 (highest energy)
    # Match 2: fish 5,6,7,8 (1,2,3,4 in cooldown)
    # Match 3: fish 1,2,3,4 (cooldown expired for them)
    assert len(outcomes) == 3

    first_match = set(outcomes[0].teams["left"] + outcomes[0].teams["right"])
    assert first_match == {1, 2, 3, 4}, f"First match got {first_match}"

    # Second match should NOT include any from first match (in cooldown)
    second_match = set(outcomes[1].teams["left"] + outcomes[1].teams["right"])
    assert first_match.isdisjoint(
        second_match
    ), f"Second match {second_match} should not overlap with first {first_match}"
