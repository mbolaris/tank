"""Tests for the Theme 10.6 control-arm campaign.

These use stub benchmark modules rather than the tank benchmarks: a real
campaign candidate costs about 160 seconds, and none of the behaviour under
test here is about the tank.

The two guards get the most attention, because each one already caught a real
error during pre-flight and each fails silently if it regresses — an inert
instrument and an unreproducible reference both yield acceptance rates that
look like findings.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from core.research.control_arm import (
    CandidateOutcome,
    ReferenceCheck,
    binomial_interval,
    champion_seed_scores,
    check_reference_validity,
    probe_operator_sensitivity,
    run_campaign,
    summarize_campaign,
)


class _StubBenchmark(SimpleNamespace):
    """A benchmark module whose score is driven by a caller-supplied function."""


def _benchmark(benchmark_id: str, score_for) -> Any:
    calls: list[int] = []

    def run(seed: int) -> dict[str, Any]:
        calls.append(seed)
        return {"score": score_for(seed), "seed": seed}

    return _StubBenchmark(BENCHMARK_ID=benchmark_id, run=run, calls=calls)


def _inert(benchmark_id: str = "stub/inert") -> Any:
    """A benchmark no mutation can move — the foraging-gym failure mode."""
    return _benchmark(benchmark_id, lambda seed: 100.0)


def _responsive(benchmark_id: str = "stub/responsive") -> Any:
    """A benchmark whose score tracks a live mutated parameter."""
    from core.algorithms.composable import definitions

    def score_for(seed: int) -> float:
        # The operator shifts each parameter's bounds around its new value, so
        # the midpoint is what a mutation actually moves.
        low, high = definitions.SUB_BEHAVIOR_PARAMS["flee_speed"]
        return 100.0 + (float(low) + float(high)) * 5.0

    return _benchmark(benchmark_id, score_for)


# --- Wilson interval -------------------------------------------------------


def test_zero_successes_does_not_claim_certainty():
    """The normal approximation returns (0, 0) here, asserting the impossible."""
    low, high = binomial_interval(0, 3)
    assert low == pytest.approx(0.0, abs=1e-9)
    assert high > 0.5, "a 0/3 result must not be reported as a certain zero rate"


def test_interval_tightens_with_more_trials():
    _, narrow = binomial_interval(0, 100)
    _, wide = binomial_interval(0, 3)
    assert narrow < wide


def test_interval_brackets_the_observed_rate():
    low, high = binomial_interval(25, 100)
    assert low < 0.25 < high


def test_no_trials_is_not_a_division_error():
    assert binomial_interval(0, 0) == (0.0, 0.0)


# --- sensitivity guard -----------------------------------------------------


def test_inert_benchmark_is_reported_unresponsive():
    report = probe_operator_sensitivity(_inert(), seed=42, probes=3)
    assert not report.responsive
    assert report.mutations_applied > 0, "probes must actually propose mutations"
    assert set(report.deltas) == {0.0}


def test_responsive_benchmark_is_reported_responsive():
    report = probe_operator_sensitivity(_responsive(), seed=42, probes=5)
    assert report.responsive
    assert any(delta != 0.0 for delta in report.deltas)


def test_sensitivity_probe_restores_parameters():
    """A probe must leave the process's parameters exactly as it found them."""
    from core.algorithms.composable import definitions

    before = json.dumps(definitions.SUB_BEHAVIOR_PARAMS, sort_keys=True, default=str)
    probe_operator_sensitivity(_responsive(), seed=42, probes=3)
    after = json.dumps(definitions.SUB_BEHAVIOR_PARAMS, sort_keys=True, default=str)
    assert before == after


# --- reference-validity guard ---------------------------------------------


def test_champion_that_reproduces_is_accepted():
    benchmark = _benchmark("stub/exact", lambda seed: 500.0)
    check = check_reference_validity(benchmark, {"seed": 42, "score": 500.0})
    assert check.reproduces
    assert check.max_abs_delta == 0.0


def test_matrix_champion_is_compared_per_seed_not_against_its_mean():
    """The real trap: survival_5k's top-level score is a three-seed mean.

    Comparing that mean against a single-seed run manufactures a reproduction
    failure out of a champion that reproduces exactly - which is precisely what
    ``tools/validate_reproduction.py`` warns about.
    """
    recorded = {
        "42": 702.5775136245999,
        "7": 749.4781982900204,
        "123": 609.2674835157783,
    }
    benchmark = _benchmark("stub/matrix", lambda seed: recorded[str(seed)])
    champion = {
        "seed": 42,
        "score": 687.1077318101328,  # the mean, not any seed's score
        "per_seed": {seed: {"score": score} for seed, score in recorded.items()},
    }
    check = check_reference_validity(benchmark, champion)
    assert check.reproduces, "a champion matching every recorded seed must reproduce"
    assert check.seeds == (7, 42, 123)
    assert check.max_abs_delta == 0.0


def test_champion_seed_scores_prefers_per_seed_over_the_mean():
    champion = {
        "seed": 42,
        "score": 687.1077318101328,
        "per_seed": {"42": {"score": 702.5}, "7": {"score": 749.5}},
    }
    assert champion_seed_scores(champion) == {"42": 702.5, "7": 749.5}


def test_champion_seed_scores_falls_back_to_the_single_seed():
    assert champion_seed_scores({"seed": 42, "score": 500.0}) == {"42": 500.0}


