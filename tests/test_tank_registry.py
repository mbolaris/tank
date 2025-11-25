"""Tests for the TankRegistry multi-tank management system."""

import pytest
from backend.tank_registry import TankRegistry


class TestTankRegistry:
    """Tests for TankRegistry class."""

    def test_registry_creates_default_tank(self):
        """Test that registry creates a default tank on initialization."""
        registry = TankRegistry(create_default=True)

        assert registry.tank_count == 1
        assert registry.default_tank_id is not None
        assert registry.default_tank is not None
        assert registry.default_tank.tank_info.name == "Tank 1"
        assert registry.default_tank.tank_info.allow_transfers is True

        # Clean up
        registry.stop_all()

    def test_registry_no_default_tank(self):
        """Test registry can be created without default tank."""
        registry = TankRegistry(create_default=False)

        assert registry.tank_count == 0
        assert registry.default_tank_id is None
        assert registry.default_tank is None

    def test_create_tank(self):
        """Test creating a new tank."""
        registry = TankRegistry(create_default=False)

        manager = registry.create_tank(
            name="Test Tank",
            description="A test tank",
            owner="test_user",
            is_public=True,
            allow_transfers=False,
        )

        assert registry.tank_count == 1
        assert manager.tank_info.name == "Test Tank"
        assert manager.tank_info.description == "A test tank"
        assert manager.tank_info.owner == "test_user"
        assert manager.tank_info.is_public is True
        assert manager.tank_info.allow_transfers is False

        # Clean up
        registry.stop_all()

    def test_get_tank(self):
        """Test getting a tank by ID."""
        registry = TankRegistry(create_default=False)
        manager = registry.create_tank(name="Test Tank")
        assert manager.tank_info.allow_transfers is True

        # Get by valid ID
        retrieved = registry.get_tank(manager.tank_id)
        assert retrieved is manager

        # Get by invalid ID
        retrieved = registry.get_tank("invalid-id")
        assert retrieved is None

        # Clean up
        registry.stop_all()

    def test_get_tank_or_default(self):
        """Test getting tank with fallback to default."""
        registry = TankRegistry(create_default=True)

        # Get by None should return default
        retrieved = registry.get_tank_or_default(None)
        assert retrieved is registry.default_tank

        # Get by invalid ID should return default
        retrieved = registry.get_tank_or_default("invalid-id")
        assert retrieved is registry.default_tank

        # Create a new tank and get by valid ID
        new_tank = registry.create_tank(name="New Tank")
        retrieved = registry.get_tank_or_default(new_tank.tank_id)
        assert retrieved is new_tank

        # Clean up
        registry.stop_all()

    def test_list_tanks(self):
        """Test listing tanks."""
        registry = TankRegistry(create_default=False)

        # Create public and private tanks
        public_tank = registry.create_tank(name="Public Tank", is_public=True)
        private_tank = registry.create_tank(name="Private Tank", is_public=False)

        # List public only
        public_list = registry.list_tanks(include_private=False)
        assert len(public_list) == 1
        assert public_list[0]["tank"]["name"] == "Public Tank"

        # List all
        all_list = registry.list_tanks(include_private=True)
        assert len(all_list) == 2

        # Clean up
        registry.stop_all()

    def test_remove_tank(self):
        """Test removing a tank."""
        registry = TankRegistry(create_default=False)

        tank1 = registry.create_tank(name="Tank 1")
        tank2 = registry.create_tank(name="Tank 2")

        assert registry.tank_count == 2

        # Remove tank1
        result = registry.remove_tank(tank1.tank_id)
        assert result is True
        assert registry.tank_count == 1
        assert registry.get_tank(tank1.tank_id) is None

        # Try to remove non-existent tank
        result = registry.remove_tank("invalid-id")
        assert result is False

        # Clean up
        registry.stop_all()

    def test_list_tank_ids(self):
        """Test getting list of tank IDs."""
        registry = TankRegistry(create_default=False)

        tank1 = registry.create_tank(name="Tank 1")
        tank2 = registry.create_tank(name="Tank 2")

        ids = registry.list_tank_ids()
        assert len(ids) == 2
        assert tank1.tank_id in ids
        assert tank2.tank_id in ids

        # Clean up
        registry.stop_all()

    def test_contains(self):
        """Test membership checking."""
        registry = TankRegistry(create_default=False)
        tank = registry.create_tank(name="Test Tank")

        assert tank.tank_id in registry
        assert "invalid-id" not in registry

        # Clean up
        registry.stop_all()

    def test_iteration(self):
        """Test iterating over tanks."""
        registry = TankRegistry(create_default=False)

        tank1 = registry.create_tank(name="Tank 1")
        tank2 = registry.create_tank(name="Tank 2")

        tanks = list(registry)
        assert len(tanks) == 2
        assert tank1 in tanks
        assert tank2 in tanks

        # Clean up
        registry.stop_all()

    def test_start_stop_all(self):
        """Test starting and stopping all tanks."""
        registry = TankRegistry(create_default=False)

        tank1 = registry.create_tank(name="Tank 1")
        tank2 = registry.create_tank(name="Tank 2")

        # Start all
        registry.start_all(start_paused=True)
        assert tank1.running is True
        assert tank2.running is True

        # Stop all
        registry.stop_all()
        assert tank1.running is False
        assert tank2.running is False
