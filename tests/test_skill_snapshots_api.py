"""Tests for live skill snapshots backend API and persistence integration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app_factory import create_app
from core.skill.ladder import RungResult, SkillLadderSummary
from core.skill.snapshots import SkillSnapshot, SkillSnapshotStore


def _make_sample_snapshot(skill_index: float = 50.0) -> SkillSnapshot:
    rungs = [
        RungResult(rung="L0", rung_id="stationary_v1", metric=2.0, beaten=True),
        RungResult(rung="L1", rung_id="random_walk_v1", metric=1.0, beaten=True),
        RungResult(rung="L2", rung_id="chase_shoot_v1", metric=-0.4, beaten=False),
        RungResult(rung="L3", rung_id="formation_v1", metric=-1.2, beaten=False),
    ]
    summary = SkillLadderSummary(
        domain="soccer",
        benchmark_id="soccer/ladder_live",
        metric_name="goal_diff_per_match",
        skill_index=skill_index,
        rungs=tuple(rungs),
    )
    return SkillSnapshot(
        domain="soccer",
        generation=3,
        frame=5000,
        subject_fish_ids=[1, 2, 3],
        subject_lineage_ids=["1", "2", "3"],
        summary=summary,
        previous_score=25.0,
        personal_best=50.0,
        tank_best=50.0,
        sample_size=24,
    )


def test_get_skill_snapshots_api_endpoint() -> None:
    """GET /api/skill/snapshots returns JSON shape matching specs."""
    app = create_app(production_mode=False)
    with TestClient(app) as client:
        # Call endpoint for default world
        res = client.get("/api/skill/snapshots")
        assert res.status_code == 200

        data = res.json()
        assert "schema_version" in data
        assert "world_id" in data
        assert "count" in data
        assert "tank_best" in data
        assert "snapshots" in data
        assert isinstance(data["snapshots"], list)


def test_snapshot_store_persistence_serialization() -> None:
    """Test saving and restoring SkillSnapshotStore state via world persistence functions."""
    store = SkillSnapshotStore()
    snap = _make_sample_snapshot(75.0)
    store.add_snapshot(snap)

    data = store.to_dict()

    restored_store = SkillSnapshotStore.from_dict(data)
    assert restored_store.tank_best == 75.0
    snaps = restored_store.get_snapshots()
    assert len(snaps) == 1
    assert snaps[0].summary.skill_index == 75.0
    assert snaps[0].subject_fish_ids == [1, 2, 3]
