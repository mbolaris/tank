"""Tests for fish policy adapter and runtime policy swapping."""

import random
from unittest.mock import MagicMock, Mock

import pytest

from core.algorithms.composable.behavior import ComposableBehavior
from core.entities import Fish
from core.policies.behavior_adapter import BehaviorToMovementPolicyAdapter, SimplePolicy
from core.policies.interfaces import MovementPolicy


class TestPolicyAdapter:
    """Tests for policy swapping at runtime."""

    def test_simple_policy_called(self):
        """A simple policy returns expected velocity."""
        calls = []
        
        def my_policy(obs, rng):
            calls.append(obs)
            return (0.5, 0.5)
        
        policy = SimplePolicy(my_policy, policy_id="test_policy")
        result = policy({"energy": 100}, random.Random(42))
        
        assert result == (0.5, 0.5)
        assert len(calls) == 1
        assert policy.policy_id == "test_policy"

    def test_behavior_adapter(self):
        """Behavior adapter correctly delegates to ComposableBehavior."""
        # Mock behavior
        mock_behavior = Mock(spec=ComposableBehavior)
        mock_behavior.execute.return_value = (0.8, -0.2)
        
        # Mock fish
        mock_fish = Mock(spec=Fish)
        
        # Create adapter
        adapter = BehaviorToMovementPolicyAdapter(mock_behavior, mock_fish)
        
        # Execute
        vx, vy = adapter({}, random.Random(42))
        
        assert (vx, vy) == (0.8, -0.2)
        assert adapter.policy_id.startswith("behavior_adapter:")
        mock_behavior.execute.assert_called_once_with(mock_fish)

    def test_fish_uses_movement_policy_override(self):
        """Fish uses movement_policy override if set."""
        # Setup mocks
        mock_env = Mock()
        mock_env.rng = random.Random(42)
        mock_env.get_detection_modifier.return_value = 1.0
        # Mock nearby_resources to return empty list to avoid iteration errors
        mock_env.nearby_resources.return_value = []
        mock_env.nearby_agents_by_type.return_value = []
        
        # Create fish with mocked dependencies
        mock_genome = Mock()
        mock_genome.behavioral.behavior.value = None
        mock_genome.speed_modifier = 1.0
        mock_genome.metabolism_rate = 1.0
        mock_genome.physical.size_modifier.value = 1.0
        mock_genome.physical.lifespan_modifier.value = 1.0
        mock_genome.behavioral.poker_strategy.value = None  # Ensure poker strategy check passes
        mock_genome.behavioral.aggression.value = 0.5
        
        fish = Fish(
            environment=mock_env,
            movement_strategy=None,  # Not used in this test
            species="test_fish",
            x=100,
            y=100,
            speed=5.0,
            genome=mock_genome,
            fish_id=1,
            skip_birth_recording=True
        )
        
        # 1. Test with no policy (should fallback to whatever default logic, 
        # but we are testing the policy slot specifically)
        assert fish.movement_policy is None
        
        # 2. Set an override policy
        mock_policy = Mock(return_value=(0.9, 0.1))
        fish.movement_policy = mock_policy
        
        assert fish.movement_policy is mock_policy
        
        # 3. Simulate AlgorithmicMovement logic (simplified for unit test)
        # We need to manually invoke the policy because we can't easily run the full 
        # AlgorithmicMovement.move() without a complex simulation setup.
        # But we can verify the Fish property holds the policy.
        
        # To truly verify AlgorithmicMovement uses it, we'd need to instantiate AlgorithmicMovement
        # and call move(fish). Let's try that.
        
        from core.movement_strategy import AlgorithmicMovement
        strategy = AlgorithmicMovement()
        
        # Mock build_movement_observation (implicitly needed)
        # We can just let it run if dependencies are mocked enough
        # But build_movement_observation accesses fish.environment...
        
        strategy.move(fish)
        
        # Verify our mock policy was called
        mock_policy.assert_called_once()
