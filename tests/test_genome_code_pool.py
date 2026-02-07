"""Tests for GenomeCodePool: genome-centric code pool for evolving agent policies.

Tests cover:
1. Genome mutation keeps policy IDs valid
2. Determinism: same seed → same actions for N steps
3. Safety: AST limits, source limits, action clamping
4. Crossover: combines parent policies correctly
"""

from __future__ import annotations

import random

import pytest

from core.code_pool import (CodePool, GenomeCodePool, GenomePolicySet,
                            SafetyConfig, ValidationError,
                            create_deterministic_rng, fork_rng,
                            validate_rng_determinism)
from core.code_pool.sandbox import parse_and_validate

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_movement_source() -> str:
    """Simple movement policy source code."""
    return """
def policy(observation, rng):
    food = observation.get("nearest_food_vector", {"x": 0.0, "y": 0.0})
    return (food.get("x", 0.0), food.get("y", 0.0))
"""


@pytest.fixture
def random_movement_source() -> str:
    """Movement policy that uses RNG for determinism testing."""
    return """
def policy(observation, rng):
    vx = rng.random() * 2.0 - 1.0
    vy = rng.random() * 2.0 - 1.0
    return (vx, vy)
"""


@pytest.fixture
def dt_aware_source() -> str:
    """Movement policy that uses dt for frame-rate independence."""
    return """
def policy(observation, rng):
    dt = observation.get("dt", 1.0)
    base_speed = 0.5
    return (base_speed * dt, 0.0)
"""


@pytest.fixture
def genome_code_pool(simple_movement_source: str) -> GenomeCodePool:
    """Create a GenomeCodePool with some test components."""
    pool = GenomeCodePool()

    # Add some movement policies
    pool.add_component(
        kind="movement_policy",
        name="Simple Seek Food",
        source=simple_movement_source,
    )
    pool.add_component(
        kind="movement_policy",
        name="Wander Policy",
        source="""
def policy(observation, rng):
    return (0.5, 0.5)
""",
    )
    pool.add_component(
        kind="movement_policy",
        name="Flee Policy",
        source="""
def policy(observation, rng):
    threat = observation.get("nearest_threat_vector", {"x": 0.0, "y": 0.0})
    return (-threat.get("x", 0.0), -threat.get("y", 0.0))
""",
    )

    # Set default for movement policy
    movement_ids = pool.get_components_by_kind("movement_policy")
    if movement_ids:
        pool.register_default("movement_policy", movement_ids[0])

    return pool


# =============================================================================
# Test: Genome Mutation Keeps Policy IDs Valid
# =============================================================================


