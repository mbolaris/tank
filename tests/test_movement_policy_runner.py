"""Tests for the movement policy runner."""

import random
from unittest.mock import MagicMock

import pytest

from core.code_pool import GenomeCodePool
from core.math_utils import Vector2
from core.policies.interfaces import MovementAction
from core.policies.movement_policy_runner import run_movement_policy


@pytest.fixture
def mock_genome():
    genome = MagicMock()
    # Configure for new per-kind policy fields
    genome.behavioral.movement_policy_id.value = "test_policy_id"
    genome.behavioral.movement_policy_params.value = None
    # Also set legacy fields for backward compatibility testing
    genome.behavioral.code_policy_kind.value = "movement_policy"
    genome.behavioral.code_policy_component_id.value = "test_policy_id"
    genome.behavioral.code_policy_params.value = None
    return genome


@pytest.fixture
def mock_code_pool():
    pool = MagicMock(spec=GenomeCodePool)
    return pool


def test_run_movement_policy_success(mock_genome, mock_code_pool):
    """Test successful execution returning tuple."""
    # Setup successful execution result
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = (0.5, -0.5)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    obs = {"dt": 1.0}

    result = run_movement_policy(mock_genome, mock_code_pool, obs, rng)

    assert result == (0.5, -0.5)
    mock_code_pool.execute_policy.assert_called_once()
    args = mock_code_pool.execute_policy.call_args
    assert args.kwargs["component_id"] == "test_policy_id"


def test_run_movement_policy_success_movement_action(mock_genome, mock_code_pool):
    """Test successful execution returning MovementAction."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = MovementAction(0.8, 0.2)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    obs = {"dt": 1.0}

    result = run_movement_policy(mock_genome, mock_code_pool, obs, rng)
    assert result == (0.8, 0.2)


def test_run_movement_policy_success_vector2(mock_genome, mock_code_pool):
    """Test successful execution returning Vector2."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = Vector2(0.1, 0.1)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    obs = {"dt": 1.0}

    result = run_movement_policy(mock_genome, mock_code_pool, obs, rng)
    assert result == (0.1, 0.1)


def test_run_movement_policy_clamping(mock_genome, mock_code_pool):
    """Test that outputs are clamped to [-1, 1]."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = (2.0, -50.0)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    obs = {"dt": 1.0}

    result = run_movement_policy(mock_genome, mock_code_pool, obs, rng)
    assert result == (1.0, -1.0)


def test_run_movement_policy_invalid_kind(mock_genome, mock_code_pool):
    """Test early return if no movement policy is set."""
    # Clear both new and legacy fields
    mock_genome.behavioral.movement_policy_id.value = None
    mock_genome.behavioral.code_policy_kind.value = "soccer_policy"

    rng = random.Random(42)
    result = run_movement_policy(mock_genome, mock_code_pool, {}, rng)

    assert result is None
    mock_code_pool.execute_policy.assert_not_called()


def test_run_movement_policy_execution_failure(mock_genome, mock_code_pool):
    """Test fallback when execution fails."""
    execution_result = MagicMock()
    execution_result.success = False
    execution_result.error_message = "Runtime Error"
    execution_result.output = None
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    result = run_movement_policy(mock_genome, mock_code_pool, {}, rng)

    assert result is None


def test_run_movement_policy_invalid_output_type(mock_genome, mock_code_pool):
    """Test fallback on invalid output type."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = "not a vector"
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    result = run_movement_policy(mock_genome, mock_code_pool, {}, rng)

    assert result is None


