"""Regression tests for the survival benchmark's ecological validity gate."""

from benchmarks.tank.survival_5k import MAX_VALID_STARVATION_RATE, calculate_score


def test_valid_starvation_rate_keeps_normal_score_contract():
    score, breakdown, valid, reason = calculate_score(
        avg_fish_energy=100.0,
        avg_fish_pop=20.0,
        max_generation=4,
        starvation_rate=0.5,
    )

    assert valid is True
    assert reason is None
    assert score == 2.4  # 2.0 raw score × 1.2 generation multiplier
    assert breakdown["validity_gate"] == 1.0


def test_starvation_at_validity_limit_scores_zero():
    score, breakdown, valid, reason = calculate_score(
        avg_fish_energy=100_000.0,
        avg_fish_pop=100.0,
        max_generation=100,
        starvation_rate=MAX_VALID_STARVATION_RATE,
    )

    assert score == 0.0
    assert breakdown["validity_gate"] == 0.0
    assert valid is False
    assert reason is not None
    assert "maximum valid rate" in reason


def test_total_starvation_cannot_produce_a_positive_score():
    score, _, valid, reason = calculate_score(
        avg_fish_energy=1_000_000.0,
        avg_fish_pop=1_000.0,
        max_generation=1_000,
        starvation_rate=1.0,
    )

    assert score == 0.0
    assert valid is False
    assert reason is not None
