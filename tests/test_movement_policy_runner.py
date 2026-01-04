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
    # Configure mostly valid defaults
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
    """Test early return if policy kind is wrong."""
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
