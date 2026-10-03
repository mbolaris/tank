"""Persisted skill evidence has a run identity and comparable segments."""

from types import SimpleNamespace

import pytest

from backend.foraging_history import ForagingHistory, config_identity, evaluator_identity
from backend.runner_stores import capture_runner_stores, restore_runner_stores
from backend.skill_evaluation_service import SkillEvaluationService
from backend.skill_progress_service import SkillProgressService


def result(history, frame=10, score=0.5, **extra):
    return {
        "status": "success",
        "world_id": history.world_id,
        "run_id": history.run_id,
        "evaluator_identity": evaluator_identity(),
        "config_identity": config_identity({}),
        "benchmark_hash": "ruler-1",
        "evaluated_at_frame": frame,
        "evaluated_at_generation": frame // 10,
        "tank_average": score,
        "wandering_mean": 0.1,
        "perfect_mean": 1.0,
        **extra,
    }


def manager(history):
    runner = SimpleNamespace(
        foraging_history=history, world=SimpleNamespace(simulation_config={}), frame_count=100
    )
    instance = SimpleNamespace(runner=runner)
    return SimpleNamespace(
        get_world=lambda world_id: instance if world_id == history.world_id else None
    )


def test_save_reload_preserves_verdict_idempotently():
    first = ForagingHistory("w1")
    for frame in range(10, 100, 10):
        first.record(result(first, frame, score=frame / 110))
    saved = {}
    capture_runner_stores(SimpleNamespace(foraging_history=first), saved)
    restored = ForagingHistory("w1")
    runner = SimpleNamespace(foraging_history=restored)
    restore_runner_stores(runner, saved)
    restore_runner_stores(runner, saved)
    assert restored.run_id == first.run_id
    assert restored.to_payload() == first.to_payload()
    assert SkillProgressService(manager(restored)).assess("w1") == SkillProgressService(
        manager(first)
    ).assess("w1")
    restored.record(result(restored, 90))
    assert len(restored.records) == 9


def test_reset_and_late_completion_cannot_mix_runs(tmp_path):
    history = ForagingHistory("w1")
    old = result(history)
    history.record(old)
    service = SkillEvaluationService(manager(history), storage_path=tmp_path / "latest.json")
    service.store_result("w1", old)
    history.start_run()
    assert service.get_latest("w1") is None
    service.store_result("w1", old)
    assert service.get_latest("w1") is None
    history.record(old)
    assert history.comparable() == []
    history.record(result(history))
    assert len(history.records) == 2
    progress = SkillProgressService(manager(history))
    assert len(progress.foraging_observations("w1")) == 1
    assert progress.evidence_metadata("w1")["series_breaks"] == 1


def test_changed_ruler_or_config_begins_a_segment():
    history = ForagingHistory("w1")
    history.record(result(history))
    history.record(result(history, 20, benchmark_hash="ruler-2"))
    assert len(history.comparable()) == 1
    history.record(result(history, 30, config_identity=config_identity({"changed": True})))
    assert SkillProgressService(manager(history)).foraging_observations("w1") == []
    history.record(result(history, 40, evaluator_identity="old-code"))
    assert history.comparable() == []


@pytest.mark.parametrize(
    "bad",
    [{}, {"schema_version": 1, "run_id": "old", "records": "truncated"}, {"schema_version": 0}],
)
def test_old_or_truncated_payloads_are_visible_unknown(bad):
    history = ForagingHistory("w1")
    history.load(bad)
    assert history.comparable() == []
    assert history.unknown_records == 1


def test_storage_is_bounded_and_failed_evaluation_is_absence():
    history = ForagingHistory("w1")
    for frame in range(100):
        history.record(result(history, frame, large_unused_data="x" * 1000))
    assert len(history.records) == 60
    assert "large_unused_data" not in history.records[-1]
    history.record(result(history, 101, status="failed"))
    history.record(result(history, 102, tank_average=float("nan")))
    assert history.records[-1]["evaluated_at_frame"] == 99


def test_real_world_save_restore_keeps_run_and_samples():
    from backend.simulation_runner import SimulationRunner
    from backend.world_persistence import (
        load_snapshot,
        restore_world_from_snapshot,
        save_world_state,
    )

    first = SimulationRunner(seed=42, world_id="persisted-skill")
    history = first.foraging_history
    history.record(result(history, config_identity=config_identity(first.world.config)))
    path = save_world_state(first.world_id, first)
    assert path is not None
    saved = load_snapshot(path)
    assert saved is not None
    restored = SimulationRunner(seed=42, world_id=first.world_id)
    assert restore_world_from_snapshot(saved, restored.world)
    assert restored.foraging_history.to_payload() == history.to_payload()


def test_loaded_unknown_count_and_duplicate_identity_remain_honest():
    history = ForagingHistory("w1")
    row = result(history)
    history.load(
        {
            "schema_version": 1,
            "run_id": history.run_id,
            "unknown_records": 2,
            "records": [row, {**row, "tank_average": 0.8}],
        }
    )
    assert len(history.records) == 1
    assert history.unknown_records == 2
