"""Tests for the multi-run transfer study: config threading, scenario-count
scaling, aggregation math, and the conservative verdict rule."""

from __future__ import annotations

import pytest

from core.behavior.target_memory_transfer_evolution import (
    TransferStudyConfig,
    evaluate_target_memory_transfer,
)
from core.behavior.target_memory_transfer_scenarios import generate_scenario_set
from core.behavior.target_memory_transfer_study import (
    aggregate_rows,
    bootstrap_ci,
    build_report,
    render_markdown,
    seed_row,
)

_TINY = TransferStudyConfig(
    population_size=4,
    generations=2,
    evolution_runs=1,
    food_train_count=3,
    food_validation_count=2,
    ball_held_out_count=3,
    ball_train_count=3,
    ball_validation_count=2,
)


def _row(
    seed: int,
    vs_disjoint: float,
    vs_neutral: float = 0.0,
    established: bool = False,
    gens_food: int | None = None,
    gens_default: int | None = None,
) -> dict:
    return {
        "seed": seed,
        "group_scores": {},
        "transfer_vs_disjoint": vs_disjoint,
        "transfer_vs_neutral": vs_neutral,
        "family_effect_vs_default": {"bouncing": vs_disjoint},
        "adaptation_reference_established": established,
        "adaptation_reference_gap": 0.05 if established else -0.01,
        "adaptation_generations_food": gens_food,
        "adaptation_generations_default": gens_default,
        "diagnostics": {},
    }


# ---------------------------------------------------------------------------
# Scenario-count scaling
# ---------------------------------------------------------------------------
def test_scenario_count_extends_the_default_set_deterministically():
    """Bigger sets must extend the default set (same seed -> same first
    scenarios), so scaled studies add evidence rather than replacing it."""
    default = generate_scenario_set("train", 42)
    scaled = generate_scenario_set("train", 42, count=16)
    assert len(scaled) == 16
    for small, big in zip(default, scaled, strict=False):
        assert small.family_name == big.family_name
        assert small.tracks[0].positions[0] == big.tracks[0].positions[0]

    # Families cycle in canonical order past the default length.
    assert scaled[len(default)].family_name == scaled[0].family_name


def test_scenario_count_validates_input():
    with pytest.raises(ValueError):
        generate_scenario_set("train", 42, count=0)


# ---------------------------------------------------------------------------
# Config threading
# ---------------------------------------------------------------------------
@pytest.mark.slow
def test_default_config_matches_no_config():
    """evaluate_target_memory_transfer(seed) must be unchanged by the config
    plumbing: an explicit default config gives the identical evaluation."""
    implicit = evaluate_target_memory_transfer(3)
    explicit = evaluate_target_memory_transfer(3, TransferStudyConfig())
    assert implicit.group_summaries == explicit.group_summaries
    assert implicit.adaptation_reference_gap == explicit.adaptation_reference_gap


def test_tiny_config_runs_all_groups_and_is_deterministic():
    first = evaluate_target_memory_transfer(0, _TINY)
    second = evaluate_target_memory_transfer(0, _TINY)
    assert set(first.group_summaries) == {
        "naive_greedy",
        "default_params",
        "neutral_evolution",
        "food_trained",
        "ball_trained",
    }
    assert first.group_summaries == second.group_summaries
    assert first.adaptation_reference_gap == second.adaptation_reference_gap


def test_seed_row_flattens_the_evaluation():
    row = seed_row(0, _TINY)
    assert row["seed"] == 0
    assert row["transfer_vs_disjoint"] == pytest.approx(
        row["group_scores"]["food_trained"] - row["group_scores"]["default_params"]
    )
    assert set(row["diagnostics"]) == set(row["group_scores"])
    assert row["family_effect_vs_default"]


# ---------------------------------------------------------------------------
# Aggregation math and the verdict rule
# ---------------------------------------------------------------------------
def test_bootstrap_ci_is_deterministic_and_brackets_the_mean():
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    lo1, hi1 = bootstrap_ci(values)
    lo2, hi2 = bootstrap_ci(values)
    assert (lo1, hi1) == (lo2, hi2)
    assert lo1 <= sum(values) / len(values) <= hi1
    assert lo1 < hi1


def test_verdict_requires_ci_to_exclude_zero():
    # Consistently positive effects -> CI above zero -> positive verdict.
    positive_rows = [_row(seed, 0.05 + 0.001 * seed) for seed in range(10)]
    agg = aggregate_rows(positive_rows)
    assert agg["effects"]["transfer_vs_disjoint"]["verdict"] == "positive"
    assert agg["overall_verdict"] == "positive"

    negative_rows = [_row(seed, -0.05 - 0.001 * seed) for seed in range(10)]
    assert aggregate_rows(negative_rows)["overall_verdict"] == "negative"

    # Mixed-sign effects straddling zero must never produce a verdict.
    mixed_rows = [_row(seed, 0.05 if seed % 2 else -0.05) for seed in range(10)]
    agg = aggregate_rows(mixed_rows)
    assert agg["overall_verdict"] == "inconclusive"
    assert agg["effects"]["transfer_vs_disjoint"]["fraction_positive"] == 0.5


def test_aggregate_reports_adaptation_only_where_established():
    rows = [
        _row(0, 0.01, established=True, gens_food=3, gens_default=7),
        _row(1, 0.02, established=True, gens_food=5, gens_default=5),
        _row(2, 0.03),
    ]
    adaptation = aggregate_rows(rows)["adaptation"]
    assert adaptation["seeds_with_reference"] == 2
    assert adaptation["seeds_total"] == 3
    accel = adaptation["acceleration_generations"]
    assert accel["values"] == [4, 0]
    assert accel["fraction_positive"] == 0.5

    no_reference = aggregate_rows([_row(0, 0.01), _row(1, 0.02)])["adaptation"]
    assert no_reference["acceleration_generations"] is None


def test_report_and_markdown_are_complete():
    rows = [_row(seed, 0.01 * seed - 0.02) for seed in range(5)]
    report = build_report(rows, _TINY)
    assert report["study"]["seeds"] == [0, 1, 2, 3, 4]
    assert report["study"]["primary_effect"] == "transfer_vs_disjoint"
    assert len(report["per_seed"]) == 5

    markdown = render_markdown(report)
    assert "Overall verdict" in markdown
    assert "transfer_vs_disjoint" in markdown
    assert "bouncing" in markdown
    assert "Reference established" in markdown
