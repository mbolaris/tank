"""Tests for IncrementalSoccerLadderEvaluator: determinism, isolation, and incremental execution."""

from __future__ import annotations

import random


from core.code_pool import create_default_genome_code_pool, default_soccer_policy_params
from core.config.simulation_config import SimulationConfig
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from core.minigames.soccer.reference_teams import register_reference_policies
from core.skill.live_soccer_evaluator import IncrementalSoccerLadderEvaluator
from core.skill.snapshots import SkillSnapshotStore


class MockFish:
    """Mock Fish entity for evaluator tests."""

    def __init__(self, fish_id: int, energy: float = 100.0, generation: int = 1) -> None:
        self.fish_id = fish_id
        self.energy = energy
        self.generation = generation
        self.parent_id = 0

        pool = create_default_genome_code_pool()
        register_reference_policies(pool)
        default_id = pool.get_default("soccer_policy")

        rng = random.Random(fish_id)
        self.genome = Genome.random(use_algorithm=False, rng=rng)
        self.genome.behavioral.soccer_policy_id = GeneticTrait(default_id)
        self.genome.behavioral.soccer_policy_params = GeneticTrait(
            default_soccer_policy_params(default_id)
        )

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        self.energy += amount
        return amount


class MockEntityManager:

    def __init__(self, fish_list: list[MockFish]) -> None:
        self._fish = fish_list

    def get_fish(self) -> list[MockFish]:
        return list(self._fish)


class MockEngine:

    def __init__(self, seed: int = 42, fish_count: int = 6) -> None:
        self.seed = seed
        self.frame_count = 0
        self.config = SimulationConfig.production(headless=True)
        self.config.server.soccer_ladder_eval_enabled = True
        self.config.server.soccer_ladder_eval_interval_frames = 100

        self.rng = random.Random(seed)
        self.fish = [MockFish(i + 1, energy=100.0 + i) for i in range(fish_count)]
        self._entity_manager = MockEntityManager(self.fish)
        self.soccer_events = None


def test_evaluator_determinism() -> None:
    """Evaluating identical genomes with the same seed produces identical scores."""
    store1 = SkillSnapshotStore()
    eval1 = IncrementalSoccerLadderEvaluator(
        store=store1,
        eval_interval_frames=10,
        n_seeds=1,
        frames_per_match=30,
        team_size=3,
    )
    engine1 = MockEngine(seed=42, fish_count=6)

    store2 = SkillSnapshotStore()
    eval2 = IncrementalSoccerLadderEvaluator(
        store=store2,
        eval_interval_frames=10,
        n_seeds=1,
        frames_per_match=30,
        team_size=3,
    )
    engine2 = MockEngine(seed=42, fish_count=6)

    # Run pass on both
    for frame in range(1, 600):
        engine1.frame_count = frame
        eval1.tick(engine1)

        engine2.frame_count = frame
        eval2.tick(engine2)

    snaps1 = store1.get_snapshots()
    snaps2 = store2.get_snapshots()

    assert len(snaps1) >= 1
    assert len(snaps2) >= 1

    s1 = snaps1[0]
    s2 = snaps2[0]

    assert s1.summary.skill_index == s2.summary.skill_index
    assert s1.summary.rungs_beaten == s2.summary.rungs_beaten
    assert eval1.latest_baseline_score_diff == eval2.latest_baseline_score_diff


def test_ecosystem_isolation_energy_and_rng() -> None:
    """Proof that evaluator consumption does NOT touch fish energy or engine RNG."""
    # Control engine: evaluator disabled
    control_engine = MockEngine(seed=123, fish_count=6)
    control_engine.config.server.soccer_ladder_eval_enabled = False

    # Test engine: evaluator enabled
    test_store = SkillSnapshotStore()
    test_evaluator = IncrementalSoccerLadderEvaluator(
        store=test_store,
        eval_interval_frames=10,
        n_seeds=1,
        frames_per_match=20,
        team_size=3,
    )
    test_engine = MockEngine(seed=123, fish_count=6)
    test_engine.config.server.soccer_ladder_eval_enabled = True

    # Record initial energy levels
    initial_control_energies = [f.energy for f in control_engine.fish]
    initial_test_energies = [f.energy for f in test_engine.fish]

    # Tick both engines over N frames, drawing RNG on control and test identically
    for frame in range(1, 400):
        control_engine.frame_count = frame
        _ = control_engine.rng.random()  # Simulate main loop RNG draw

        test_engine.frame_count = frame
        _ = test_engine.rng.random()  # Simulate main loop RNG draw
        test_evaluator.tick(test_engine)

    # 1. Energy check: fish energy must be 100% unchanged on test engine
    final_test_energies = [f.energy for f in test_engine.fish]
    assert final_test_energies == initial_test_energies
    assert final_test_energies == initial_control_energies

    # 2. Engine RNG check: random state on test_engine must match control_engine
    assert control_engine.rng.getstate() == test_engine.rng.getstate()

    # Verify that test_evaluator completed at least one evaluation snapshot
    assert len(test_store.get_snapshots()) >= 1


def test_incremental_execution_bounded_work() -> None:
    """Evaluator does bounded per-frame work without blocking loop stalls."""
    store = SkillSnapshotStore()
    evaluator = IncrementalSoccerLadderEvaluator(
        store=store,
        eval_interval_frames=5,
        n_seeds=1,
        frames_per_match=20,
        team_size=3,
        cycles_per_frame=1,
    )
    engine = MockEngine(seed=99, fish_count=6)
    engine.config.server.soccer_ladder_eval_interval_frames = 5

    # Tick once to start evaluation

    engine.frame_count = 5
    evaluator.tick(engine)
    assert evaluator.active is True

    # Check active match status
    assert evaluator._active_match is not None
    initial_match_frame = evaluator._active_match.current_frame

    # Tick one frame -> should step match by exactly 1 cycle
    engine.frame_count = 6
    evaluator.tick(engine)

    if evaluator._active_match is not None:
        assert evaluator._active_match.current_frame == initial_match_frame + 1


def test_top_unbeaten_rung_baseline_diff_calculation() -> None:
    """Goal diff vs top unbeaten rung is calculated correctly."""
    store = SkillSnapshotStore()
    evaluator = IncrementalSoccerLadderEvaluator(
        store=store,
        eval_interval_frames=10,
        n_seeds=1,
        frames_per_match=15,
        team_size=3,
    )
    engine = MockEngine(seed=77, fish_count=6)

    # Run until at least one snapshot completes
    for frame in range(1, 500):
        engine.frame_count = frame
        evaluator.tick(engine)
        if store.get_snapshots():
            break

    snaps = store.get_snapshots()
    assert len(snaps) == 1
    snap = snaps[0]

    # Verify summary fields
    summary = snap.summary
    assert summary.domain == "soccer"
    assert len(summary.rungs) == 4

    # Top unbeaten rung logic verification
    top_unbeaten_diff = None
    for r in summary.rungs:
        if not r.beaten:
            top_unbeaten_diff = r.metric
            break
    if top_unbeaten_diff is None and summary.rungs:
        top_unbeaten_diff = summary.rungs[-1].metric

    assert evaluator.latest_baseline_score_diff == top_unbeaten_diff
