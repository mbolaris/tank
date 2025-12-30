"""Tests for new architectural abstractions: World and SkillfulAgent Protocols.

These tests verify that:
1. World Protocol is correctly defined
2. Environment implements World Protocol
3. SkillfulAgent Protocol is correctly defined
4. Protocol-based type checking works correctly
"""

import random
from typing import List

import pytest

from core.entities.base import Agent
from core.environment import Environment
from core.interfaces import SkillfulAgent
from core.world import World, World2D, get_2d_dimensions, is_2d_world


class TestWorldProtocol:
    """Tests for the World Protocol abstraction."""

    def test_environment_implements_world_protocol(self):
        """Environment should satisfy World Protocol."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        # Protocol check - Environment should be recognized as a World
        assert isinstance(env, World), "Environment should implement World Protocol"

        # Check specific methods
        assert hasattr(env, "get_agents_of_type"), "Environment should implement get_agents_of_type"
        assert hasattr(
            env, "nearby_agents_by_type"
        ), "Environment should implement nearby_agents_by_type"

    def test_environment_implements_world2d_protocol(self):
        """Environment should satisfy World2D Protocol."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        # Protocol check - Environment should be recognized as a World2D
        assert isinstance(env, World2D), "Environment should implement World2D Protocol"

    def test_generic_spatial_queries(self):
        """Generic spatial query methods should return lists."""

        class MockAgent(Agent):
            def __init__(self, env, x, y):
                super().__init__(env, x, y, 0)

        env = Environment(width=800, height=600, rng=random.Random(42))
        agent = MockAgent(env, 100, 100)

        # Generic methods should exist
        assert hasattr(env, "nearby_evolving_agents"), "Should have generic method"
        assert hasattr(env, "nearby_resources"), "Should have generic method"

        # Both should return list results
        evolving = env.nearby_evolving_agents(agent, 100)
        assert isinstance(evolving, list), "Return type should be list"

        resources = env.nearby_resources(agent, 100)
        assert isinstance(resources, list), "Return type should be list"

    def test_is_2d_world_helper(self):
        """is_2d_world helper should correctly identify 2D worlds."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        assert is_2d_world(env), "Environment should be identified as 2D world"

    def test_get_2d_dimensions_helper(self):
        """get_2d_dimensions should extract width/height from 2D worlds."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        width, height = get_2d_dimensions(env)
        assert width == 800, "Width should match"
        assert height == 600, "Height should match"

    def test_world_spatial_queries_work(self):
        """World Protocol spatial queries should work on Environment."""

        # Create environment with some mock agents
        class MockAgent(Agent):
            def __init__(self, env, x, y):
                super().__init__(env, x, y, 0)

        env = Environment(width=800, height=600, rng=random.Random(42))
        agent1 = MockAgent(env, 100, 100)
        agent2 = MockAgent(env, 150, 150)
        agent3 = MockAgent(env, 500, 500)

        env.agents = [agent1, agent2, agent3]
        env.rebuild_spatial_grid()

        # Test nearby_agents query through World Protocol
        nearby: List[Agent] = env.nearby_agents(agent1, radius=100)

        # Should find agent2 (distance ~70) but not agent3 (distance ~565)
        assert agent2 in nearby, "Should find nearby agent"
        assert agent3 not in nearby, "Should not find distant agent"

    def test_world_dimensions_property(self):
        """World.dimensions property should return environment dimensions."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        dims = env.dimensions
        assert len(dims) == 2, "Should have 2 dimensions"
        assert dims[0] == 800, "First dimension should be width"
        assert dims[1] == 600, "Second dimension should be height"

    def test_world_bounds_method(self):
        """World.get_bounds should return valid boundaries."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        bounds = env.get_bounds()
        assert bounds is not None, "Bounds should be defined"
        # Bounds format: ((min_x, min_y), (max_x, max_y))
        assert len(bounds) == 2, "Should have min and max bounds"

    def test_world_is_valid_position(self):
        """World.is_valid_position should check position validity."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        # Valid positions
        assert env.is_valid_position((100, 100)), "Center position should be valid"
        assert env.is_valid_position((0, 0)), "Origin should be valid"
        assert env.is_valid_position((799, 599)), "Max position should be valid"

        # Invalid positions
        assert not env.is_valid_position((-10, 100)), "Negative x should be invalid"
        assert not env.is_valid_position((100, -10)), "Negative y should be invalid"
        assert not env.is_valid_position((900, 100)), "Out of bounds x should be invalid"
        assert not env.is_valid_position((100, 700)), "Out of bounds y should be invalid"


class TestSkillfulAgentProtocol:
    """Tests for the SkillfulAgent Protocol."""

    def test_protocol_is_runtime_checkable(self):
        """SkillfulAgent Protocol should be runtime checkable."""
        from core.skills.base import SkillGameResult, SkillGameType, SkillStrategy

        # Create a mock class that implements the protocol
        class MockSkillfulAgent:
            def get_strategy(self, game_type: SkillGameType):
                return None

            def set_strategy(self, game_type: SkillGameType, strategy: SkillStrategy):
                pass

            def learn_from_game(self, game_type: SkillGameType, result: SkillGameResult):
                pass

            @property
            def can_play_skill_games(self) -> bool:
                return True

        agent = MockSkillfulAgent()

        # Protocol check should pass
        assert isinstance(agent, SkillfulAgent), "Mock agent should satisfy SkillfulAgent Protocol"

    def test_protocol_rejects_incomplete_implementation(self):
        """SkillfulAgent Protocol should reject incomplete implementations."""

        # Create a class missing required methods
        class IncompleteAgent:
            def get_strategy(self, game_type):
                return None

            # Missing set_strategy, learn_from_game, can_play_skill_games

        agent = IncompleteAgent()

        # Protocol check should fail
        assert not isinstance(agent, SkillfulAgent), "Incomplete agent should not satisfy Protocol"

    def test_fish_implements_skillful_agent(self):
        """Fish should implement SkillfulAgent Protocol."""
        from core.entities.fish import Fish
        from core.movement_strategy import AlgorithmicMovement

        env = Environment(agents=[], width=800, height=600, rng=random.Random(42))
        movement = AlgorithmicMovement()

        fish = Fish(
            environment=env,
            movement_strategy=movement,
            species="test_fish",
            x=100,
            y=100,
            speed=2.0,
        )

        # Fish should satisfy SkillfulAgent Protocol
        assert isinstance(fish, SkillfulAgent), "Fish should implement SkillfulAgent Protocol"

        # Verify all required methods exist and work
        from core.skills.base import SkillGameType

        # get_strategy should return None for uninitialized games
        strategy = fish.get_strategy(SkillGameType.ROCK_PAPER_SCISSORS)
        assert strategy is None, "Should return None for uninitialized strategy"

        # can_play_skill_games should return bool
        can_play = fish.can_play_skill_games
        assert isinstance(can_play, bool), "can_play_skill_games should return bool"


class TestProtocolBackwardCompatibility:
    """Tests ensuring new protocols don't break existing code."""

    def test_environment_still_has_original_methods(self):
        """Environment should retain all original methods."""
        env = Environment(width=800, height=600, rng=random.Random(42))

        # Original methods should still exist
        assert hasattr(env, "nearby_agents"), "Should have nearby_agents"
        assert hasattr(env, "nearby_agents_by_type"), "Should have nearby_agents_by_type"
        assert hasattr(env, "get_agents_of_type"), "Should have get_agents_of_type"
        assert hasattr(env, "rebuild_spatial_grid"), "Should have rebuild_spatial_grid"

    def test_existing_code_patterns_still_work(self):
        """Common existing code patterns should continue to work."""

        class MockAgent(Agent):
            def __init__(self, env, x, y):
                super().__init__(env, x, y, 0)

        env = Environment(
            agents=[], width=800, height=600, rng=random.Random(42)
        )  # Initialize with empty list
        agent = MockAgent(env, 100, 100)
        env.agents = [agent]  # Add agent to list

        # Pattern 1: Direct spatial queries
        nearby = env.nearby_agents(agent, 100)
        assert isinstance(nearby, list), "Should return list"

        # Pattern 2: Type-specific queries
        from core.entities.resources import Food

        food_nearby = env.nearby_agents_by_type(agent, 100, Food)
        assert isinstance(food_nearby, list), "Should return list"

        # Pattern 3: Get all of type
        all_agents = env.get_agents_of_type(Agent)
        assert isinstance(all_agents, list), "Should return list"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
