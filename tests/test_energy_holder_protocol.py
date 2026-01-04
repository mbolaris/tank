"""Tests for EnergyHolder protocol conformance.

Validates that Fish and Plant both properly implement the EnergyHolder protocol
with consistent modify_energy() semantics.
"""

import random
from unittest.mock import MagicMock, patch

import pytest

from core.entities.fish import Fish
from core.entities.plant import Plant
from core.genetics import PlantGenome
from core.interfaces import EnergyHolder


@pytest.fixture
def mock_environment():
    """Create a mock environment for entity tests."""
    env = MagicMock()
    env.rng = random.Random(42)
    env.width = 800
    env.height = 600
    env.tank_bounds = MagicMock()
    env.tank_bounds.left = 0
    env.tank_bounds.right = 800
    env.tank_bounds.top = 0
    env.tank_bounds.bottom = 600
    env.tank_bounds.water_top = 50
    env.add_entity = MagicMock()
    env.food_list = []
    env.simulation_config = None
    return env


@pytest.fixture
def mock_root_spot():
    """Create a mock root spot for plant tests."""
    spot = MagicMock()
    spot.x = 400
    spot.y = 550
    spot.spot_id = 5
    spot.manager = MagicMock()
    spot.manager.spots = list(range(25))
    spot.manager.get_spot_by_id = MagicMock(return_value=None)
    spot.get_anchor_topleft = MagicMock(return_value=(380, 500))
    return spot


class TestEnergyHolderProtocol:
    """Test that entities conform to EnergyHolder protocol."""

    def test_fish_is_energy_holder(self, mock_environment):
        """Fish should satisfy EnergyHolder protocol (runtime_checkable)."""
        fish = Fish(
            environment=mock_environment,
            movement_strategy=MagicMock(),
            species="test",
            x=100,
            y=100,
            speed=5,
        )
        assert isinstance(fish, EnergyHolder)

    def test_plant_is_energy_holder(self, mock_environment, mock_root_spot):
        """Plant should satisfy EnergyHolder protocol (runtime_checkable)."""
        genome = PlantGenome.create_random(rng=mock_environment.rng)
        plant = Plant(
            environment=mock_environment,
            genome=genome,
            root_spot=mock_root_spot,
            plant_id=1,
        )
        assert isinstance(plant, EnergyHolder)


class TestFishModifyEnergy:
    """Test Fish.modify_energy() semantics."""

    def test_returns_actual_delta_for_gain(self, mock_environment):
        """modify_energy should return the actual delta applied."""
        fish = Fish(
            environment=mock_environment,
            movement_strategy=MagicMock(),
            species="test",
            x=100,
            y=100,
            speed=5,
        )
        fish._energy_component.energy = 50.0

        delta = fish.modify_energy(20.0, source="test")

        assert delta == 20.0
        assert fish.energy == 70.0

    def test_clamps_at_max_energy(self, mock_environment):
        """Energy gains should clamp at max_energy."""
        fish = Fish(
            environment=mock_environment,
            movement_strategy=MagicMock(),
            species="test",
            x=100,
            y=100,
            speed=5,
        )
        fish._energy_component.energy = 90.0
        max_e = fish.max_energy

        # Try to add more than fits
        delta = fish.modify_energy(50.0, source="test")

        # Should only gain up to max
        assert fish.energy == max_e
        # Delta should reflect actual internal change (not overflow)
        assert delta == max_e - 90.0

    def test_clamps_at_zero_for_loss(self, mock_environment):
        """Energy loss should clamp at 0."""
        fish = Fish(
            environment=mock_environment,
            movement_strategy=MagicMock(),
            species="test",
            x=100,
            y=100,
            speed=5,
        )
        fish._energy_component.energy = 20.0

        delta = fish.modify_energy(-50.0, source="test")

        assert fish.energy == 0.0
        assert delta == -20.0  # Only lost 20, not 50


class TestPlantModifyEnergy:
    """Test Plant.modify_energy() semantics."""

    def test_returns_actual_delta_for_gain(self, mock_environment, mock_root_spot):
        """modify_energy should return the actual delta applied."""
        genome = PlantGenome.create_random(rng=mock_environment.rng)
        plant = Plant(
            environment=mock_environment,
            genome=genome,
            root_spot=mock_root_spot,
            plant_id=1,
        )
        plant.energy = 50.0

        delta = plant.modify_energy(20.0, source="test")

        assert delta == 20.0
        assert plant.energy == 70.0

    def test_clamps_at_max_energy(self, mock_environment, mock_root_spot):
        """Energy gains should clamp at max_energy, overflow routed."""
        genome = PlantGenome.create_random(rng=mock_environment.rng)
        plant = Plant(
            environment=mock_environment,
            genome=genome,
            root_spot=mock_root_spot,
            plant_id=1,
        )
        plant.energy = plant.max_energy - 10.0
        before = plant.energy

        with patch.object(plant, "_route_overflow_energy") as mock_route:
            delta = plant.modify_energy(50.0, source="test")

            # Overflow should be routed
            mock_route.assert_called_once()
            overflow_amount = mock_route.call_args[0][0]
            assert overflow_amount == pytest.approx(40.0, abs=0.1)

        # Energy should be at max
        assert plant.energy == plant.max_energy
        # Delta reflects internal change only
        assert delta == plant.max_energy - before

    def test_clamps_at_zero_for_loss(self, mock_environment, mock_root_spot):
        """Energy loss should clamp at 0."""
        genome = PlantGenome.create_random(rng=mock_environment.rng)
        plant = Plant(
            environment=mock_environment,
            genome=genome,
            root_spot=mock_root_spot,
            plant_id=1,
        )
        plant.energy = 20.0

        delta = plant.modify_energy(-50.0, source="test")

        assert plant.energy == 0.0
        assert delta == -20.0  # Only lost 20, not 50

    def test_zero_amount_returns_zero(self, mock_environment, mock_root_spot):
        """modify_energy(0) should be a no-op returning 0."""
        genome = PlantGenome.create_random(rng=mock_environment.rng)
        plant = Plant(
            environment=mock_environment,
            genome=genome,
            root_spot=mock_root_spot,
            plant_id=1,
        )
        initial = plant.energy

        delta = plant.modify_energy(0.0, source="test")

        assert delta == 0.0
        assert plant.energy == initial
