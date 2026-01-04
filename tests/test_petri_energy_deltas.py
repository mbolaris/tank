"""Cross-mode tests for energy delta application.

Verifies that energy deltas work correctly in non-Tank modes like Petri,
ensuring the identity provider changes are truly mode-agnostic.
"""

import pytest

from core.simulation.engine import SimulationEngine
from core.worlds.petri.pack import PetriPack


def test_petri_mode_initializes_with_identity_provider():
    """Verify Petri mode sets up identity provider correctly."""
    engine = SimulationEngine(headless=True, seed=42)
    pack = PetriPack(engine.config)
    engine.setup(pack)

    # Identity provider should be set
    assert engine._identity_provider is not None, "Petri mode should have an identity provider"

    # Provider should have get_entity_by_id method
    assert hasattr(
        engine._identity_provider, "get_entity_by_id"
    ), "Identity provider must support get_entity_by_id for reverse lookup"

    # Provider should have sync_entities method
    assert hasattr(
        engine._identity_provider, "sync_entities"
    ), "Identity provider must support sync_entities for batch operations"


def test_petri_mode_runs_multiple_frames():
    """Verify Petri mode can run multiple frames with energy processing."""
    engine = SimulationEngine(headless=True, seed=42)
    pack = PetriPack(engine.config)
    engine.setup(pack)

    # Run several frames
    for _ in range(10):
        engine.update()

    # Verify frame count advanced
    assert engine.frame_count == 10, "Engine should have run 10 frames"


def test_petri_energy_deltas_reference_real_entities():
    """Verify energy deltas in Petri mode reference entities via identity provider."""
    engine = SimulationEngine(headless=True, seed=42)
    pack = PetriPack(engine.config)
    engine.setup(pack)

    # Get a fish (Petri inherits Tank entities for now)
    fish_list = engine.get_fish_list()
    if len(fish_list) == 0:
        pytest.skip("No fish in Petri mode to test energy deltas")

    fish = fish_list[0]
    initial_energy = fish.energy

    # Run update to process (should trigger metabolism burn)
    engine.update()

    # Energy should have decreased (burn)
    assert (
        fish.energy < initial_energy
    ), f"Fish energy should have decreased from {initial_energy}, but is {fish.energy}"

    # Check that energy delta record uses stable ID format
    from core.config.entities import FISH_ID_OFFSET

    expected_stable_id = str(fish.fish_id + FISH_ID_OFFSET)

    # Look for delta relating to this fish
    energy_delta = next(
        (d for d in engine._frame_energy_deltas if d.stable_id == expected_stable_id), None
    )

    assert energy_delta is not None, "Energy delta record not found"
    assert energy_delta.source == "metabolism"

    # Verify the ID is in stable format (uses offset, not raw fish_id)
    assert energy_delta.entity_id == expected_stable_id, (
        f"Energy delta ID ({energy_delta.entity_id}) should be stable ID "
        f"({expected_stable_id}), not raw fish_id ({fish.fish_id})"
    )
    assert energy_delta.stable_id == expected_stable_id

    # Stable ID should resolve to a real entity
    provider = engine._identity_provider
    assert provider is not None
    resolved = provider.get_entity_by_id(energy_delta.stable_id)
    assert resolved is not None, "Energy delta stable_id did not resolve to an entity"


def test_identity_provider_sync_captures_all_entities():
    """Verify sync_entities captures all current entities for reverse lookup."""
    engine = SimulationEngine(headless=True, seed=42)
    pack = PetriPack(engine.config)
    engine.setup(pack)

    provider = engine._identity_provider
    assert provider is not None

    # Get all entities
    all_entities = engine._entity_manager.entities_list

    # Sync the provider
    provider.sync_entities(all_entities)

    # Each entity should be findable by its stable ID
    for entity in all_entities:
        entity_type, stable_id = provider.get_identity(entity)
        found_entity = provider.get_entity_by_id(stable_id)
        assert (
            found_entity is entity
        ), f"Entity with stable ID {stable_id} not found via get_entity_by_id"
