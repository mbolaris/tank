"""Tests for the evolution_report study tool's pure analysis/verdict logic."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "evolution_report", Path(__file__).resolve().parents[1] / "tools" / "evolution_report.py"
)
assert _SPEC and _SPEC.loader
er = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(er)


def _sample(frame, gen, pop, div, traits, births=0, deaths=0):
    return {
        "frame": frame,
        "max_generation": gen,
        "population": pop,
        "births_total": births,
        "deaths_total": deaths,
        "diversity_score": div,
        "traits": traits,
    }


def test_extractors_tolerate_shapes() -> None:
    payload = {"samples": [{"frame": 1}]}
    assert er.extract_history_samples(payload) == [{"frame": 1}]
    snapshot = {"metrics_history": {"samples": [{"frame": 2}]}, "stats": {"population": 30}}
    assert er.extract_history_samples(snapshot) == [{"frame": 2}]
    assert er.extract_stats(snapshot) == {"population": 30}
    # A raw export dict is already the stats block.
    assert er.extract_stats({"population": 5})["population"] == 5
    assert er.extract_history_samples(None) == []


def test_fetch_live_falls_back_to_history_when_snapshot_has_only_stats(monkeypatch) -> None:
    calls = []

    def fake_http_get_json(url: str, timeout: float = 10.0):
        del timeout
        calls.append(url)
        if url.endswith("/api/worlds/default/id"):
            return {"world_id": "abc"}
        if url.endswith("/api/worlds/abc/snapshot"):
            return {"snapshot": {"stats": {"population": 30}}}
        if url.endswith("/api/world/abc/metrics/history"):
            return {"samples": [{"frame": 1, "population": 30}]}
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(er, "_http_get_json", fake_http_get_json)

    samples, stats, source = er.fetch_live("http://test", None)

    assert samples == [{"frame": 1, "population": 30}]
    assert stats == {"population": 30}
    assert "snapshot+metrics/history" in source
    assert len(calls) == 3


def test_starvation_fraction_from_causes() -> None:
    assert er.starvation_fraction({"starvation_rate": 0.9}) == 0.9
    assert er.starvation_fraction({"death_causes": {"starvation": 8, "predation": 2}}) == 0.8
    assert er.starvation_fraction({"death_causes": {}}) is None


def test_population_value_prefers_explicit_fish_count() -> None:
    stats = {"population": 8022, "fish_count": 25}
    assert er.population_value(stats) == 25.0


def test_ambiguous_population_history_is_suppressed() -> None:
    samples = [
        _sample(1000, 1, 8000, 0.6, {"pursuit_aggression": 0.40}),
        _sample(2000, 4, 8022, 0.6, {"pursuit_aggression": 0.50}),
    ]
    stats = {"population": 8022, "fish_count": 25}

    report = er.build_report(samples, stats, "test")

    assert report["current"]["population"] == 25.0
    assert report["history"]["population_history_ambiguous"] is True
    assert "population_mean" not in report["history"]


def test_trait_drift_flags_selection() -> None:
    samples = [
        _sample(1000, 1, 30, 0.6, {"pursuit_aggression": 0.40, "speed": 1.00}),
        _sample(2000, 3, 31, 0.6, {"pursuit_aggression": 0.50, "speed": 1.005}),
    ]
    hist = er.analyze_history(samples)
    drift = hist["trait_drift"]
    # +25% pursuit_aggression is directional selection; +0.5% speed is not.
    assert drift["pursuit_aggression"]["selection"] is True
    assert drift["speed"]["selection"] is False
    assert hist["selection_detected"] is True


def test_healthy_run_verdict() -> None:
    samples = [
        _sample(i * 1000, i, 35, 0.65, {"pursuit_aggression": 0.40 + i * 0.02}, births=i * 5)
        for i in range(1, 12)
    ]
    stats = {
        "max_generation": 11,
        "population": 35,
        "death_causes": {"starvation": 30, "predation": 40},  # ~43% starvation
        "diversity_stats": {"diversity_score": 0.65, "unique_algorithms": 12},
    }
    report = er.build_report(samples, stats, "test")
    assert report["axes"]["selection"] == "active"
    assert report["axes"]["foraging"] == "ok"
    assert report["axes"]["turnover"] == "healthy"
    assert report["verdict"] == "healthy"
    # The all-clear recommendation is still present and low priority.
    assert report["recommendations"][0]["priority"] == "low"


def test_struggling_run_flags_and_recommendations() -> None:
    # Flat traits (drift only), slow turnover, high starvation.
    samples = [
        _sample(i * 1000, 1, 12, 0.2, {"pursuit_aggression": 0.40, "speed": 1.0})
        for i in range(1, 12)
    ]
    stats = {
        "max_generation": 1,
        "population": 12,
        "death_causes": {"starvation": 97, "predation": 3},  # 97% starvation -> broken
        "diversity_stats": {"diversity_score": 0.2, "unique_algorithms": 2},
    }
    report = er.build_report(samples, stats, "test")
    assert report["axes"]["foraging"] == "broken"
    assert report["axes"]["selection"] == "drift_only"
    assert report["axes"]["turnover"] == "stalled"
    assert report["verdict"] in {"struggling", "stalled"}
    # The top recommendation is high priority and food-seeking points at the ball gotcha.
    assert report["recommendations"][0]["priority"] == "high"
    joined = json.dumps(report["recommendations"])
    assert "diagnose_food_seeking" in joined
    assert "movement_strategy" in joined


def test_high_starvation_with_stable_turnover_is_strained_not_broken() -> None:
    samples = [
        _sample(
            i * 1000,
            i,
            45,
            0.5,
            {"pursuit_aggression": 0.40 + i * 0.02},
            births=i * 20,
            deaths=i * 20,
        )
        for i in range(1, 12)
    ]
    stats = {
        "max_generation": 11,
        "population": 45,
        "death_causes": {"starvation": 97, "predation": 3},
        "diversity_stats": {"diversity_score": 0.5, "unique_algorithms": 12},
    }

    report = er.build_report(samples, stats, "test")

    assert report["axes"]["population"] == "stable"
    assert report["axes"]["turnover"] == "healthy"
    assert report["axes"]["foraging"] == "strained"
    assert report["verdict"] == "treading_water"


def test_insufficient_data_verdict() -> None:
    report = er.build_report([_sample(1000, 1, 30, 0.6, {})], {}, "test")
    assert report["verdict"] == "insufficient_data"
    assert any("history sample" in r["finding"] for r in report["recommendations"])


def test_new_samples_since() -> None:
    samples = [{"frame": 100}, {"frame": 200}, {"frame": 300}]
    assert er._new_samples_since(150, samples) == [{"frame": 200}, {"frame": 300}]
    assert er._new_samples_since(300, samples) == []


def test_format_human_runs() -> None:
    samples = [
        _sample(1000, 1, 30, 0.6, {"pursuit_aggression": 0.40}),
        _sample(2000, 4, 31, 0.6, {"pursuit_aggression": 0.50}),
    ]
    text = er.format_human(er.build_report(samples, {"population": 31}, "test"))
    assert "EVOLUTION HEALTH REPORT" in text
    assert "RECOMMENDATIONS" in text
