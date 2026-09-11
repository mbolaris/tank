"""Tests for the control-arm candidate confirmation stage.

These use stub benchmarks: the behaviour under test is the rule, not the tank.
The rule exists because of a real candidate, so the numbers in
``test_the_real_candidate_27_shape_is_refused`` are that candidate's.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from core.research.candidate_confirmation import (
    CAMPAIGN_SEEDS,
    ConfirmationReport,
    SeedOutcome,
    confirm_candidate,
    invalid_reason,
    run_validity,
)


def _benchmark(benchmark_id: str, runs: dict[int, dict[str, Any]]) -> Any:
    """A stub whose result for each seed is supplied directly.

    ``runs`` maps seed -> {"baseline": result, "candidate": result}; the stub
    returns the candidate result whenever the mutated parameters are in effect,
    which the test signals with a module-level flag rather than real mutation.
    """
    state = {"mutated": False}

    def run(seed: int) -> dict[str, Any]:
        return runs[seed]["candidate" if state["mutated"] else "baseline"]

    return SimpleNamespace(BENCHMARK_ID=benchmark_id, run=run, _state=state)


def _result(score: float, *, valid: bool = True, reason: str | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {"score_valid": valid}
    if reason:
        metadata["score_invalid_reason"] = reason
    return {"score": score, "metadata": metadata}


class _Plan:
    """Stands in for a MutationPlan; flips the stub into candidate mode."""

    def __init__(self, benchmark: Any) -> None:
        self._benchmark = benchmark

    def to_dict(self) -> dict[str, Any]:
        return {"mutations": []}


@pytest.fixture(autouse=True)
def _patch_evaluate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route evaluate_plan at the stub without touching global algorithm state."""
    import tools.non_ai_baseline as baseline_module

    def fake_evaluate(benchmark: Any, seeds: tuple[int, ...], plan: Any) -> dict[str, Any]:
        benchmark._state["mutated"] = plan is not None
        per_seed = {str(seed): benchmark.run(seed) for seed in seeds}
        scores = [float(run["score"]) for run in per_seed.values()]
        return {"score": sum(scores) / len(scores), "per_seed": per_seed}

    monkeypatch.setattr(baseline_module, "evaluate_plan", fake_evaluate)


# --- validity reading -------------------------------------------------------


def test_validity_is_read_from_the_benchmarks_own_metadata():
    assert run_validity(_result(1.0, valid=True)) is True
    assert run_validity(_result(0.0, valid=False)) is False


def test_a_benchmark_without_a_validity_gate_is_not_guessed_at():
    assert run_validity({"score": 5.0}) is True
    assert run_validity({"score": 5.0, "metadata": {}}) is True


def test_the_benchmarks_own_reason_is_carried_through():
    reason = "starvation_rate 0.9778 >= maximum valid rate 0.9500"
    assert invalid_reason(_result(0.0, valid=False, reason=reason)) == reason
    assert invalid_reason(_result(1.0)) is None


# --- the rule ---------------------------------------------------------------


def test_a_clean_improvement_is_confirmed():
    runs = {
        1: {"baseline": _result(100.0), "candidate": _result(120.0)},
        2: {"baseline": _result(200.0), "candidate": _result(210.0)},
        999: {"baseline": _result(50.0), "candidate": _result(55.0)},
    }
    report = confirm_candidate(_benchmark("stub/clean", runs), _Plan(None))
    assert report.confirmed
    assert report.mean_delta == pytest.approx((20 + 10 + 5) / 3)
    assert report.invalidated == ()


def test_the_real_candidate_27_shape_is_refused():
    """The measured case: a big mean win that breaks one previously-valid seed."""
    reason = "starvation_rate 0.9778 >= maximum valid rate 0.9500"
    runs = {
        1: {"baseline": _result(666.1149), "candidate": _result(743.0540)},
        2: {
            "baseline": _result(513.4733, valid=True),
            "candidate": _result(0.0, valid=False, reason=reason),
        },
        999: {
            "baseline": _result(0.0, valid=False),
            "candidate": _result(0.0, valid=False),
        },
    }
    report = confirm_candidate(_benchmark("tank/survival_5k", runs), _Plan(None))
    assert not report.confirmed, "breaking a valid run must not be outvoted by an average"
    assert [outcome.seed for outcome in report.invalidated] == [2]
    assert report.invalidated[0].candidate_invalid_reason == reason


def test_a_seed_already_invalid_at_baseline_is_not_blamed_on_the_candidate():
    runs = {
        1: {"baseline": _result(100.0), "candidate": _result(110.0)},
        2: {"baseline": _result(100.0), "candidate": _result(110.0)},
        999: {
            "baseline": _result(0.0, valid=False),
            "candidate": _result(0.0, valid=False),
        },
    }
    report = confirm_candidate(_benchmark("stub/prebroken", runs), _Plan(None))
    assert report.invalidated == (), "the baseline was already broken on that seed"
    assert report.confirmed


def test_an_average_win_cannot_outvote_a_break():
    runs = {
        1: {"baseline": _result(10.0), "candidate": _result(10_000.0)},
        2: {"baseline": _result(10.0), "candidate": _result(0.0, valid=False)},
        999: {"baseline": _result(10.0), "candidate": _result(10.0)},
    }
    report = confirm_candidate(_benchmark("stub/lopsided", runs), _Plan(None))
    assert report.mean_delta > 0
    assert not report.confirmed


def test_a_mean_regression_is_refused_even_with_nothing_broken():
    runs = {
        1: {"baseline": _result(100.0), "candidate": _result(80.0)},
        2: {"baseline": _result(100.0), "candidate": _result(105.0)},
        999: {"baseline": _result(100.0), "candidate": _result(100.0)},
    }
    report = confirm_candidate(_benchmark("stub/down", runs), _Plan(None))
    assert not report.confirmed
    assert [outcome.seed for outcome in report.regressions] == [1]


# --- the seeds themselves ---------------------------------------------------


def test_confirmation_refuses_to_reuse_the_searched_seeds():
    runs = {seed: {"baseline": _result(1.0), "candidate": _result(2.0)} for seed in (42, 5, 6)}
    with pytest.raises(ValueError, match="disjoint"):
        confirm_candidate(_benchmark("stub/overlap", runs), _Plan(None), seeds=(42, 5, 6))


def test_the_default_seeds_do_not_overlap_the_campaign():
    from core.research.candidate_confirmation import DEFAULT_CONFIRMATION_SEEDS

    assert not set(DEFAULT_CONFIRMATION_SEEDS) & set(CAMPAIGN_SEEDS)


def test_report_serialises_what_a_reader_needs():
    outcome = SeedOutcome(
        seed=2,
        baseline_score=513.4733,
        candidate_score=0.0,
        baseline_valid=True,
        candidate_valid=False,
        candidate_invalid_reason="starvation",
    )
    payload = ConfirmationReport(benchmark_id="tank/survival_5k", outcomes=(outcome,)).to_dict()
    assert payload["confirmed"] is False
    assert payload["invalidated_seeds"] == [2]
    assert payload["outcomes"][0]["delta"] == pytest.approx(-513.4733)
