"""Tests for the non-AI research control arm without running long benchmarks."""

from __future__ import annotations

import pytest

from tools.non_ai_baseline import majority_improvement, parse_seeds


def _result(scores: dict[str, float]) -> dict[str, object]:
    values = list(scores.values())
    return {
        "seed": int(next(iter(scores))),
        "seeds": [int(seed) for seed in scores],
        "score": sum(values) / len(values),
        "per_seed": {seed: {"score": score} for seed, score in scores.items()},
    }


def test_parse_seeds_requires_unique_integer_matrix() -> None:
    assert parse_seeds("42, 7,123") == (42, 7, 123)
    with pytest.raises(ValueError, match="duplicates"):
        parse_seeds("42,7,42")
    with pytest.raises(ValueError, match="at least one"):
        parse_seeds(",")


def test_majority_improvement_requires_mean_and_seed_majority() -> None:
    reference = _result({"42": 10.0, "7": 10.0, "123": 10.0})
    assert majority_improvement(_result({"42": 11.0, "7": 12.0, "123": 9.0}), reference)
    assert not majority_improvement(_result({"42": 11.0, "7": 9.0, "123": 9.0}), reference)


def test_majority_improvement_rejects_catastrophic_seed_regression() -> None:
    reference = _result({"42": 10.0, "7": 10.0, "123": 10.0})
    candidate = _result({"42": 12.0, "7": 12.0, "123": 8.0})
    assert not majority_improvement(candidate, reference)
