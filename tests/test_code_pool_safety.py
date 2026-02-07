"""Tests for code pool safety and sandboxing.

Verifies that:
- Malicious code is blocked at validation time
- Runtime safety limits are enforced
- Policies are deterministic across executions
- No file/network/OS access is possible
"""

import random

import pytest

from core.code_pool import (CodePool, ValidationError,
                            create_default_genome_code_pool,
                            validate_source_safety)
from core.code_pool.safety import SafetyConfig, SourceTooLongError


class TestSandboxValidation:
    """Test AST-level validation catches dangerous code."""

    def test_import_is_blocked(self):
        """Code attempting to import modules should be rejected."""
        dangerous_code = """
def policy(observation, rng):
    import os
    os.system("rm -rf /")
    return (0.0, 0.0)
"""
        with pytest.raises(ValidationError, match="import"):
            validate_source_safety(dangerous_code, SafetyConfig())

    def test_open_is_blocked(self):
        """Code attempting file I/O should be rejected."""
        dangerous_code = """
def policy(observation, rng):
    with open("/etc/passwd", "r") as f:
        data = f.read()
    return (0.0, 0.0)
"""
        with pytest.raises(ValidationError, match="open"):
            validate_source_safety(dangerous_code, SafetyConfig())

    def test_exec_is_blocked(self):
        """Code attempting exec/eval should be rejected."""
        dangerous_code = """
def policy(observation, rng):
    exec("import os; os.system('evil')")
    return (0.0, 0.0)
"""
        with pytest.raises(ValidationError, match="exec"):
            validate_source_safety(dangerous_code, SafetyConfig())

    def test_while_loop_is_blocked(self):
        """Infinite loops should be blocked at parse time."""
        dangerous_code = """
def policy(observation, rng):
    while True:
        pass
    return (0.0, 0.0)
"""
        with pytest.raises(ValidationError, match="while"):
            validate_source_safety(dangerous_code, SafetyConfig())

    def test_lambda_is_blocked(self):
        """Lambdas should be blocked to prevent code injection."""
        dangerous_code = """
def policy(observation, rng):
    f = lambda x: x * 2
    return (f(1.0), 0.0)
"""
        with pytest.raises(ValidationError, match="lambda"):
            validate_source_safety(dangerous_code, SafetyConfig())

    def test_list_comprehension_is_blocked(self):
        """List comprehensions should be blocked for safety."""
        dangerous_code = """
def policy(observation, rng):
    data = [x * 2 for x in range(1000000)]
    return (0.0, 0.0)
"""
        with pytest.raises(ValidationError, match="comprehension"):
            validate_source_safety(dangerous_code, SafetyConfig())

    def test_class_definition_is_blocked(self):
        """Class definitions should be blocked."""
        dangerous_code = """
class Evil:
    def __init__(self):
        pass

def policy(observation, rng):
    return (0.0, 0.0)
"""
        with pytest.raises(ValidationError, match="class"):
            validate_source_safety(dangerous_code, SafetyConfig())

    def test_source_length_limit(self):
        """Extremely long source code should be rejected."""
        # Create source that exceeds 10,000 character limit
        long_code = "def policy(observation, rng):\n" + "    x = 1.0\n" * 5000
        with pytest.raises(SourceTooLongError):
            validate_source_safety(long_code, SafetyConfig())


class TestAllowedOperations:
    """Test that safe operations are allowed."""

    def test_basic_math_is_allowed(self):
        """Simple math operations should work."""
        safe_code = """
def policy(observation, rng):
    x = 1.0 + 2.0
    y = 3.0 * 4.0
    z = y / 2.0
    return (x, z)
"""
        # Should not raise
        validate_source_safety(safe_code, SafetyConfig())

        pool = CodePool()
        component_id = pool.add_component(
            kind="movement_policy", name="math_test", source=safe_code, entrypoint="policy"
        )

        func = pool.get_callable(component_id)
        assert func is not None

        result = func({}, random.Random())
        assert result == (3.0, 6.0)

    def test_if_statements_are_allowed(self):
        """Conditional logic should work."""
        safe_code = """
def policy(observation, rng):
    x = observation.get("energy", 0.0)
    if x > 50.0:
        return (1.0, 0.0)
    else:
        return (0.0, 1.0)
"""
        validate_source_safety(safe_code, SafetyConfig())

        pool = CodePool()
        component_id = pool.add_component(
            kind="movement_policy", name="conditional", source=safe_code, entrypoint="policy"
        )

        func = pool.get_callable(component_id)
        assert func is not None

        # Test both branches
        result1 = func({"energy": 60.0}, random.Random())
        assert result1 == (1.0, 0.0)

        result2 = func({"energy": 30.0}, random.Random())
        assert result2 == (0.0, 1.0)

    def test_math_module_is_allowed(self):
        """Math module should be available."""
        safe_code = """
import math

def policy(observation, rng):
    angle = math.pi / 4.0
    x = math.cos(angle)
    y = math.sin(angle)
    return (x, y)
"""
        validate_source_safety(safe_code, SafetyConfig())

        pool = CodePool()
        component_id = pool.add_component(
            kind="movement_policy", name="trigonometry", source=safe_code, entrypoint="policy"
        )

        func = pool.get_callable(component_id)
        assert func is not None
        result = func({}, random.Random())

        # cos(π/4) ≈ sin(π/4) ≈ 0.707
        assert abs(result[0] - 0.707) < 0.01
        assert abs(result[1] - 0.707) < 0.01