class TestGenomeMutationValidity:
    """Test that genome mutation produces valid policy IDs."""

    def test_mutation_preserves_valid_ids(self, genome_code_pool: GenomeCodePool) -> None:
        """Mutating a genome should result in valid component IDs."""
        rng = random.Random(42)

        # Get available movement policies
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")
        assert len(movement_ids) >= 2, "Need at least 2 policies for this test"

        # Create initial policy set
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", movement_ids[0], {"speed": 0.5})

        # Mutate many times and verify IDs remain valid
        for _ in range(100):
            mutated = genome_code_pool.mutate_policy_set(policy_set, rng, mutation_rate=0.3)

            # Check all component IDs are valid
            for kind in ["movement_policy", "poker_policy", "soccer_policy"]:
                component_id = mutated.get_component_id(kind)
                if component_id is not None:
                    assert genome_code_pool.has_component(
                        component_id
                    ), f"Mutation produced invalid {kind} ID: {component_id}"

            policy_set = mutated  # Use for next iteration

    def test_mutation_can_swap_components(self, genome_code_pool: GenomeCodePool) -> None:
        """Mutation should be able to swap to different components of same kind."""
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")
        assert len(movement_ids) >= 2, "Need at least 2 policies for swap test"

        original_id = movement_ids[0]
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", original_id)

        # Run many mutations - should eventually swap
        swapped = False
        for seed in range(1000):
            rng = random.Random(seed)
            mutated = genome_code_pool.mutate_policy_set(policy_set, rng, mutation_rate=0.5)
            new_id = mutated.get_component_id("movement_policy")
            if new_id is not None and new_id != original_id:
                swapped = True
                # Verify the new ID is valid
                assert genome_code_pool.has_component(new_id)
                break

        assert swapped, "Mutation never swapped components after 1000 tries"

    def test_mutation_can_drop_policy(self, genome_code_pool: GenomeCodePool) -> None:
        """Mutation should be able to drop policies with low probability."""
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", movement_ids[0])

        # Run many mutations with high drop probability
        dropped = False
        for seed in range(1000):
            rng = random.Random(seed)
            # High mutation rate to trigger drops more often
            mutated = genome_code_pool.mutate_policy_set(policy_set, rng, mutation_rate=1.0)
            if mutated.get_component_id("movement_policy") is None:
                dropped = True
                break

        assert dropped, "Mutation never dropped policy after 1000 tries"

    def test_ensure_valid_policies_fills_missing(self, genome_code_pool: GenomeCodePool) -> None:
        """ensure_valid_policies should fill missing required policies."""
        rng = random.Random(42)

        # Start with empty policy set
        policy_set = GenomePolicySet()
        assert policy_set.get_component_id("movement_policy") is None

        # Ensure valid policies
        validated = genome_code_pool.ensure_valid_policies(policy_set, rng)

        # Movement policy should now be set (it's required)
        movement_id = validated.get_component_id("movement_policy")
        assert movement_id is not None, "Required movement_policy not filled"
        assert genome_code_pool.has_component(movement_id)

    def test_ensure_valid_policies_fixes_invalid_ids(
        self, genome_code_pool: GenomeCodePool
    ) -> None:
        """ensure_valid_policies should fix invalid component IDs."""
        rng = random.Random(42)

        # Create policy set with invalid ID
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", "nonexistent-uuid-12345")

        # Ensure valid policies
        validated = genome_code_pool.ensure_valid_policies(policy_set, rng)

        # Should be replaced with a valid ID
        movement_id = validated.get_component_id("movement_policy")
        assert movement_id != "nonexistent-uuid-12345"
        if movement_id is not None:
            assert genome_code_pool.has_component(movement_id)


# =============================================================================
# Test: Determinism - Same Seed → Same Actions
# =============================================================================


