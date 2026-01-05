from __future__ import annotations

from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder
from core.config.entities import (
    FOOD_ID_OFFSET,
    NECTAR_ID_OFFSET,
)
from core.entities.plant import PlantNectar
from core.entities.resources import Food
from core.math_utils import Vector2


def _make_minimal_food(x: float = 10, y: float = 20) -> Food:
    food = Food.__new__(Food)
    food.pos = Vector2(x, y)
    food.vel = Vector2(0, 0)
    food.width = 5
    food.height = 5
    food.food_type = "algae"
    return food


def _make_minimal_nectar(x: float = 30, y: float = 40) -> PlantNectar:
    nectar = PlantNectar.__new__(PlantNectar)
    nectar.pos = Vector2(x, y)
    nectar.vel = Vector2(0, 0)
    nectar.width = 3
    nectar.height = 3
    nectar.energy = 50.0
    nectar.source_plant = None
    return nectar


def test_food_stable_id_is_consistent_for_same_object() -> None:
    builder = TankSnapshotBuilder()
    food = _make_minimal_food()

    snap1 = builder.to_snapshot(food)
    snap2 = builder.to_snapshot(food)

    assert snap1 is not None
    assert snap2 is not None
    assert snap1.type == "food"
    assert snap1.id == snap2.id
    assert snap1.id >= FOOD_ID_OFFSET


def test_food_stable_id_increments_for_new_objects() -> None:
    builder = TankSnapshotBuilder()
    food1 = _make_minimal_food()
    food2 = _make_minimal_food()

    snap1 = builder.to_snapshot(food1)
    snap2 = builder.to_snapshot(food2)

    assert snap1 is not None
    assert snap2 is not None
    assert snap1.id == FOOD_ID_OFFSET
    assert snap2.id == FOOD_ID_OFFSET + 1


def test_nectar_stable_id_uses_nectar_offset() -> None:
    builder = TankSnapshotBuilder()
    nectar = _make_minimal_nectar()

    snap = builder.to_snapshot(nectar)

    assert snap is not None
    assert snap.type == "plant_nectar"
    assert snap.id == NECTAR_ID_OFFSET


def test_collect_prunes_stale_ids() -> None:
    builder = TankSnapshotBuilder()
    food = _make_minimal_food()

    snap1 = builder.collect([food])[0]
    assert snap1.id == FOOD_ID_OFFSET

    # Remove from "world" and collect again to prune stable IDs.
    builder.collect([])

    # If this object ever re-enters collection, it should get a new stable ID.
    snap2 = builder.collect([food])[0]
    assert snap2.id > snap1.id
