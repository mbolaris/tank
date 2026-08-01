"""Tests for SkillSnapshot and SkillSnapshotStore."""

from __future__ import annotations

from dataclasses import replace

from core.skill.ladder import RungResult, SkillLadderSummary
from core.skill.snapshots import SkillSnapshot, SkillSnapshotStore


def _make_dummy_summary(skill_index: float, beaten_count: int = 1) -> SkillLadderSummary:
    rungs = [
        RungResult(rung="L0", rung_id="stationary_v1", metric=1.0, beaten=True),
        RungResult(rung="L1", rung_id="random_walk_v1", metric=0.5, beaten=beaten_count >= 2),
        RungResult(rung="L2", rung_id="chase_shoot_v1", metric=-0.2, beaten=beaten_count >= 3),
        RungResult(rung="L3", rung_id="formation_v1", metric=-1.5, beaten=beaten_count >= 4),
    ]
    return SkillLadderSummary(
        domain="soccer",
        benchmark_id="soccer/ladder_live",
        metric_name="goal_diff_per_match",
        skill_index=skill_index,
        rungs=tuple(rungs),
    )


def test_snapshot_store_bounding() -> None:
    """Test that SkillSnapshotStore caps history at MAX_SNAPSHOTS (50)."""
    store = SkillSnapshotStore(MAX_SNAPSHOTS=50)

    for i in range(70):
        snap = SkillSnapshot(
            domain="soccer",
            generation=i,
            frame=i * 1000,
            subject_fish_ids=[1, 2, 3],
            subject_lineage_ids=["1", "2", "3"],
            summary=_make_dummy_summary(float(i)),
            previous_score=float(i - 1) if i > 0 else None,
            personal_best=float(i),
            tank_best=float(i),
            sample_size=24,
        )
        store.add_snapshot(snap)

    snapshots = store.get_snapshots()
    assert len(snapshots) == 50
    # Oldest 20 (generations 0-19) should have been pruned
    assert snapshots[0].generation == 20
    assert snapshots[-1].generation == 69


def test_tank_best_tracking() -> None:
    """Test O(1) tank_best tracking."""
    store = SkillSnapshotStore()
    assert store.tank_best == 0.0

    store.add_snapshot(
        SkillSnapshot(
            domain="soccer",
            generation=1,
            frame=1000,
            subject_fish_ids=[1, 2, 3],
            subject_lineage_ids=["1", "2", "3"],
            summary=_make_dummy_summary(25.0),
            previous_score=None,
            personal_best=25.0,
            tank_best=25.0,
            sample_size=24,
        )
    )
    assert store.tank_best == 25.0

    # Lower score does not decrease tank_best
    store.add_snapshot(
        SkillSnapshot(
            domain="soccer",
            generation=2,
            frame=2000,
            subject_fish_ids=[4, 5, 6],
            subject_lineage_ids=["4", "5", "6"],
            summary=_make_dummy_summary(10.0),
            previous_score=25.0,
            personal_best=10.0,
            tank_best=25.0,
            sample_size=24,
        )
    )
    assert store.tank_best == 25.0

    # Higher score updates tank_best
    store.add_snapshot(
        SkillSnapshot(
            domain="soccer",
            generation=3,
            frame=3000,
            subject_fish_ids=[1, 2, 3],
            subject_lineage_ids=["1", "2", "3"],
            summary=_make_dummy_summary(50.0),
            previous_score=10.0,
            personal_best=50.0,
            tank_best=50.0,
            sample_size=24,
        )
    )
    assert store.tank_best == 50.0


def test_snapshot_capacity_is_per_domain() -> None:
    """Poker history must not evict the soccer history from S1."""
    store = SkillSnapshotStore(MAX_SNAPSHOTS=2)

    for domain in ("soccer", "poker"):
        for i in range(3):
            summary = replace(_make_dummy_summary(float(i)), domain=domain)
            store.add_snapshot(
                SkillSnapshot(
                    domain=domain,
                    generation=i,
                    frame=i,
                    subject_fish_ids=[i + 1],
                    subject_lineage_ids=[str(i)],
                    summary=summary,
                    previous_score=None,
                    personal_best=float(i),
                    tank_best=float(i),
                    sample_size=1,
                )
            )

    assert len(store.get_snapshots(domain="soccer")) == 2
    assert len(store.get_snapshots(domain="poker")) == 2
    assert store.get_tank_best("soccer") == 2.0
    assert store.get_tank_best("poker") == 2.0


def test_personal_best_tracking() -> None:
    """Test per-team personal best tracking."""
    store = SkillSnapshotStore()

    # Team A: [1, 2, 3] score 25.0
    snap_a1 = SkillSnapshot(
        domain="soccer",
        generation=1,
        frame=1000,
        subject_fish_ids=[1, 2, 3],
        subject_lineage_ids=["1", "2", "3"],
        summary=_make_dummy_summary(25.0),
        previous_score=None,
        personal_best=25.0,
        tank_best=25.0,
        sample_size=24,
    )
    store.add_snapshot(snap_a1)

    # Team B: [4, 5, 6] score 35.0
    snap_b = SkillSnapshot(
        domain="soccer",
        generation=1,
        frame=1000,
        subject_fish_ids=[4, 5, 6],
        subject_lineage_ids=["4", "5", "6"],
        summary=_make_dummy_summary(35.0),
        previous_score=25.0,
        personal_best=35.0,
        tank_best=35.0,
        sample_size=24,
    )
    store.add_snapshot(snap_b)

    # Order of fish IDs should not matter
    assert store.get_personal_best_for_team([1, 2, 3]) == 25.0
    assert store.get_personal_best_for_team([3, 1, 2]) == 25.0
    assert store.get_personal_best_for_team([4, 5, 6]) == 35.0
    assert store.get_personal_best_for_team([7, 8, 9]) == 0.0


def test_serialization_roundtrip() -> None:
    """Test to_dict / from_dict serialization roundtrip for store and snapshot."""
    store = SkillSnapshotStore()
    snap = SkillSnapshot(
        domain="soccer",
        generation=5,
        frame=10000,
        subject_fish_ids=[10, 20, 30],
        subject_lineage_ids=["10", "20", "30"],
        summary=_make_dummy_summary(75.0, beaten_count=3),
        previous_score=50.0,
        personal_best=75.0,
        tank_best=75.0,
        sample_size=24,
    )
    store.add_snapshot(snap)

    data = store.to_dict()
    restored_store = SkillSnapshotStore.from_dict(data)

    assert restored_store.tank_best == 75.0
    assert restored_store.get_personal_best_for_team([10, 20, 30]) == 75.0
    snapshots = restored_store.get_snapshots()
    assert len(snapshots) == 1

    r_snap = snapshots[0]
    assert r_snap.domain == "soccer"
    assert r_snap.generation == 5
    assert r_snap.frame == 10000
    assert r_snap.subject_fish_ids == [10, 20, 30]
    assert r_snap.previous_score == 50.0
    assert r_snap.personal_best == 75.0
    assert r_snap.tank_best == 75.0
    assert r_snap.summary.skill_index == 75.0
