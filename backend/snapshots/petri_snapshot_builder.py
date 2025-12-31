"""Petri-specific snapshot builder that reuses tank entities."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder
from backend.state_payloads import EntitySnapshot


_PETRI_HINTS = {
    "fish": {"style": "petri", "sprite": "microbe"},
    "food": {"style": "petri", "sprite": "nutrient"},
    "plant": {"style": "petri", "sprite": "colony"},
    "plant_nectar": {"style": "petri", "sprite": "nutrient"},
    "crab": {"style": "petri", "sprite": "predator"},
    "castle": {"style": "petri", "sprite": "inert"},
}


class PetriSnapshotBuilder:
    """Snapshot builder that adds Petri render hints to tank snapshots."""

    def __init__(self) -> None:
        self._tank_builder = TankSnapshotBuilder()

    def collect(self, live_entities: Iterable[Any]) -> List[EntitySnapshot]:
        snapshots = self._tank_builder.collect(live_entities)
        self._apply_hints(snapshots)
        return snapshots

    def build(self, step_result: Any, world: Any) -> List[EntitySnapshot]:
        snapshots = self._tank_builder.build(step_result, world)
        self._apply_hints(snapshots)
        return snapshots

    def to_snapshot(self, entity: Any) -> Optional[EntitySnapshot]:
        snapshot = self._tank_builder.to_snapshot(entity)
        if snapshot is None:
            return None
        self._apply_hint(snapshot)
        return snapshot

    def _apply_hints(self, snapshots: Iterable[EntitySnapshot]) -> None:
        for snapshot in snapshots:
            self._apply_hint(snapshot)

    def _apply_hint(self, snapshot: EntitySnapshot) -> None:
        hint = _PETRI_HINTS.get(snapshot.type)
        if hint is not None:
            snapshot.render_hint = dict(hint)
