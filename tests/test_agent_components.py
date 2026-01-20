"""Tests for shared agent components.

Tests PerceptionComponent, LocomotionComponent, and FeedingComponent
in isolation and with basic integration scenarios.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from core.agents.components import FeedingComponent, LocomotionComponent, PerceptionComponent
from core.fish_memory import FishMemorySystem
from core.math_utils import Vector2


class TestPerceptionComponent:
    """Tests for PerceptionComponent."""

    def test_init_with_memory_system(self):
        """Component should initialize with a memory system."""
        memory = FishMemorySystem()
        perception = PerceptionComponent(memory)
        assert perception.memory_system is memory

    def test_get_food_locations_empty(self):
        """Should return empty list when no memories exist."""
        memory = FishMemorySystem()
        perception = PerceptionComponent(memory)
        locations = perception.get_food_locations()
        assert locations == []

    def test_record_and_get_food_locations(self):
        """Should record food discoveries and retrieve them."""
        memory = FishMemorySystem()
        perception = PerceptionComponent(memory)

        food_pos = Vector2(100.0, 200.0)
        perception.record_food_discovery(food_pos)

        locations = perception.get_food_locations()
        assert len(locations) == 1
        assert locations[0].x == food_pos.x
        assert locations[0].y == food_pos.y

    def test_record_danger(self):
        """Should record danger zones and retrieve them."""
        memory = FishMemorySystem()
        perception = PerceptionComponent(memory)

        danger_pos = Vector2(50.0, 75.0)
        perception.record_danger(danger_pos)

        locations = perception.get_danger_locations()
        assert len(locations) == 1

    def test_get_danger_zones(self):
        """Should return danger locations as zones to avoid."""
        memory = FishMemorySystem()
        perception = PerceptionComponent(memory)

        perception.record_danger(Vector2(10.0, 20.0))

        danger = perception.get_danger_zones(min_strength=0.1)
        assert len(danger) == 1


class TestLocomotionComponent:
    """Tests for LocomotionComponent."""

    def test_init_no_direction(self):
        """Component should start with no last direction."""
        locomotion = LocomotionComponent()
        assert locomotion.last_direction is None

    def test_update_direction_from_velocity(self):
        """Should update direction from velocity vector."""
        locomotion = LocomotionComponent()

        vel = Vector2(10.0, 0.0)
        previous = locomotion.update_direction(vel)

        assert previous is None  # First update has no previous
        assert locomotion.last_direction is not None
        assert locomotion.last_direction.x == 1.0
        assert locomotion.last_direction.y == 0.0

    def test_update_direction_zero_velocity(self):
        """Should set direction to None for zero velocity."""
        locomotion = LocomotionComponent()
        locomotion.update_direction(Vector2(10.0, 0.0))

        locomotion.update_direction(Vector2(0.0, 0.0))
        assert locomotion.last_direction is None

    def test_calculate_turn_cost_no_turn(self):
        """No turn should result in zero cost."""
        locomotion = LocomotionComponent()

        dir1 = Vector2(1.0, 0.0)
        dir2 = Vector2(1.0, 0.0)

        cost = locomotion.calculate_turn_cost(
            dir1, dir2, size=1.0, base_cost=0.1, size_multiplier=1.5
        )
        assert cost == 0.0

    def test_calculate_turn_cost_90_degree(self):
        """90-degree turn should have moderate cost."""
        locomotion = LocomotionComponent()

        dir1 = Vector2(1.0, 0.0)
        dir2 = Vector2(0.0, 1.0)

        cost = locomotion.calculate_turn_cost(
            dir1, dir2, size=1.0, base_cost=0.1, size_multiplier=1.5
        )
        assert cost > 0.0
        assert cost < 0.2  # Should be reasonable

    def test_calculate_turn_cost_180_degree(self):
        """180-degree turn should have highest cost."""
        locomotion = LocomotionComponent()

        dir1 = Vector2(1.0, 0.0)
        dir2 = Vector2(-1.0, 0.0)

        cost_180 = locomotion.calculate_turn_cost(
            dir1, dir2, size=1.0, base_cost=0.1, size_multiplier=1.5
        )
        cost_90 = locomotion.calculate_turn_cost(
            dir1, Vector2(0.0, 1.0), size=1.0, base_cost=0.1, size_multiplier=1.5
        )

        assert cost_180 > cost_90

    def test_calculate_turn_cost_scales_with_size(self):
        """Larger agents should pay more for turns."""
        locomotion = LocomotionComponent()

        dir1 = Vector2(1.0, 0.0)
        dir2 = Vector2(0.0, 1.0)

        cost_small = locomotion.calculate_turn_cost(
            dir1, dir2, size=0.5, base_cost=0.1, size_multiplier=1.5
        )
        cost_large = locomotion.calculate_turn_cost(
            dir1, dir2, size=2.0, base_cost=0.1, size_multiplier=1.5
        )

        assert cost_large > cost_small


class TestFeedingComponent:
    """Tests for FeedingComponent."""

    def test_init_default_multiplier(self):
        """Should use default bite size multiplier."""
        feeding = FeedingComponent()
        assert feeding.calculate_bite_size(1.0) == 20.0

    def test_init_custom_multiplier(self):
        """Should use custom bite size multiplier."""
        feeding = FeedingComponent(bite_size_multiplier=10.0)
        assert feeding.calculate_bite_size(1.0) == 10.0

    def test_bite_size_scales_with_agent_size(self):
        """Larger agents should take bigger bites."""
        feeding = FeedingComponent()

        small_bite = feeding.calculate_bite_size(0.5)
        large_bite = feeding.calculate_bite_size(2.0)

        assert large_bite > small_bite
        assert small_bite == 10.0
        assert large_bite == 40.0

    def test_can_eat_when_hungry(self):
        """Should be able to eat when not full."""
        feeding = FeedingComponent()
        assert feeding.can_eat(current_energy=50.0, max_energy=100.0)

    def test_cannot_eat_when_full(self):
        """Should not eat when at capacity."""
        feeding = FeedingComponent()
        assert not feeding.can_eat(current_energy=96.0, max_energy=100.0)

    def test_effective_bite_limited_by_capacity(self):
        """Effective bite should be limited by available capacity."""
        feeding = FeedingComponent()

        # Agent with only 5 energy capacity left
        effective = feeding.calculate_effective_bite(
            size=1.0, current_energy=95.0, max_energy=100.0
        )
        assert effective == 5.0

    def test_effective_bite_uses_full_bite_when_room(self):
        """Effective bite should use full bite size when capacity allows."""
        feeding = FeedingComponent()

        effective = feeding.calculate_effective_bite(
            size=1.0, current_energy=10.0, max_energy=100.0
        )
        assert effective == 20.0


class TestPetriMicrobeAgent:
    """Tests for GenericAgent component composition.

    Historically this used PetriMicrobeAgent (a reference stub). We now keep the
    same coverage by defining a minimal GenericAgent subclass inside the test.
    """

    def test_agent_initializes_with_components(self):
        """Agent should initialize with all required components."""
        from core.agents.components import (
            FeedingComponent,
            LocomotionComponent,
            PerceptionComponent,
        )
        from core.energy.energy_component import EnergyComponent
        from core.entities.generic_agent import AgentComponents, GenericAgent

        class TestMicrobe(GenericAgent):
            def __init__(self, environment, x, y, speed):
                memory = FishMemorySystem(
                    max_memories_per_type=50, decay_rate=0.02, learning_rate=0.2
                )
                components = AgentComponents(
                    energy=EnergyComponent(
                        max_energy=100.0,
                        base_metabolism=0.05,
                        initial_energy_ratio=0.5,
                    ),
                    perception=PerceptionComponent(memory),
                    locomotion=LocomotionComponent(),
                    feeding=FeedingComponent(bite_size_multiplier=10.0),
                )
                super().__init__(
                    environment=environment, x=x, y=y, speed=speed, components=components
                )

        mock_world = MagicMock()
        mock_world.get_bounds.return_value = ((0, 0), (1000, 600))

        agent = TestMicrobe(mock_world, x=100, y=100, speed=2.0)

        assert agent.perception is not None
        assert agent.locomotion is not None
        assert agent.feeding is not None
        assert agent.energy == 50.0

    def test_agent_uses_perception_for_food_locations(self):
        """Agent should delegate food memory to perception component."""
        from core.agents.components import (
            FeedingComponent,
            LocomotionComponent,
            PerceptionComponent,
        )
        from core.energy.energy_component import EnergyComponent
        from core.entities.generic_agent import AgentComponents, GenericAgent

        class TestMicrobe(GenericAgent):
            def __init__(self, environment, x, y, speed):
                memory = FishMemorySystem(
                    max_memories_per_type=50, decay_rate=0.02, learning_rate=0.2
                )
                components = AgentComponents(
                    energy=EnergyComponent(
                        max_energy=100.0,
                        base_metabolism=0.05,
                        initial_energy_ratio=0.5,
                    ),
                    perception=PerceptionComponent(memory),
                    locomotion=LocomotionComponent(),
                    feeding=FeedingComponent(bite_size_multiplier=10.0),
                )
                super().__init__(
                    environment=environment, x=x, y=y, speed=speed, components=components
                )

        mock_world = MagicMock()
        mock_world.get_bounds.return_value = ((0, 0), (1000, 600))

        agent = TestMicrobe(mock_world, x=100, y=100, speed=2.0)

        # Initially empty
        assert agent.perception is not None
        assert agent.perception.get_food_locations() == []

        # Record via perception
        agent.perception.record_food_discovery(Vector2(50, 50))
        locations = agent.perception.get_food_locations()
        assert len(locations) == 1
