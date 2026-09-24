"""Tests for the Champions Tank noise-study statistics (core/research/arena_noise.py)."""

import random

import pytest

from core.research.arena_noise import (
    admission_margin,
    kendalls_w,
    paired_difference_sd,
    permutation_p_value,
    select_seed_pack,
    sign_test_p,
    split_half_reliability,
    summarize_pair,
    variance_decomposition,
    verdict,
)


def _identity_matrix(houses: int, seeds: int) -> list[list[float]]:
    """Each house has a fixed share and every seed agrees exactly."""
    return [[(h + 1) / 100 for _ in range(seeds)] for h in range(houses)]


def test_identity_dominated_matrix_reads_as_pure_house_effect():
    shares = _identity_matrix(10, 8)

    decomposition = variance_decomposition(shares)

    assert decomposition["ms_within"] == pytest.approx(0.0, abs=1e-20)
    assert decomposition["icc1"] == pytest.approx(1.0)
    assert decomposition["eta_squared"] == pytest.approx(1.0)
    assert kendalls_w(shares) == pytest.approx(1.0)
    assert split_half_reliability(shares) == pytest.approx(1.0)
    assert permutation_p_value(shares, 200, random.Random(0)) < 0.01


def test_exchangeable_houses_read_as_noise():
    rng = random.Random(3)
    shares = [[rng.random() / 10 for _ in range(20)] for _ in range(10)]

    decomposition = variance_decomposition(shares)

    assert decomposition["icc1"] < 0.2
    assert kendalls_w(shares) < 0.2
    assert permutation_p_value(shares, 500, random.Random(0)) > 0.01
    assert verdict({"variance": decomposition, "permutation_p": 0.5}) == "redesign"


def test_paired_difference_sd_ignores_shared_seed_effects():
    # Every house moves up and down together with the seed; the pairwise gap is constant.
    seed_effect = [0.0, 0.05, -0.03, 0.02]
    shares = [[base + e for e in seed_effect] for base in (0.1, 0.2, 0.3)]

    assert paired_difference_sd(shares) == pytest.approx(0.0, abs=1e-12)


def test_admission_margin_shrinks_with_root_seeds():
    assert admission_margin(0.04, 4) == pytest.approx(2 * admission_margin(0.04, 16))


def test_select_seed_pack_takes_medoid_then_farthest_points():
    positions = {1: 0.0, 2: 1.0, 3: 2.0, 4: 3.0, 5: 4.0, 6: 10.0}

    pack = select_seed_pack(list(positions), lambda a, b: abs(positions[a] - positions[b]), 3)

    medoid = 3  # smallest summed distance, ties broken by the smaller id
    assert pack[0] == medoid
    assert pack[1] == 6  # farthest from the medoid
    assert pack[2] == 1  # farthest from both picks so far
    assert len(set(pack)) == 3


def test_select_seed_pack_keeps_small_taxa_whole():
    assert select_seed_pack([9, 4, 7], lambda a, b: 1.0, 5) == [4, 7, 9]


@pytest.mark.parametrize(
    ("icc", "p", "expected"),
    [
        (0.7, 0.001, "proceed"),
        (0.3, 0.001, "proceed_with_more_seeds"),
        (0.1, 0.001, "redesign"),
        (0.9, 0.2, "redesign"),
    ],
)
def test_verdict_applies_pre_registered_thresholds(icc, p, expected):
    assert verdict({"variance": {"icc1": icc}, "permutation_p": p}) == expected


def test_sign_test_matches_exact_binomial():
    assert sign_test_p(6, 0) == pytest.approx(2 / 64)
    assert sign_test_p(3, 3) == pytest.approx(1.0)
    assert sign_test_p(0, 0) == 1.0


def test_summarize_pair_counts_wins_and_ties():
    summary = summarize_pair([0.9, 0.6, 0.0, 0.7], [0.1, 0.4, 0.0, 0.3])

    assert (summary["wins"], summary["losses"], summary["ties"]) == (3, 0, 1)
    assert summary["majority_agreement"] == 1.0
    assert summary["mean_difference"] == pytest.approx(0.35)