def test_run_movement_policy_nan_check(mock_genome, mock_code_pool):
    """Test fallback on NaN values."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = (float("nan"), 0.5)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    result = run_movement_policy(mock_genome, mock_code_pool, {}, rng)

    assert result is None


def test_movement_policy_error_logs_rate_limited_by_age(mock_genome, mock_code_pool, caplog):
    """Test that error logs are rate-limited by frame bucket when age is present."""
    from core.policies.movement_policy_runner import _reset_error_log_state_for_tests

    _reset_error_log_state_for_tests()

    # Setup failing execution result
    execution_result = MagicMock()
    execution_result.success = False
    execution_result.error_message = "Test error"
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)

    # Call multiple times within the same 60-frame bucket (ages 0, 1, 2, 59)
    # Should only log once per bucket
    caplog.clear()
    for age in [0, 1, 2, 59]:
        obs = {"dt": 1.0, "age": age}
        run_movement_policy(mock_genome, mock_code_pool, obs, rng, fish_id=1)

    warning_count = sum(1 for r in caplog.records if r.levelname == "WARNING")
    assert warning_count == 1, f"Expected 1 warning in bucket 0, got {warning_count}"

    # Call at age 60 (new bucket), should trigger second log
    caplog.clear()
    obs = {"dt": 1.0, "age": 60}
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, fish_id=1)

    warning_count = sum(1 for r in caplog.records if r.levelname == "WARNING")
    assert warning_count == 1, f"Expected 1 warning in bucket 1, got {warning_count}"


def test_movement_policy_error_logs_not_rate_limited_without_age(
    mock_genome, mock_code_pool, caplog
):
    """Test that error logs are NOT rate-limited when age is missing (makes missing metadata obvious)."""
    from core.policies.movement_policy_runner import _reset_error_log_state_for_tests

    _reset_error_log_state_for_tests()

    # Setup failing execution result
    execution_result = MagicMock()
    execution_result.success = False
    execution_result.error_message = "Test error"
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)

    # Call twice without age - should log both times
    caplog.clear()
    obs = {"dt": 1.0}  # No "age" key
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, fish_id=1)
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, fish_id=1)

    warning_count = sum(1 for r in caplog.records if r.levelname == "WARNING")
    assert warning_count == 2, f"Expected 2 warnings without rate limiting, got {warning_count}"


def test_explicit_frame_parameter_used_for_rate_limiting(mock_genome, mock_code_pool, caplog):
    """Test that explicit frame parameter is used for rate limiting over observation age."""
    from core.policies.movement_policy_runner import _reset_error_log_state_for_tests

    _reset_error_log_state_for_tests()

    # Setup failing execution result
    execution_result = MagicMock()
    execution_result.success = False
    execution_result.error_message = "Test error"
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)

    # Observation has age=100 (bucket 1), but explicit frame=0 (bucket 0)
    # If explicit frame is used, calls within the same bucket should be rate-limited
    caplog.clear()
    obs = {"age": 100}  # Would be bucket 1
    run_movement_policy(
        mock_genome, mock_code_pool, obs, rng, fish_id=1, frame=0
    )  # Explicit bucket 0
    run_movement_policy(
        mock_genome, mock_code_pool, obs, rng, fish_id=1, frame=30
    )  # Still bucket 0

    warning_count = sum(1 for r in caplog.records if r.levelname == "WARNING")
    assert (
        warning_count == 1
    ), f"Expected 1 warning (rate limited by explicit frame), got {warning_count}"

    # Call with frame=60 (bucket 1), should trigger new log
    caplog.clear()
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, fish_id=1, frame=60)
    warning_count = sum(1 for r in caplog.records if r.levelname == "WARNING")
    assert warning_count == 1, f"Expected 1 warning in new bucket, got {warning_count}"


def test_explicit_frame_falls_back_to_observation_age(mock_genome, mock_code_pool, caplog):
    """Test that when frame is None, observation['age'] is used for rate limiting."""
    from core.policies.movement_policy_runner import _reset_error_log_state_for_tests

    _reset_error_log_state_for_tests()

    # Setup failing execution result
    execution_result = MagicMock()
    execution_result.success = False
    execution_result.error_message = "Test error"
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)

    # Call without explicit frame - should fall back to observation["age"]
    caplog.clear()
    obs = {"age": 10}  # Bucket 0
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, fish_id=1, frame=None)
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, fish_id=1)  # frame defaults to None

    warning_count = sum(1 for r in caplog.records if r.levelname == "WARNING")
    assert warning_count == 1, f"Expected 1 warning (rate limited by obs age), got {warning_count}"


def test_explicit_dt_forwarded_to_execute_policy(mock_genome, mock_code_pool):
    """Test that explicit dt parameter is forwarded to GenomeCodePool.execute_policy."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = (0.5, 0.5)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    obs = {}

    # Call with explicit dt=0.1
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, dt=0.1)

    # Verify execute_policy was called with dt=0.1
    mock_code_pool.execute_policy.assert_called_once()
    call_kwargs = mock_code_pool.execute_policy.call_args.kwargs
    assert call_kwargs["dt"] == 0.1, f"Expected dt=0.1, got dt={call_kwargs['dt']}"


def test_dt_defaults_to_1_when_not_provided(mock_genome, mock_code_pool):
    """Test that dt defaults to 1.0 when not explicitly provided."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = (0.5, 0.5)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    obs = {}

    # Call without explicit dt
    run_movement_policy(mock_genome, mock_code_pool, obs, rng)

    # Verify execute_policy was called with dt=1.0
    mock_code_pool.execute_policy.assert_called_once()
    call_kwargs = mock_code_pool.execute_policy.call_args.kwargs
    assert call_kwargs["dt"] == 1.0, f"Expected dt=1.0, got dt={call_kwargs['dt']}"


def test_dt_not_read_from_observation(mock_genome, mock_code_pool):
    """Test that dt is NOT read from observation (uses explicit param only)."""
    execution_result = MagicMock()
    execution_result.success = True
    execution_result.output = (0.5, 0.5)
    mock_code_pool.execute_policy.return_value = execution_result

    rng = random.Random(42)
    obs = {"dt": 999.0}  # This should be ignored

    # Call with explicit dt=0.5 while observation has dt=999.0
    run_movement_policy(mock_genome, mock_code_pool, obs, rng, dt=0.5)

    # Verify execute_policy was called with the explicit dt=0.5, not obs dt=999.0
    call_kwargs = mock_code_pool.execute_policy.call_args.kwargs
    assert call_kwargs["dt"] == 0.5, f"Expected explicit dt=0.5, got dt={call_kwargs['dt']}"
