from __future__ import annotations

import pytest

from core.transfer.entity_transfer import deserialize_entity, serialize_entity_for_transfer
from core.config.server import PLANTS_ENABLED
from core.entities.fish import Fish
from core.entities.plant import Plant
from core.genetics import PlantGenome
from core.tank_world import TankWorld, TankWorldConfig


def _make_world(seed: int) -> TankWorld:
    world = TankWorld(config=TankWorldConfig(headless=True), seed=seed)
    world.setup()
    return world


def test_fish_transfer_round_trip() -> None:
    source = _make_world(seed=1)
    fish = next(e for e in source.entities_list if isinstance(e, Fish))
    fish.genome.physical.size_modifier.mutation_rate = 1.7
    fish.genome.behavioral.aggression.hgt_probability = 0.42

    data = serialize_entity_for_transfer(fish)
    assert data is not None
    assert data["type"] == "fish"
    assert "genome_data" in data
    assert "mate_preferences" in data["genome_data"]
    assert "lifespan_modifier" in data["genome_data"]
    assert "asexual_reproduction_chance" in data["genome_data"]
    assert data["genome_data"]["trait_meta"]["size_modifier"]["mutation_rate"] == pytest.approx(1.7)
    assert data["genome_data"]["trait_meta"]["aggression"]["hgt_probability"] == pytest.approx(0.42)

    dest = _make_world(seed=2)
    restored = deserialize_entity(data, dest)
    assert isinstance(restored, Fish)
    assert restored.species == data["species"]
    assert restored.energy == pytest.approx(data["energy"])
    assert restored.generation == data["generation"]
    assert (
        restored.genome.behavioral.mate_preferences.value == data["genome_data"]["mate_preferences"]
    )
    assert restored.genome.physical.lifespan_modifier.value == pytest.approx(
        data["genome_data"]["lifespan_modifier"]
    )
    assert restored.genome.physical.size_modifier.mutation_rate == pytest.approx(1.7)
    assert restored.genome.behavioral.aggression.hgt_probability == pytest.approx(0.42)


def test_unknown_entity_type_returns_none() -> None:
    dest = _make_world(seed=3)
    assert deserialize_entity({"type": "nope"}, dest) is None


@pytest.mark.skipif(not PLANTS_ENABLED, reason="Plants disabled in constants")
def test_plant_transfer_round_trip() -> None:
    source = _make_world(seed=10)

    # Create a plant explicitly so the test is stable (independent of initial population settings).
    assert source.engine.root_spot_manager is not None
    spot = source.engine.root_spot_manager.get_random_empty_spot()
    assert spot is not None

    plant = Plant(
        environment=source.engine.environment,
        genome=PlantGenome.create_random(rng=source.rng),
        root_spot=spot,
        initial_energy=42.0,
        ecosystem=source.engine.ecosystem,
        plant_id=999,  # Explicit test ID (normally assigned by PlantManager)
    )
    spot.claim(plant)
    source.engine.request_spawn(plant, reason="test")
    source.engine._apply_entity_mutations("test")

    data = serialize_entity_for_transfer(plant, migration_direction="left")
    assert data is not None
    assert data["type"] == "plant"
    assert data.get("migration_direction") == "left"
    assert "genome_data" in data

    dest = _make_world(seed=11)
    restored = deserialize_entity(data, dest)
    assert isinstance(restored, Plant)
    assert restored.energy == pytest.approx(data["energy"])
    assert restored.genome.type == data["genome_data"].get("type")
