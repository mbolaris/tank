"""Persistence and idempotency contracts for Soccer PR 3 breakthroughs."""

from __future__ import annotations

from core.skill.snapshots import BreakthroughRecord, SkillSnapshotStore


def test_breakthroughs_are_idempotent_and_persisted() -> None:
    store = SkillSnapshotStore()
    record = BreakthroughRecord(
        event_id="tank-team_skill_record-200",
        kind="team_skill_record",
        source_id="tank",
        frame=200,
        detail={"skill_index": 75.0, "previous_best": 50.0},
    )

    assert store.add_breakthrough(record) is True
    assert store.add_breakthrough(record) is False

    restored = SkillSnapshotStore.from_dict(store.to_dict())
    assert restored.get_breakthroughs() == [record]
