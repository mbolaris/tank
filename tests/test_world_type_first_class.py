"""Tests verifying world_type is first-class throughout the stack."""

from backend.snapshots.petri_snapshot_builder import PetriSnapshotBuilder
from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder
from backend.world_manager import WorldManager
from backend.world_registry import create_world


class TestWorldTypeFirstClass:
    """Verify world_type is properly stored and propagated."""

    def test_world_manager_creates_tank_world(self):
        """WorldManager can create tank instances."""
        manager = WorldManager()
        try:
            instance = manager.create_world(name="Tank Test", world_type="tank")
            assert instance.world_type == "tank"
            assert instance.is_tank()
            assert instance.runner.world_type == "tank"
        finally:
            manager.stop_all_worlds()

    def test_world_manager_creates_petri_world(self):
        """WorldManager can create petri instances."""
        manager = WorldManager()
        try:
            instance = manager.create_world(name="Petri Test", world_type="petri")
            assert instance.world_type == "petri"
            assert instance.runner.world_type == "petri"
            # Petri is technically a "tank" subtype currently, so is_tank() returns True
            assert instance.is_tank()
        finally:
            manager.stop_all_worlds()

    def test_world_manager_creates_soccer_world(self):
        """WorldManager can create soccer world instances."""
        manager = WorldManager()
        try:
            instance = manager.create_world(name="Soccer Test", world_type="soccer_training")
            assert instance.world_type == "soccer_training"
            assert instance.runner.world_type == "soccer_training"
            assert not instance.is_tank()
        finally:
            manager.stop_all_worlds()

    def test_snapshot_builder_matches_world_type(self):
        """Snapshot builder is correct for world_type."""
        tank_world, tank_builder = create_world("tank")
        assert isinstance(tank_builder, TankSnapshotBuilder)

        petri_world, petri_builder = create_world("petri")
        assert isinstance(petri_builder, PetriSnapshotBuilder)
