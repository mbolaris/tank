import math

from backend.simulation_manager import SimulationManager
from core.entities.plant import Plant
from core.math_utils import Vector2
from core.root_spots import RootSpotManager
from core.worlds.petri.root_spots import CircularRootSpotManager


class TestModeSwitchingRootSpots:
    def test_switch_to_petri_swaps_root_spot_manager_and_relocates_plants(self):
        # Initialize SimulationManager (which creates its own runner and engine)
        manager = SimulationManager(tank_id="test-tank")

        # Access the engine used by the manager
        engine = manager._runner.engine

        # Ensure we start in Tank mode
        assert manager.tank_info.world_type == "tank"
        assert isinstance(engine.plant_manager.root_spot_manager, RootSpotManager)

        # Create some test plants at known locations (center of tank)
        # Note: we need to manually add them because we bypass the normal spawn queue for this test setup
        spot = engine.plant_manager.root_spot_manager.get_random_empty_spot()
        plant1 = Plant(
            engine.environment,
            engine.plant_manager.create_variant_genome("lsystem"),
            spot,
            ecosystem=engine.ecosystem,
            plant_id=999,
        )
        plant1.pos = Vector2(400, 300)
        # Manually add to environment agents list
        if engine.environment.agents is None:
            engine.environment.agents = []
        engine.environment.agents.append(plant1)
        # Also add to ecosystem for consistency if needed, but runner relies on environment list
        # engine.ecosystem.registry.register(plant1)

        # Switch to Petri
        manager.change_world_type("petri")

        # Assert Manager Swapped
        assert isinstance(engine.plant_manager.root_spot_manager, CircularRootSpotManager)

        # Assert Plant Relocated
        # Petri Dish is centered at screen center.
        # Plants should be on the perimeter.

        dish = engine.environment.dish
        assert dish is not None

        # Check plant1 position
        dx = plant1.pos.x - dish.cx
        dy = plant1.pos.y - dish.cy
        distance = math.sqrt(dx * dx + dy * dy)

        # Should be approximately radius (PetriDish.r)
        # The CircularRootSpotManager puts spots exactly on radius.
        assert math.isclose(distance, dish.r, abs_tol=1.0)

        # Assert Plant has a new root spot
        assert plant1.root_spot is not None
        assert plant1.root_spot.manager == engine.plant_manager.root_spot_manager

    def test_switch_back_to_tank_restores_rectangular_manager(self):
        # Setup
        manager = SimulationManager(tank_id="test-tank")
        engine = manager._runner.engine

        manager.change_world_type("petri")

        # Verify Petri state
        assert isinstance(engine.plant_manager.root_spot_manager, CircularRootSpotManager)

        # Switch back to Tank
        manager.change_world_type("tank")

        # Assert Manager Restored
        assert isinstance(engine.plant_manager.root_spot_manager, RootSpotManager)
        assert not isinstance(engine.plant_manager.root_spot_manager, CircularRootSpotManager)

        # Assert Dish removed
        assert engine.environment.dish is None
