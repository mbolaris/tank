"""Guards validate_reproduction.py against matrix-format champions.

Motivation
----------
``champions/tank/survival_5k.json`` stores a 3-seed matrix: the top-level
``score`` is the *mean* across seeds 42/7/123, with each seed's own score
under ``per_seed``. But ``tools/verify_all_champions.py`` only ever runs a
*single* seed (the champion's primary seed) and handed that single-seed
result straight to ``validate_reproduction`` for comparison against the
top-level mean - so a matrix-format champion could never pass verification,
regardless of whether the recorded scores were correct. This sat unnoticed
because the nightly ``verify-champions`` job had already been red for other
reasons; see the champion re-baseline that uncovered this (commit history
around 2026-07-28/29).

These tests are pure data-comparison, no simulation, so they run in the
ordinary PR gates.
"""

from __future__ import annotations

from tools.validate_reproduction import validate_reproduction


def test_matrix_champion_compares_against_own_seed_not_mean() -> None:
    champion_record = {
        "score": 741.7865637960541,  # mean of 3 seeds
        "seed": 42,
        "config_hash": "abc123",
        "metadata": {"frames": 5000},
        "per_seed": {
            "42": {
                "score": 770.5569025783376,
                "config_hash": "abc123",
                "metadata": {"frames": 5000, "avg_pop": 51.9226},
            },
            "7": {"score": 682.5605890314287, "config_hash": "abc123", "metadata": {}},
            "123": {"score": 772.2421997783963, "config_hash": "abc123", "metadata": {}},
        },
    }
    single_seed_result = {
        "seed": 42,
        "score": 770.5569025783376,
        "config_hash": "abc123",
        "metadata": {"frames": 5000, "avg_pop": 51.9226},
    }

    assert validate_reproduction(single_seed_result, champion_record) is True


def test_matrix_champion_still_detects_real_mismatch() -> None:
    champion_record = {
        "score": 741.7865637960541,
        "seed": 42,
        "config_hash": "abc123",
        "metadata": {},
        "per_seed": {
            "42": {"score": 770.5569025783376, "config_hash": "abc123", "metadata": {}},
        },
    }
    drifted_result = {
        "seed": 42,
        "score": 999.0,
        "config_hash": "abc123",
        "metadata": {},
    }

    assert validate_reproduction(drifted_result, champion_record) is False


def test_flat_champion_without_per_seed_is_unaffected() -> None:
    champion_record = {
        "score": 12.006686634858294,
        "seed": 42,
        "config_hash": "def456",
        "metadata": {"frames": 10000},
    }
    single_seed_result = {
        "seed": 42,
        "score": 12.006686634858294,
        "config_hash": "def456",
        "metadata": {"frames": 10000},
    }

    assert validate_reproduction(single_seed_result, champion_record) is True