def test_champion_that_genuinely_diverges_is_rejected():
    champion = {
        "seed": 42,
        "score": 500.0,
        "per_seed": {"42": {"score": 500.0}, "7": {"score": 600.0}},
    }
    local = {"42": 500.0, "7": 611.0}
    benchmark = _benchmark("stub/diverged", lambda seed: local[str(seed)])
    check = check_reference_validity(benchmark, champion)
    assert not check.reproduces
    assert check.max_abs_delta == pytest.approx(11.0)
    assert check.deltas["42"] == 0.0


def test_reference_check_uses_the_champions_own_seed():
    benchmark = _benchmark("stub/seeded", lambda seed: float(seed))
    check = check_reference_validity(benchmark, {"seed": 7, "score": 7.0})
    assert check.seeds == (7,)
    assert check.reproduces


# --- campaign --------------------------------------------------------------


def test_campaign_writes_its_trace_incrementally(tmp_path: Path):
    """An interrupted campaign must still leave every scored candidate on disk."""
    benchmark = _responsive("stub/trace")
    report = run_campaign(
        benchmark,
        candidates=3,
        seeds=(42, 7),
        results_dir=tmp_path,
        ledger_path=tmp_path / "ledger.jsonl",
    )
    trace = tmp_path / "stub_trace_candidates.jsonl"
    lines = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    assert len(lines) == 3
    assert [line["candidate"] for line in lines] == [1, 2, 3]
    assert all("mutation_plan" in line for line in lines)
    assert report["candidates"] == 3


def test_campaign_falls_back_to_paired_baseline_without_a_champion(tmp_path: Path):
    report = run_campaign(
        _responsive("stub/paired"),
        candidates=2,
        seeds=(42,),
        results_dir=tmp_path,
        ledger_path=tmp_path / "ledger.jsonl",
    )
    assert report["reference_kind"] == "local-paired-baseline"
    assert report["reference_score"] == report["baseline_score"]


def test_heldout_baseline_is_measured_once_not_per_acceptance(tmp_path: Path):
    """Re-measuring identical unmutated code per acceptance is wasted compute."""
    heldout = _benchmark("stub/heldout", lambda seed: 10.0)
    # A benchmark that improves on every candidate, so every one is accepted.
    scores = iter([1.0] + [float(n) for n in range(100, 200)])
    tuning = _benchmark("stub/always", lambda seed: next(scores))
    run_campaign(
        tuning,
        candidates=3,
        seeds=(42,),
        heldout=heldout,
        results_dir=tmp_path,
        ledger_path=tmp_path / "ledger.jsonl",
    )
    # One baseline plus one re-score per acceptance, never a baseline each time.
    assert len(heldout.calls) == 1 + 3


def test_campaign_reports_compute_accounting(tmp_path: Path):
    report = run_campaign(
        _responsive("stub/compute"),
        candidates=2,
        seeds=(42, 7, 123),
        results_dir=tmp_path,
        ledger_path=tmp_path / "ledger.jsonl",
    )
    compute = report["compute"]
    assert compute["benchmark_runs"] == 9, "baseline plus two candidates, three seeds each"
    assert compute["wall_clock_seconds"] >= 0.0


# --- summary ---------------------------------------------------------------


def _outcome(index: int, *, accepted: bool, score: float, transferred: bool | None = None):
    return CandidateOutcome(
        index=index,
        accepted=accepted,
        score=score,
        per_seed={"42": score},
        mutation_digest=None,
        runtime_seconds=0.0,
        heldout_transferred=transferred,
    )


def test_summary_separates_acceptance_from_transfer(tmp_path: Path):
    """Accepting on the tuning benchmark is not the same as transferring."""
    outcomes = [
        _outcome(1, accepted=True, score=10.0, transferred=False),
        _outcome(2, accepted=True, score=12.0, transferred=True),
        _outcome(3, accepted=False, score=1.0),
    ]
    report = summarize_campaign(
        benchmark_id="stub/summary",
        heldout_id="stub/heldout",
        seeds=(42,),
        baseline={"score": 5.0},
        comparison={"score": 5.0},
        reference_kind="local-paired-baseline",
        outcomes=outcomes,
        wall_clock_seconds=1.0,
        benchmark_runs=4,
        trace_path=tmp_path / "trace.jsonl",
    )
    assert report["acceptance"]["accepted"] == 2
    assert report["transfer"]["transferred"] == 1
    assert report["transfer"]["rate"] == pytest.approx(0.5)
    assert report["best_achieved"]["score"] == 12.0
    assert report["best_achieved"]["delta_vs_reference"] == pytest.approx(7.0)


def test_summary_records_an_unreproducible_reference(tmp_path: Path):
    check = ReferenceCheck(
        benchmark_id="stub/summary",
        champion_scores={"42": 500.0},
        local_scores={"42": 515.0},
        tolerance=1e-9,
    )
    report = summarize_campaign(
        benchmark_id="stub/summary",
        heldout_id=None,
        seeds=(42,),
        baseline={"score": 702.0},
        comparison={"score": 702.0},
        reference_kind="local-paired-baseline",
        outcomes=[_outcome(1, accepted=False, score=1.0)],
        wall_clock_seconds=1.0,
        benchmark_runs=2,
        trace_path=tmp_path / "trace.jsonl",
        reference_check=check,
    )
    assert report["reference_check"]["reproduces"] is False
    assert report["reference_check"]["max_abs_delta"] == pytest.approx(15.0)