class TestDeterminism:
    """Test that same seed produces same actions for N steps."""

    def test_same_seed_same_output(self, random_movement_source: str) -> None:
        """Same seed should produce identical outputs."""
        pool = GenomeCodePool()
        component_id = pool.add_component(
            kind="movement_policy",
            name="Random Movement",
            source=random_movement_source,
        )

        observation = {"nearest_food_vector": {"x": 1.0, "y": 0.0}}

        # Execute with same seed twice
        rng1 = create_deterministic_rng(12345)
        result1 = pool.execute_policy(component_id, observation, rng1)

        rng2 = create_deterministic_rng(12345)
        result2 = pool.execute_policy(component_id, observation, rng2)

        assert result1.success and result2.success
        assert result1.output == result2.output

    def test_different_seeds_different_output(self, random_movement_source: str) -> None:
        """Different seeds should produce different outputs."""
        pool = GenomeCodePool()
        component_id = pool.add_component(
            kind="movement_policy",
            name="Random Movement",
            source=random_movement_source,
        )

        observation = {"nearest_food_vector": {"x": 1.0, "y": 0.0}}

        rng1 = create_deterministic_rng(12345)
        result1 = pool.execute_policy(component_id, observation, rng1)

        rng2 = create_deterministic_rng(54321)
        result2 = pool.execute_policy(component_id, observation, rng2)

        assert result1.success and result2.success
        # Different seeds should produce different outputs (probabilistically)
        assert result1.output != result2.output

    def test_determinism_over_n_steps(self, random_movement_source: str) -> None:
        """Executing N steps with same seed should give same sequence."""
        pool = GenomeCodePool()
        component_id = pool.add_component(
            kind="movement_policy",
            name="Random Movement",
            source=random_movement_source,
        )

        observation = {"nearest_food_vector": {"x": 1.0, "y": 0.0}}
        n_steps = 100
        seed = 999

        # Run first sequence
        rng1 = create_deterministic_rng(seed)
        sequence1 = []
        for _ in range(n_steps):
            result = pool.execute_policy(component_id, observation, rng1)
            sequence1.append(result.output)

        # Run second sequence with same seed
        rng2 = create_deterministic_rng(seed)
        sequence2 = []
        for _ in range(n_steps):
            result = pool.execute_policy(component_id, observation, rng2)
            sequence2.append(result.output)

        assert sequence1 == sequence2, "Sequences diverged despite same seed"

    def test_dt_affects_output_deterministically(self) -> None:
        """dt parameter should affect output deterministically."""
        # Policy that explicitly uses dt parameter
        dt_source = """
def policy(observation, rng):
    dt = observation.get("dt", 1.0)
    base_speed = 0.5
    return (base_speed * dt, 0.0)
"""
        pool = GenomeCodePool()
        component_id = pool.add_component(
            kind="movement_policy",
            name="DT Aware",
            source=dt_source,
        )

        # dt=1.0
        rng1 = create_deterministic_rng(42)
        obs1 = {"dt": 1.0}
        result1 = pool.execute_policy(component_id, obs1, rng1, dt=1.0)

        # dt=2.0 - pass dt both in observation and as parameter
        rng2 = create_deterministic_rng(42)
        obs2 = {"dt": 2.0}
        result2 = pool.execute_policy(component_id, obs2, rng2, dt=2.0)

        assert result1.success and result2.success
        vx1, _ = result1.output
        vx2, _ = result2.output
        # vx1 = 0.5 * 1.0 = 0.5, vx2 = 0.5 * 2.0 = 1.0
        assert vx1 == 0.5
        assert vx2 == 1.0

    def test_fork_rng_independence(self) -> None:
        """Forked RNG should be deterministic but independent."""
        parent_rng = create_deterministic_rng(42)

        # Fork twice with same parent state
        parent_state = parent_rng.getstate()
        child1 = fork_rng(parent_rng)
        parent_rng.setstate(parent_state)
        child2 = fork_rng(parent_rng)

        # Children should produce same sequences
        seq1 = [child1.random() for _ in range(10)]
        seq2 = [child2.random() for _ in range(10)]
        assert seq1 == seq2

    def test_validate_rng_determinism_helper(self, simple_movement_source: str) -> None:
        """Test the validate_rng_determinism helper function."""
        pool = CodePool()
        component_id = pool.add_component(
            kind="movement_policy",
            name="Simple",
            source=simple_movement_source,
        )
        func = pool.get_callable(component_id)
        assert func is not None

        observation = {"nearest_food_vector": {"x": 1.0, "y": 0.0}}
        assert validate_rng_determinism(func, observation, seed=42, num_trials=5)


# =============================================================================
# Test: Safety - AST Limits, Source Limits, Action Clamping
# =============================================================================


