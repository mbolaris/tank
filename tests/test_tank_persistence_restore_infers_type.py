from __future__ import annotations

from backend.entity_transfer import serialize_entity_for_transfer
from backend.tank_persistence import restore_tank_from_snapshot
from core.constants import FRACTAL_PLANTS_ENABLED
from core.entities.fractal_plant import FractalPlant
from core.genetics import PlantGenome
from core.tank_world import TankWorld, TankWorldConfig


def _make_world(seed: int) -> TankWorld:
    world = TankWorld(config=TankWorldConfig(headless=True), seed=seed)
    world.setup()
    return world


def test_restore_snapshot_infers_missing_type_for_fractal_plants() -> None:
    if not FRACTAL_PLANTS_ENABLED:
        return

    source = _make_world(seed=100)
    assert source.engine.root_spot_manager is not None
    spot = source.engine.root_spot_manager.get_random_empty_spot()
    assert spot is not None

    plant = FractalPlant(
        environment=source.engine.environment,
        genome=PlantGenome.create_random(rng=source.rng),
        root_spot=spot,
        initial_energy=42.0,
        ecosystem=source.engine.ecosystem,
        screen_width=source.config.screen_width,
        screen_height=source.config.screen_height,
    )
    spot.claim(plant)
    source.engine.add_entity(plant)

    entity_data = serialize_entity_for_transfer(plant, migration_direction="left")
    assert entity_data is not None
    original_id = entity_data["id"]
    entity_data.pop("type", None)

    dest = _make_world(seed=101)
    snapshot = {
        "tank_id": "test-tank",
        "frame": 1,
        "entities": [entity_data],
    }

    assert restore_tank_from_snapshot(snapshot, dest) is True
    restored = [e for e in dest.entities_list if isinstance(e, FractalPlant)]
    assert len(restored) == 1
    assert restored[0].plant_id == original_id

