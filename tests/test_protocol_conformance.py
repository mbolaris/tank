"""Comprehensive protocol conformance tests.

These tests verify that all implementations correctly conform to their declared
protocols. This catches mismatches between protocols and implementations early,
preventing bugs that would only surface at runtime.

Design Philosophy:
    Protocol conformance tests are a form of "contract testing" - they verify
    that implementations honor the contracts defined by protocols. This is
    especially important as the codebase evolves, because:

    1. Adding a method to a protocol should fail tests if implementations
       don't provide that method
    2. Changing a protocol's method signature should fail tests if
       implementations have the wrong signature
    3. New implementations must satisfy all protocol requirements

Test Categories:
    - Protocol interface tests: Verify protocols define expected methods
    - Implementation tests: Verify implementations satisfy protocols
    - Signature tests: Verify method signatures match protocol expectations
"""

import pytest

from core.entities.base import Agent
from core.environment import Environment


class TestBehaviorStrategyProtocol:
    """Tests for BehaviorStrategy protocol conformance."""

    def test_all_algorithms_implement_execute(self):
        """All algorithms must implement execute() method."""
        from core.algorithms.registry import ALL_ALGORITHMS

        for algo_class in ALL_ALGORITHMS:
            instance = algo_class.random_instance()
            assert hasattr(instance, "execute"), f"{algo_class.__name__} missing execute method"
            assert callable(instance.execute), f"{algo_class.__name__}.execute should be callable"

    def test_all_algorithms_implement_mutate_parameters(self):
        """All algorithms must implement mutate_parameters() method."""
        from core.algorithms.registry import ALL_ALGORITHMS

        for algo_class in ALL_ALGORITHMS:
            instance = algo_class.random_instance()
            assert hasattr(
                instance, "mutate_parameters"
            ), f"{algo_class.__name__} missing mutate_parameters"
            assert callable(
                instance.mutate_parameters
            ), f"{algo_class.__name__}.mutate_parameters should be callable"

    def test_all_algorithms_have_algorithm_id(self):
        """All algorithms must have an algorithm_id attribute."""
        from core.algorithms.registry import ALL_ALGORITHMS

        seen_ids = set()
        for algo_class in ALL_ALGORITHMS:
            instance = algo_class.random_instance()
            assert hasattr(instance, "algorithm_id"), f"{algo_class.__name__} missing algorithm_id"
            assert isinstance(
                instance.algorithm_id, str
            ), f"{algo_class.__name__}.algorithm_id should be str"
            assert len(instance.algorithm_id) > 0, f"{algo_class.__name__}.algorithm_id is empty"

            # Check uniqueness
            assert (
                instance.algorithm_id not in seen_ids
            ), f"Duplicate algorithm_id: {instance.algorithm_id}"
            seen_ids.add(instance.algorithm_id)

    def test_all_algorithms_have_parameters(self):
        """All algorithms must have a parameters dict."""
        from core.algorithms.registry import ALL_ALGORITHMS

        for algo_class in ALL_ALGORITHMS:
            instance = algo_class.random_instance()
            assert hasattr(instance, "parameters"), f"{algo_class.__name__} missing parameters"
            assert isinstance(
                instance.parameters, dict
            ), f"{algo_class.__name__}.parameters should be dict"

    def test_execute_returns_tuple(self):
        """execute() should return a tuple of two floats."""
        from core.algorithms.registry import ALL_ALGORITHMS
        from core.entities.fish import Fish
        from core.movement_strategy import AlgorithmicMovement

        env = Environment(agents=[], width=800, height=600)
        movement = AlgorithmicMovement()
        fish = Fish(
            environment=env,
            movement_strategy=movement,
            species="test",
            x=400,
            y=300,
            speed=2.0,
        )
        env.agents = [fish]
        env.rebuild_spatial_grid()

        for algo_class in ALL_ALGORITHMS:
            instance = algo_class.random_instance()
            result = instance.execute(fish)

            assert isinstance(
                result, tuple
            ), f"{algo_class.__name__}.execute() should return tuple, got {type(result)}"
            assert (
                len(result) == 2
            ), f"{algo_class.__name__}.execute() should return 2-tuple, got {len(result)}"
            assert isinstance(
                result[0], (int, float)
            ), f"{algo_class.__name__}.execute()[0] should be numeric"
            assert isinstance(
                result[1], (int, float)
            ), f"{algo_class.__name__}.execute()[1] should be numeric"

    def test_behavior_helpers_mixin_methods_accessible(self):
        """All algorithms should have access to BehaviorHelpersMixin methods."""
        from core.algorithms.registry import ALL_ALGORITHMS

        mixin_methods = [
            "_find_nearest",
            "_safe_normalize",
            "_get_predator_threat",
            "_find_nearest_food",
            "_should_flee_predator",
            "_get_energy_state",
        ]

        for algo_class in ALL_ALGORITHMS:
            instance = algo_class.random_instance()
            for method_name in mixin_methods:
                assert hasattr(
                    instance, method_name
                ), f"{algo_class.__name__} missing mixin method {method_name}"
                assert callable(
                    getattr(instance, method_name)
                ), f"{algo_class.__name__}.{method_name} should be callable"