class TestSafety:
    """Test safety mechanisms."""

    def test_source_too_long_rejected(self) -> None:
        """Source exceeding max length should be rejected."""
        long_source = "def policy(obs, rng):\n" + "    x = 1\n" * 10000
        with pytest.raises(ValidationError, match="Source too long"):
            parse_and_validate(long_source, max_source_length=100)

    def test_ast_too_complex_rejected(self) -> None:
        """AST exceeding max nodes should be rejected."""
        # Many statements = many nodes
        complex_source = "def policy(obs, rng):\n"
        for i in range(100):
            complex_source += f"    x{i} = {i}\n"
        complex_source += "    return (0.0, 0.0)\n"

        with pytest.raises(ValidationError, match="AST too complex"):
            parse_and_validate(complex_source, max_ast_nodes=50)

    def test_function_nesting_too_deep_rejected(self) -> None:
        """Function nesting exceeding max depth should be rejected."""
        # Create deeply nested functions (7 levels deep)
        nested_source = """
def policy(obs, rng):
    def inner1():
        def inner2():
            def inner3():
                def inner4():
                    return (0.0, 0.0)
                return inner4()
            return inner3()
        return inner2()
    return inner1()
"""
        # This has 5 function levels, should fail with max_function_depth=2
        with pytest.raises(ValidationError, match="nesting too deep"):
            parse_and_validate(nested_source, max_function_depth=2)

    def test_output_clamping(self) -> None:
        """Policy outputs should be clamped to valid range."""
        pool = GenomeCodePool()

        # Policy that returns values outside [-1, 1]
        component_id = pool.add_component(
            kind="movement_policy",
            name="Overflow",
            source="""
def policy(obs, rng):
    return (5.0, -10.0)
""",
        )

        rng = create_deterministic_rng(42)
        vx, vy = pool.execute_movement_policy(
            GenomePolicySet(component_ids={"movement_policy": component_id}),
            {},
            rng,
        )

        # Should be clamped
        assert vx == 1.0, f"vx not clamped: {vx}"
        assert vy == -1.0, f"vy not clamped: {vy}"

    def test_nan_and_inf_handled(self) -> None:
        """NaN and Inf outputs should be handled safely."""
        pool = GenomeCodePool()

        component_id = pool.add_component(
            kind="movement_policy",
            name="BadOutput",
            source="""
def policy(obs, rng):
    return (float('nan'), float('inf'))
""",
        )

        rng = create_deterministic_rng(42)
        vx, vy = pool.execute_movement_policy(
            GenomePolicySet(component_ids={"movement_policy": component_id}),
            {},
            rng,
        )

        # Should be replaced with safe values
        assert vx == 0.0, f"NaN not handled: {vx}"
        assert vy == 0.0, f"Inf not handled: {vy}"

    def test_safety_config_customization(self) -> None:
        """SafetyConfig should allow customization of limits."""
        config = SafetyConfig(
            max_source_length=500,
            max_ast_nodes=100,
            max_recursion_depth=25,
        )

        pool = GenomeCodePool(safety_config=config)
        assert pool._safety_config.max_source_length == 500
        assert pool._safety_config.max_ast_nodes == 100
        assert pool._safety_config.max_recursion_depth == 25


# =============================================================================
# Test: Crossover - Combines Parent Policies
# =============================================================================


