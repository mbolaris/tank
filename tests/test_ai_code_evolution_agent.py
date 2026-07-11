"""Regression tests for the AI evolution agent's validation matrix."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.ai_code_evolution_agent import parse_validation_seeds, summarize_validation_matrix


def _result(seed: int, passed: bool, improvement: float) -> SimpleNamespace:
    return SimpleNamespace(
        passed=passed,
        reason=f"seed {seed}",
        simulation_error=None,
        baseline_reproduction_rate=1.0,
        baseline_survival_rate=2.0,
        baseline_avg_lifespan=100.0,
        new_reproduction_rate=1.0 + improvement,
        new_survival_rate=2.0 + improvement,
        new_avg_lifespan=100.0 * (1.0 + improvement),
        improvement_reproduction=improvement,
        improvement_survival=improvement,
        improvement_lifespan=improvement,
    )


def test_parse_validation_seeds_requires_unique_three_seed_matrix():
    assert parse_validation_seeds("42, 7, 123") == (42, 7, 123)

    with pytest.raises(ValueError, match="at least three"):
        parse_validation_seeds("42,7")
    with pytest.raises(ValueError, match="unique"):
        parse_validation_seeds("42,7,42")


def test_validation_matrix_requires_majority_and_reports_dispersion():
    seeds = (42, 7, 123)
    summary = summarize_validation_matrix(
        [_result(42, True, 0.10), _result(7, True, 0.05), _result(123, False, -0.02)],
        seeds,
    )

    assert summary["passed"] is True
    assert summary["passed_count"] == 2
    assert summary["seeds"] == [42, 7, 123]
    assert summary["candidate_summary"]["reproduction_rate"]["mean"] == pytest.approx(1.043333)
    assert summary["candidate_summary"]["reproduction_rate"]["stdev"] > 0
    assert set(summary["per_seed"]) == {"42", "7", "123"}


def test_validation_matrix_rejects_without_majority():
    seeds = (42, 7, 123)
    summary = summarize_validation_matrix(
        [_result(42, True, 0.10), _result(7, False, -0.01), _result(123, False, -0.02)],
        seeds,
    )

    assert summary["passed"] is False
    assert "majority-of-seeds" in summary["reason"]