class TestSystemProtocol:
    """Tests for System protocol conformance."""

    def test_system_protocol_has_required_attributes(self):
        """System Protocol should define required attributes."""
        from core.systems.base import System

        # Check protocol defines expected interface
        assert hasattr(System, "name"), "System protocol should define 'name' property"
        assert hasattr(System, "enabled"), "System protocol should define 'enabled' property"
        assert hasattr(System, "update"), "System protocol should define 'update' method"

    def test_base_system_implements_protocol(self):
        """BaseSystem should implement System protocol."""
        from core.systems.base import BaseSystem, System, SystemResult
        from typing import cast

        from core.simulation.engine import SimulationEngine

        # Create a minimal concrete implementation
        class TestSystem(BaseSystem):
            def _do_update(self, frame: int) -> SystemResult:
                return SystemResult.empty()

        # Create mock engine
        class MockEngine:
            pass

        system = TestSystem(cast(SimulationEngine, MockEngine()), "test_system")

        # Verify protocol compliance
        assert isinstance(system, System), "BaseSystem should satisfy System protocol"
        assert hasattr(system, "name")
        assert hasattr(system, "enabled")
        assert hasattr(system, "update")
        assert callable(system.update)

    def test_system_update_returns_system_result(self):
        """System.update() should return SystemResult."""
        from core.systems.base import BaseSystem, SystemResult
        from typing import cast

        from core.simulation.engine import SimulationEngine

        class TestSystem(BaseSystem):
            def _do_update(self, frame: int) -> SystemResult:
                return SystemResult(entities_affected=5)

        class MockEngine:
            pass

        system = TestSystem(cast(SimulationEngine, MockEngine()), "test")
        result = system.update(frame=1)

        assert isinstance(result, SystemResult), "update() should return SystemResult"
        assert result.entities_affected == 5

    def test_system_result_has_expected_fields(self):
        """SystemResult should have all expected fields."""
        from core.systems.base import SystemResult

        result = SystemResult()

        # Check all expected fields
        assert hasattr(result, "entities_affected")
        assert hasattr(result, "entities_spawned")
        assert hasattr(result, "entities_removed")
        assert hasattr(result, "events_emitted")
        assert hasattr(result, "skipped")
        assert hasattr(result, "details")

        # Check types
        assert isinstance(result.entities_affected, int)
        assert isinstance(result.entities_spawned, int)
        assert isinstance(result.entities_removed, int)
        assert isinstance(result.events_emitted, int)
        assert isinstance(result.skipped, bool)
        assert isinstance(result.details, dict)


class TestEnergyHolderProtocol:
    """Tests for EnergyHolder protocol conformance."""

    def test_fish_implements_energy_holder(self):
        """Fish should implement EnergyHolder protocol."""
        from core.entities.fish import Fish
        from core.interfaces import EnergyHolder
        from core.movement_strategy import AlgorithmicMovement

        env = Environment(agents=[], width=800, height=600)
        movement = AlgorithmicMovement()
        fish = Fish(
            environment=env,
            movement_strategy=movement,
            species="test",
            x=100,
            y=100,
            speed=2.0,
        )

        # Protocol check
        assert isinstance(fish, EnergyHolder), "Fish should implement EnergyHolder"

        # Verify interface
        assert hasattr(fish, "energy"), "Should have energy property"
        assert hasattr(fish, "max_energy"), "Should have max_energy property"
        assert hasattr(fish, "modify_energy"), "Should have modify_energy method"

        # Verify functionality
        initial_energy = fish.energy
        fish.modify_energy(-10)
        assert fish.energy == initial_energy - 10, "modify_energy should work"


class TestPositionableProtocol:
    """Tests for Positionable protocol conformance."""

    def test_agent_is_positionable(self):
        """Agent should satisfy Positionable protocol."""
        from core.interfaces import Positionable

        env = Environment(agents=[], width=800, height=600)

        class TestAgent(Agent):
            def __init__(self, env, x, y):
                super().__init__(env, x, y, 0)

        agent = TestAgent(env, 100, 200)

        assert isinstance(agent, Positionable), "Agent should be Positionable"
        assert hasattr(agent, "pos")
        assert hasattr(agent, "width")
        assert hasattr(agent, "height")


