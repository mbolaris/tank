"""Tests verifying world_type is first-class throughout the stack."""

import pytest

from backend.simulation_manager import SimulationManager
from backend.tank_registry import TankRegistry
from backend.world_registry import create_world
from backend.snapshots.petri_snapshot_builder import PetriSnapshotBuilder
from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder


class TestWorldTypeFirstClass:
    """Verify world_type is properly stored and propagated."""

    def test_tank_info_includes_world_type(self):
        """TankInfo should store and serialize world_type."""
        manager = SimulationManager(world_type="petri")
        try:
            assert manager.tank_info.world_type == "petri"

            info_dict = manager.tank_info.to_dict()
            assert "world_type" in info_dict
            assert info_dict["world_type"] == "petri"
        finally:
            if manager.running:
                manager.stop()

    def test_tank_registry_creates_non_tank_worlds(self):
        """TankRegistry can create petri instances."""
        registry = TankRegistry(create_default=False)

        try:
            manager = registry.create_tank(
                name="Petri Test",
                world_type="petri",
            )

            assert manager.tank_info.world_type == "petri"
            assert manager._runner.world_type == "petri"
        finally:
            registry.stop_all()

    def test_create_and_step_petri_via_registry(self):
        """Create petri instance via registry and step N frames."""
        registry = TankRegistry(create_default=False)

        try:
            manager = registry.create_tank(
                name="Petri Step Test",
                world_type="petri",
            )
            manager.start(start_paused=False)

            # Let it initialize
            initial_frame = manager.world.frame_count
            for _ in range(10):
                manager.world.step()

            assert manager.world.frame_count == initial_frame + 10
        finally:
            registry.stop_all()

    def test_create_and_step_soccer_training_via_registry(self):
        """Create soccer_training instance via registry and verify world_type."""
        registry = TankRegistry(create_default=False)

        try:
            manager = registry.create_tank(
                name="Soccer Training Test",
                world_type="soccer_training",
            )

            # Verify world_type is correctly set
            assert manager.tank_info.world_type == "soccer_training"
            assert manager._runner.world_type == "soccer_training"

            # Verify world was created (adapter may not have frame_count)
            assert manager.world is not None
        finally:
            registry.stop_all()

    def test_default_world_type_is_tank(self):
        """Default world_type remains tank for backward compatibility."""
        manager = SimulationManager()
        try:
            assert manager.tank_info.world_type == "tank"
            assert manager._runner.world_type == "tank"
        finally:
            if manager.running:
                manager.stop()

    def test_snapshot_builder_matches_world_type(self):
        """Snapshot builder is correct for world_type."""
        tank_world, tank_builder = create_world("tank")
        assert isinstance(tank_builder, TankSnapshotBuilder)

        petri_world, petri_builder = create_world("petri")
        assert isinstance(petri_builder, PetriSnapshotBuilder)
