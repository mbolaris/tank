"""Petri-specific snapshot builder that reuses tank entities.

This is a thin compatibility wrapper around TankSnapshotBuilder configured
for Petri's default view mode ("topdown"). Render hints are applied by the
mode-aware overlay inside TankSnapshotBuilder.
"""

from __future__ import annotations

from typing import Any, Iterable

from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder
from backend.state_payloads import EntitySnapshot


class PetriSnapshotBuilder:
    """Snapshot builder that adds Petri render hints to tank snapshots."""

    def __init__(self) -> None:
        self._tank_builder = TankSnapshotBuilder(view_mode="topdown")

    def collect(self, live_entities: Iterable[Any]) -> list[EntitySnapshot]:
        return self._tank_builder.collect(live_entities)

    def build(self, step_result: Any, world: Any) -> list[EntitySnapshot]:
        return self._tank_builder.build(step_result, world)

    def to_snapshot(self, entity: Any) -> EntitySnapshot | None:
        return self._tank_builder.to_snapshot(entity)