class TestCrossover:
    """Test crossover of parent policy sets."""

    def test_crossover_inherits_from_parents(self, genome_code_pool: GenomeCodePool) -> None:
        """Crossover should inherit policies from one of the parents."""
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")
        assert len(movement_ids) >= 2

        parent1 = GenomePolicySet()
        parent1.set_policy("movement_policy", movement_ids[0], {"speed": 1.0})

        parent2 = GenomePolicySet()
        parent2.set_policy("movement_policy", movement_ids[1], {"speed": 0.5})

        # Crossover many times - should get policies from both parents
        got_from_p1 = False
        got_from_p2 = False

        for seed in range(100):
            rng = random.Random(seed)
            child = genome_code_pool.crossover_policy_sets(parent1, parent2, rng)
            child_id = child.get_component_id("movement_policy")

            if child_id == movement_ids[0]:
                got_from_p1 = True
            elif child_id == movement_ids[1]:
                got_from_p2 = True

            if got_from_p1 and got_from_p2:
                break

        assert got_from_p1, "Never inherited from parent1"
        assert got_from_p2, "Never inherited from parent2"

    def test_crossover_blends_params(self, genome_code_pool: GenomeCodePool) -> None:
        """Crossover should blend parameters from both parents."""
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")

        parent1 = GenomePolicySet()
        parent1.set_policy("movement_policy", movement_ids[0], {"speed": 1.0})

        parent2 = GenomePolicySet()
        parent2.set_policy("movement_policy", movement_ids[0], {"speed": 0.0})

        # With weight1=0.5, params should blend to ~0.5
        rng = random.Random(42)
        child = genome_code_pool.crossover_policy_sets(parent1, parent2, rng, weight1=0.5)

        child_params = child.get_params("movement_policy")
        assert "speed" in child_params
        assert child_params["speed"] == pytest.approx(0.5, abs=0.01)

    def test_crossover_weighted_inheritance(self, genome_code_pool: GenomeCodePool) -> None:
        """Weight parameter should bias inheritance toward one parent."""
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")
        assert len(movement_ids) >= 2

        parent1 = GenomePolicySet()
        parent1.set_policy("movement_policy", movement_ids[0])

        parent2 = GenomePolicySet()
        parent2.set_policy("movement_policy", movement_ids[1])

        # With weight1=0.9, should almost always get parent1's policy
        p1_count = 0
        for seed in range(100):
            rng = random.Random(seed)
            child = genome_code_pool.crossover_policy_sets(parent1, parent2, rng, weight1=0.9)
            if child.get_component_id("movement_policy") == movement_ids[0]:
                p1_count += 1

        # Should get parent1's policy most of the time
        assert p1_count > 80, f"Only got parent1's policy {p1_count}/100 times"

    def test_crossover_handles_missing_policies(self, genome_code_pool: GenomeCodePool) -> None:
        """Crossover should handle parents with missing policies."""
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")

        parent1 = GenomePolicySet()
        parent1.set_policy("movement_policy", movement_ids[0])

        parent2 = GenomePolicySet()
        # parent2 has no movement policy

        rng = random.Random(42)
        child = genome_code_pool.crossover_policy_sets(parent1, parent2, rng)

        # Child should inherit from parent1
        child_id = child.get_component_id("movement_policy")
        assert child_id == movement_ids[0] or child_id is None


# =============================================================================
# Test: GenomePolicySet Operations
# =============================================================================


class TestGenomePolicySet:
    """Test GenomePolicySet basic operations."""

    def test_set_and_get_policy(self) -> None:
        """Should be able to set and get policies."""
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", "uuid-123", {"speed": 0.5})

        assert policy_set.get_component_id("movement_policy") == "uuid-123"
        assert policy_set.get_params("movement_policy") == {"speed": 0.5}

    def test_has_policy(self) -> None:
        """has_policy should correctly detect policies."""
        policy_set = GenomePolicySet()
        assert not policy_set.has_policy("movement_policy")

        policy_set.set_policy("movement_policy", "uuid-123")
        assert policy_set.has_policy("movement_policy")

    def test_clone(self) -> None:
        """clone should create independent copy."""
        original = GenomePolicySet()
        original.set_policy("movement_policy", "uuid-123", {"speed": 0.5})

        cloned = original.clone()

        # Modify clone
        cloned.set_policy("movement_policy", "uuid-456", {"speed": 1.0})

        # Original should be unchanged
        assert original.get_component_id("movement_policy") == "uuid-123"
        assert original.get_params("movement_policy") == {"speed": 0.5}

    def test_serialization_round_trip(self) -> None:
        """to_dict/from_dict should preserve all data."""
        original = GenomePolicySet()
        original.set_policy("movement_policy", "uuid-123", {"speed": 0.5})
        original.set_policy("poker_policy", "uuid-456", {"aggression": 0.8})

        data = original.to_dict()
        restored = GenomePolicySet.from_dict(data)

        assert restored.get_component_id("movement_policy") == "uuid-123"
        assert restored.get_component_id("poker_policy") == "uuid-456"
        assert restored.get_params("movement_policy") == {"speed": 0.5}
        assert restored.get_params("poker_policy") == {"aggression": 0.8}

    def test_invalid_policy_kind_rejected(self) -> None:
        """Setting an unknown policy kind should raise ValueError."""
        policy_set = GenomePolicySet()
        with pytest.raises(ValueError, match="Unknown policy kind"):
            policy_set.set_policy("invalid_kind", "uuid-123")