class TestWorldProtocolConformance:
    """Additional World protocol conformance tests."""

    def test_environment_has_all_world_methods(self):
        """Environment should have all World protocol methods."""

        env = Environment(width=800, height=600)

        # Get all methods defined in World protocol
        world_methods = [
            "nearby_agents",
            "nearby_agents_by_type",
            "get_agents_of_type",
            "get_bounds",
            "is_valid_position",
            "dimensions",
        ]

        for method_name in world_methods:
            assert hasattr(env, method_name), f"Environment missing World method: {method_name}"

    def test_spatial_query_methods_return_lists(self):
        """All spatial query methods should return lists."""
        from core.entities.resources import Food

        env = Environment(agents=[], width=800, height=600)

        class TestAgent(Agent):
            def __init__(self, env, x, y):
                super().__init__(env, x, y, 0)

        agent = TestAgent(env, 100, 100)
        env.agents = [agent]
        env.rebuild_spatial_grid()

        # Test all spatial query methods return lists
        assert isinstance(env.nearby_agents(agent, 100), list)
        assert isinstance(env.nearby_agents_by_type(agent, 100, Food), list)
        assert isinstance(env.get_agents_of_type(Agent), list)


class TestInterfacesModuleProtocols:
    """Tests for protocols defined in core/interfaces.py."""

    def test_runtime_checkable_protocols_work(self):
        """Protocols marked @runtime_checkable should support isinstance()."""
        from core import interfaces

        # Only protocols that need isinstance() checks should be @runtime_checkable
        # Other protocols are for static type checking only
        runtime_checkable_protocols = [
            "EnergyHolder",
            "PokerPlayer",
            "Positionable",
            "BehaviorStrategy",
            "SkillfulAgent",
        ]

        for name in runtime_checkable_protocols:
            assert hasattr(interfaces, name), f"interfaces module missing Protocol: {name}"
            protocol_class = getattr(interfaces, name)

            # This should not raise for runtime_checkable protocols
            try:
                isinstance(object(), protocol_class)
            except TypeError as e:
                if "runtime_checkable" in str(e):
                    pytest.fail(f"Protocol {name} should be @runtime_checkable")

    def test_all_protocols_exist(self):
        """All expected protocols should be defined in interfaces module."""
        from core import interfaces

        # All protocols (both runtime_checkable and static-only)
        all_protocol_names = [
            "EnergyHolder",
            "PokerPlayer",
            "Positionable",
            "BehaviorStrategy",
            "SimulationStats",
            "EntityManager",
            "FoodSpawner",
            "CollisionHandler",
            "PokerCoordinator",
            "Evolvable",
            "Mortal",
            "Reproducible",
            "SkillfulAgent",
        ]

        for name in all_protocol_names:
            assert hasattr(interfaces, name), f"interfaces module missing Protocol: {name}"


class TestProtocolEvolution:
    """Tests that help catch protocol/implementation drift during evolution."""

    def test_algorithm_count_matches_registry(self):
        """Number of algorithms should match registry count."""
        from core.algorithms.registry import ALGORITHM_REGISTRY, ALL_ALGORITHMS

        assert len(ALL_ALGORITHMS) == len(
            ALGORITHM_REGISTRY
        ), "ALL_ALGORITHMS and ALGORITHM_REGISTRY should have same count"

    def test_all_algorithms_can_be_serialized_and_deserialized(self):
        """All algorithms should support to_dict/from_dict round-trip."""
        from core.algorithms.registry import ALL_ALGORITHMS, behavior_from_dict

        for algo_class in ALL_ALGORITHMS:
            instance = algo_class.random_instance()

            # Serialize
            data = instance.to_dict()
            assert isinstance(data, dict), f"{algo_class.__name__}.to_dict() should return dict"
            assert "class" in data, "Serialized data should include 'class'"
            assert "algorithm_id" in data, "Serialized data should include 'algorithm_id'"
            assert "parameters" in data, "Serialized data should include 'parameters'"

            # Deserialize
            restored = behavior_from_dict(data)
            assert restored is not None, f"Failed to deserialize {algo_class.__name__}"
            assert type(restored) == type(
                instance
            ), f"Deserialized type mismatch for {algo_class.__name__}"
            assert (
                restored.algorithm_id == instance.algorithm_id
            ), f"algorithm_id mismatch for {algo_class.__name__}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