class TestRuntimeSafety:
    """Test runtime safety limits."""

    def test_output_values_are_clamped(self):
        """Output values should be clamped to [-1, 1] for movement policies."""
        pool = create_default_genome_code_pool()

        # Policy that returns huge values
        large_code = """
def policy(observation, rng):
    return (1000.0, -500.0)
"""
        component_id = pool.add_component(
            kind="movement_policy",
            name="large_output",
            source=large_code,
            entrypoint="policy",
        )

        # Execute via GenomeCodePool (has clamping)
        from core.code_pool import GenomePolicySet

        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", component_id)

        vx, vy = pool.execute_movement_policy(
            policy_set=policy_set, observation={}, rng=random.Random(), dt=1.0
        )

        # Should be clamped to [-1, 1]
        assert vx == 1.0
        assert vy == -1.0

    def test_nan_values_are_handled(self):
        """NaN values should be replaced with safe defaults."""
        pool = create_default_genome_code_pool()

        nan_code = """
def policy(observation, rng):
    return (float('nan'), float('inf'))
"""
        component_id = pool.add_component(
            kind="movement_policy", name="nan_output", source=nan_code, entrypoint="policy"
        )

        from core.code_pool import GenomePolicySet

        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", component_id)

        vx, vy = pool.execute_movement_policy(
            policy_set=policy_set, observation={}, rng=random.Random(), dt=1.0
        )

        # NaN/Inf should be replaced with 0.0
        assert vx == 0.0
        assert vy == 0.0

    def test_exception_in_policy_is_caught(self):
        """Exceptions during execution should be caught and reported."""
        pool = create_default_genome_code_pool()

        error_code = """
def policy(observation, rng):
    x = 1.0 / 0.0  # Division by zero
    return (x, 0.0)
"""
        component_id = pool.add_component(
            kind="movement_policy", name="error_policy", source=error_code, entrypoint="policy"
        )

        result = pool.execute_policy(
            component_id=component_id, observation={}, rng=random.Random(), dt=1.0
        )

        # Should fail gracefully
        assert result.success is False
        assert result.error_message is not None


class TestDeterminism:
    """Test that policy execution is deterministic."""

    def test_same_seed_same_output(self):
        """Same RNG seed should produce identical results."""
        pool = create_default_genome_code_pool()

        # Policy that uses randomness
        random_code = """
def policy(observation, rng):
    x = rng.random()
    y = rng.gauss(0.0, 0.1)
    return (x, y)
"""
        component_id = pool.add_component(
            kind="movement_policy",
            name="random_policy",
            source=random_code,
            entrypoint="policy",
        )

        # Execute twice with same seed
        result1 = pool.execute_policy(
            component_id=component_id, observation={}, rng=random.Random(12345), dt=1.0
        )

        result2 = pool.execute_policy(
            component_id=component_id, observation={}, rng=random.Random(12345), dt=1.0
        )

        # Should be identical
        assert result1.success
        assert result2.success
        assert result1.output == result2.output

    def test_different_seed_different_output(self):
        """Different RNG seeds should produce different results."""
        pool = create_default_genome_code_pool()

        random_code = """
def policy(observation, rng):
    return (rng.random(), rng.random())
"""
        component_id = pool.add_component(
            kind="movement_policy",
            name="random_policy2",
            source=random_code,
            entrypoint="policy",
        )

        result1 = pool.execute_policy(
            component_id=component_id, observation={}, rng=random.Random(111), dt=1.0
        )

        result2 = pool.execute_policy(
            component_id=component_id, observation={}, rng=random.Random(999), dt=1.0
        )

        # Should be different
        assert result1.success
        assert result2.success
        assert result1.output != result2.output

    def test_dt_parameter_available(self):
        """Delta time should be available for frame-rate independence."""
        pool = create_default_genome_code_pool()

        dt_code = """
def policy(observation, rng):
    dt = observation.get("dt", 1.0)
    # Velocity scaled by delta time
    return (1.0 * dt, 0.5 * dt)
"""
        component_id = pool.add_component(
            kind="movement_policy", name="dt_policy", source=dt_code, entrypoint="policy"
        )

        # Execute with different dt values
        result1 = pool.execute_policy(
            component_id=component_id, observation={}, rng=random.Random(), dt=0.5
        )

        result2 = pool.execute_policy(
            component_id=component_id, observation={}, rng=random.Random(), dt=2.0
        )

        assert result1.output == (0.5, 0.25)  # 1.0 * 0.5, 0.5 * 0.5
        assert result2.output == (1.0, 1.0)  # Clamped to 1.0, 1.0


class TestParameterization:
    """Test that policies can be parameterized."""

    def test_policy_parameters_are_accessible(self):
        """Parameters should be passed to policy and accessible."""
        pool = create_default_genome_code_pool()

        parameterized_code = """
def policy(observation, rng):
    params = observation.get("params", {})
    aggression = params.get("aggression", 0.5)
    speed = params.get("speed", 1.0)
    return (aggression * speed, 0.0)
"""
        component_id = pool.add_component(
            kind="movement_policy",
            name="parameterized",
            source=parameterized_code,
            entrypoint="policy",
        )

        # Execute with different parameters
        params1 = {"aggression": 0.2, "speed": 2.0}
        result1 = pool.execute_policy(
            component_id=component_id,
            observation={},
            rng=random.Random(),
            dt=1.0,
            params=params1,
        )

        params2 = {"aggression": 0.8, "speed": 1.5}
        result2 = pool.execute_policy(
            component_id=component_id,
            observation={},
            rng=random.Random(),
            dt=1.0,
            params=params2,
        )

        assert result1.output == (0.4, 0.0)  # 0.2 * 2.0
        assert result2.output == (1.0, 0.0)  # 0.8 * 1.5, clamped to 1.0