# =============================================================================
# Test: Integration - Fish with CodePool Component
# =============================================================================


class TestIntegration:
    """Integration tests for fish using CodePool components."""

    def test_fish_can_use_codepool_movement(
        self, genome_code_pool: GenomeCodePool, simple_movement_source: str
    ) -> None:
        """A fish should be able to use a CodePool component for movement."""
        # This test verifies the acceptance criteria:
        # "A fish can be created whose movement comes from a CodePool component
        # referenced by genome."

        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")
        assert len(movement_ids) > 0

        # Create a policy set for a fish
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", movement_ids[0])

        # Execute the movement policy
        observation = {
            "nearest_food_vector": {"x": 1.0, "y": 0.5},
            "dt": 1.0,
        }
        rng = create_deterministic_rng(42)

        vx, vy = genome_code_pool.execute_movement_policy(policy_set, observation, rng, dt=1.0)

        # Should return valid movement direction
        assert -1.0 <= vx <= 1.0
        assert -1.0 <= vy <= 1.0

    def test_mutation_crossover_produces_valid_genomes(
        self, genome_code_pool: GenomeCodePool
    ) -> None:
        """Mutation/crossover should produce valid genomes (acceptance criteria)."""
        movement_ids = genome_code_pool.get_components_by_kind("movement_policy")

        # Create two parent genomes
        parent1 = GenomePolicySet()
        parent1.set_policy("movement_policy", movement_ids[0], {"speed": 0.8})

        parent2 = GenomePolicySet()
        parent2.set_policy("movement_policy", movement_ids[1], {"speed": 0.3})

        rng = random.Random(42)

        # Crossover
        child = genome_code_pool.crossover_policy_sets(parent1, parent2, rng)

        # Mutate
        mutated = genome_code_pool.mutate_policy_set(child, rng, mutation_rate=0.5)

        # Validate
        validated = genome_code_pool.ensure_valid_policies(mutated, rng)

        # Check validity
        movement_id = validated.get_component_id("movement_policy")
        if movement_id is not None:
            assert genome_code_pool.has_component(
                movement_id
            ), f"Invalid component ID after mutation/crossover: {movement_id}"

    def test_determinism_across_steps(self, genome_code_pool: GenomeCodePool) -> None:
        """Same seed should produce same actions for N steps (acceptance criteria)."""
        # Add a policy that uses RNG (math module is available in sandbox globals)
        component_id = genome_code_pool.add_component(
            kind="movement_policy",
            name="Random Walker",
            source="""
def policy(observation, rng):
    angle = rng.random() * 6.28
    vx = math.cos(angle)
    vy = math.sin(angle)
    return (vx, vy)
""",
        )

        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", component_id)

        observation = {"dt": 1.0}
        n_steps = 50
        seed = 777

        # Run sequence 1
        rng1 = create_deterministic_rng(seed)
        seq1 = []
        for step in range(n_steps):
            result = genome_code_pool.execute_policy(component_id, observation, rng1, dt=1.0)
            seq1.append(result.output)

        # Run sequence 2 with same seed
        rng2 = create_deterministic_rng(seed)
        seq2 = []
        for step in range(n_steps):
            result = genome_code_pool.execute_policy(component_id, observation, rng2, dt=1.0)
            seq2.append(result.output)

        # Verify determinism
        assert seq1 == seq2, "Sequences diverged - determinism test failed"
