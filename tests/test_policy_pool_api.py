"""Tests for the canonical policy pool API in Environment."""

from core.environment import Environment


class TestEnvironmentPolicyPoolAPI:
    """Test the canonical policy pool access API."""

    def test_list_policy_component_ids_returns_movement_policies(self):
        """Environment.list_policy_component_ids returns movement policies."""
        env = Environment()

        # Default genome_code_pool should have builtin movement policies
        policy_ids = env.list_policy_component_ids("movement_policy")

        assert isinstance(policy_ids, list)
        assert len(policy_ids) > 0, "Should have at least one movement policy"

    def test_list_policy_component_ids_returns_empty_for_unknown_kind(self):
        """Unknown policy kinds return empty list, not error."""
        env = Environment()

        policy_ids = env.list_policy_component_ids("nonexistent_kind")

        assert policy_ids == []

    def test_list_policy_component_ids_handles_none_pool(self):
        """Returns empty list when genome_code_pool is None."""
        env = Environment()
        env.genome_code_pool = None

        policy_ids = env.list_policy_component_ids("movement_policy")

        assert policy_ids == []

    def test_fish_reproduction_uses_canonical_api(self):
        """Fish reproduction uses list_policy_component_ids for mutation."""
        # This is a smoke test - the actual mutation behavior is tested elsewhere
        # We just verify the API is accessible from the fish reproduction path
        from core.entities.fish import Fish
        from core.movement_strategy import AlgorithmicMovement

        env = Environment()
        fish = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="test",
            x=100,
            y=100,
            speed=1.0,
        )

        # The fish should be able to access policies through the environment
        policies = fish.environment.list_policy_component_ids("movement_policy")
        assert isinstance(policies, list)
