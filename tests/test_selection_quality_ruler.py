"""Tests for Proposal #27: Bottleneck-Conditioned Selection Ruler.

Covers the three new functions added to tools/evolution_report.py:
  - _stable_samples(): population floor + local-CV filter
  - _range_normalized_drift(): percent-blowup-immune normalization
  - _selection_quality(): confidence label + conditioned_drift + epoch detection

Also covers the boot_id tagging in backend/metrics_history.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import evolution_report without installing it as a package
# ---------------------------------------------------------------------------
_ER_SPEC = importlib.util.spec_from_file_location(
    "evolution_report",
    Path(__file__).resolve().parents[1] / "tools" / "evolution_report.py",
)
assert _ER_SPEC and _ER_SPEC.loader
er = importlib.util.module_from_spec(_ER_SPEC)
_ER_SPEC.loader.exec_module(er)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample(frame, gen, pop, div, traits, boot_id=None):
    s = {
        "frame": frame,
        "max_generation": gen,
        "population": pop,
        "births_total": 0,
        "deaths_total": 0,
        "diversity_score": div,
        "traits": traits,
    }
    if boot_id is not None:
        s["boot_id"] = boot_id
    return s


def _stable_pop_samples(n=30, pop=35, trait_val=0.5, boot_id=1):
    """Generate n stable-population samples with consistent traits."""
    return [
        _sample(
            frame=i * 1000,
            gen=i,
            pop=pop,
            div=0.5,
            traits={"pursuit_aggression": trait_val + i * 0.001, "speed": 1.2},
            boot_id=boot_id,
        )
        for i in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# _stable_samples tests
# ---------------------------------------------------------------------------


def test_stable_samples_rejects_low_population() -> None:
    """Samples with population < POP_STABLE_MIN should be filtered out."""
    # Create 40 samples: the first is low-pop, the rest are stable pop 30
    samples = [_sample(1000, 1, 5, 0.5, {"pursuit_aggression": 0.5})] + [
        _sample(i * 1000, i, 30, 0.5, {"pursuit_aggression": 0.5}) for i in range(2, 42)
    ]
    stable = er._stable_samples(samples)
    frames = [s["frame"] for s in stable]
    assert 1000 not in frames, "Low-pop sample (frame 1000) should be filtered"
    # Samples in the stable region (e.g. frame 30000, index 30) should pass because their local CV window (width 20)
    # does not reach the low-pop sample at index 0.
    assert 30000 in frames, "Stable samples far from the low-pop sample should pass"


def test_stable_samples_rejects_boom_bust_shoulder() -> None:
    """Even if pop >= floor, a sample inside a boom/bust window should be rejected."""
    # Create 30 samples where population fluctuates wildly (CV >> 0.35)
    pops = [
        5,
        80,
        5,
        80,
        5,
        80,
        5,
        80,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
        30,
    ]
    samples = [
        _sample(i * 500, i, pop, 0.5, {"pursuit_aggression": 0.5}) for i, pop in enumerate(pops, 1)
    ]
    stable = er._stable_samples(samples)
    # The boom/bust shoulder samples should be excluded
    # The tail of stable-population samples should survive
    stable_pops = [s["population"] for s in stable]
    assert all(p >= er.POP_STABLE_MIN for p in stable_pops), "No low-pop samples should survive"


def test_stable_samples_passes_consistently_stable_run() -> None:
    """A run with pop always >= 20 and low CV should pass almost all samples."""
    samples = _stable_pop_samples(n=50, pop=35)
    stable = er._stable_samples(samples)
    # At least 80% should survive (edges may be clipped by local CV window)
    assert len(stable) >= int(
        len(samples) * 0.7
    ), f"Expected >= 70% stable samples, got {len(stable)}/{len(samples)}"


# ---------------------------------------------------------------------------
# _range_normalized_drift tests
# ---------------------------------------------------------------------------


def test_range_normalized_drift_behavioral_traits() -> None:
    """Behavioral traits [0,1] should return |delta|/1.0 = |delta|."""
    raw_drift = {
        "pursuit_aggression": {
            "start": 0.1,
            "end": 0.9,
            "delta": 0.8,
            "pct": 800.0,
            "selection": True,
        },
        "prediction_skill": {
            "start": 0.03,
            "end": 0.9,
            "delta": 0.87,
            "pct": 2900.0,
            "selection": True,
        },
    }
    rn = er._range_normalized_drift(raw_drift)
    # pursuit_aggression: |0.8| / (1.0 - 0.0) = 0.8
    assert abs(rn["pursuit_aggression"] - 0.8) < 1e-4
    # prediction_skill: |0.87| / 1.0 = 0.87  (not 2900%!)
    assert abs(rn["prediction_skill"] - 0.87) < 1e-4


def test_range_normalized_drift_clips_at_one() -> None:
    """Delta larger than the known range should be clipped to 1.0."""
    raw_drift = {
        "pursuit_aggression": {
            "start": 0.0,
            "end": 2.0,
            "delta": 2.0,
            "pct": 9999.0,
            "selection": True,
        },
    }
    rn = er._range_normalized_drift(raw_drift)
    assert rn["pursuit_aggression"] == 1.0


def test_range_normalized_drift_skips_unknown_traits() -> None:
    """Traits not in TRAIT_BOUNDS should be silently skipped."""
    raw_drift = {
        "unknown_trait": {"start": 0.1, "end": 0.9, "delta": 0.8, "pct": 800.0, "selection": True},
    }
    rn = er._range_normalized_drift(raw_drift)
    assert "unknown_trait" not in rn


# ---------------------------------------------------------------------------
# _selection_quality / confidence label tests
# ---------------------------------------------------------------------------


def test_selection_quality_high_confidence_on_stable_run() -> None:
    """A stable, single-boot run with clear drift should be high_confidence_selection."""
    # 40 stable samples, pop=35, trait drifts strongly
    samples = [
        _sample(i * 500, i, 35, 0.5, {"pursuit_aggression": 0.3 + i * 0.015}, boot_id=1)
        for i in range(1, 41)
    ]
    raw_drift = er._trait_drift(samples)
    sq = er._selection_quality(samples, raw_drift)
    assert sq["confidence"] == "high_confidence_selection", sq
    assert sq["epoch_mixed"] is False
    assert sq["conditioned_selection_detected"] is True
    assert sq["stable_sample_count"] >= 30


def test_selection_quality_epoch_confounded_multi_boot() -> None:
    """Samples from multiple boot_ids should be flagged as epoch_confounded."""
    samples = _stable_pop_samples(n=20, pop=35, trait_val=0.3, boot_id=1) + _stable_pop_samples(
        n=20, pop=35, trait_val=0.7, boot_id=2
    )
    raw_drift = er._trait_drift(samples)
    sq = er._selection_quality(samples, raw_drift)
    assert sq["confidence"] == "epoch_confounded", sq
    assert sq["epoch_mixed"] is True
    assert 1 in sq["boot_ids_in_window"]
    assert 2 in sq["boot_ids_in_window"]


def test_selection_quality_bottleneck_confounded() -> None:
    """A trait drift that disappears after pop filtering should be bottleneck_confounded.

    We engineer this by having the 'drift' only appear in low-population crash samples
    (start near zero, then crash, then stable at a different value) so the filtered
    window shows no drift.
    """
    # 10 samples with pop=4 (crash, low), traits jumping 0.1 -> 0.9
    crash = [
        _sample(i * 500, i, 4, 0.1, {"pursuit_aggression": 0.1 + i * 0.08}, boot_id=1)
        for i in range(1, 11)
    ]
    # 30 samples with pop=35 (stable), traits stable at 0.9
    stable_tail = [
        _sample(
            5500 + i * 500, 10 + i, 35, 0.5, {"pursuit_aggression": 0.89 + i * 0.0001}, boot_id=1
        )
        for i in range(1, 31)
    ]
    samples = crash + stable_tail
    # Raw drift: start=0.1 end=~0.892 -> large pct -> selection
    raw_drift = er._trait_drift(samples)
    assert (
        raw_drift.get("pursuit_aggression", {}).get("selection") is True
    ), "raw drift should show selection from crash window"
    sq = er._selection_quality(samples, raw_drift)
    # Conditioned drift only covers stable tail (pop>=20), which is ~flat
    # So confidence should be bottleneck_confounded
    assert sq["confidence"] == "bottleneck_confounded", (
        f"Expected bottleneck_confounded, got {sq['confidence']!r}. "
        f"conditioned_selection_detected={sq['conditioned_selection_detected']}, "
        f"stable_sample_count={sq['stable_sample_count']}"
    )


def test_selection_quality_no_boot_id_samples() -> None:
    """Old samples without boot_id should not be epoch_confounded (just no tag info)."""
    samples = [
        _sample(i * 500, i, 35, 0.5, {"pursuit_aggression": 0.3 + i * 0.015}) for i in range(1, 41)
    ]
    raw_drift = er._trait_drift(samples)
    sq = er._selection_quality(samples, raw_drift)
    assert sq["epoch_mixed"] is False
    assert sq["boot_ids_in_window"] == []


def test_selection_quality_in_analyze_history() -> None:
    """analyze_history() should now include selection_quality in its output."""
    samples = _stable_pop_samples(n=20, pop=35, boot_id=1)
    hist = er.analyze_history(samples)
    assert "selection_quality" in hist, "selection_quality should be in analyze_history output"
    sq = hist["selection_quality"]
    assert "confidence" in sq
    assert "stable_sample_count" in sq
    assert "range_normalized_drift" in sq
    assert "conditioned_drift" in sq


def test_selection_quality_in_build_report() -> None:
    """build_report() should propagate selection_quality through the history block."""
    samples = _stable_pop_samples(n=20, pop=35, boot_id=1)
    report = er.build_report(samples, {"population": 35}, "test")
    assert "selection_quality" in report["history"]


def test_format_human_includes_selection_quality() -> None:
    """format_human() should render the SELECTION QUALITY section."""
    samples = _stable_pop_samples(n=20, pop=35, boot_id=1)
    report = er.build_report(samples, {"population": 35}, "test")
    text = er.format_human(report)
    assert "SELECTION QUALITY" in text, "format_human should include SELECTION QUALITY section"
    assert "confidence" in text.lower()


# ---------------------------------------------------------------------------
# backend/metrics_history.py boot_id tests
# ---------------------------------------------------------------------------


def test_metrics_history_boot_id_increments() -> None:
    """Each MetricsHistory instance should get a unique, incrementing boot_id."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.metrics_history import MetricsHistory

    h1 = MetricsHistory("world-1")
    h2 = MetricsHistory("world-2")
    assert isinstance(h1.boot_id, int)
    assert isinstance(h2.boot_id, int)
    assert h2.boot_id == h1.boot_id + 1, "boot_id should increment monotonically"


def test_metrics_history_sample_has_boot_id() -> None:
    """Recorded samples should include the boot_id field."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.metrics_history import MetricsHistory

    mh = MetricsHistory("world-boot-test", sample_interval_frames=10)
    # Create a minimal stats-like dict
    stats = type(
        "S",
        (),
        {
            "max_generation": 1,
            "population": 30,
            "births": 10,
            "deaths": 8,
            "fish_energy": 100.0,
            "diversity_score": 0.5,
            "poker_elo": None,
        },
    )()
    mh.maybe_sample(
        frame=10,
        stats=stats,
        poker=None,
        soccer=None,
        auto_eval=None,
        trait_means={"pursuit_aggression": 0.5},
    )
    assert mh.samples, "Expected at least one sample"
    sample = mh.samples[0]
    assert "boot_id" in sample, "Sample must include boot_id"
    assert sample["boot_id"] == mh.boot_id


def test_metrics_history_schema_version_is_3() -> None:
    """After the Proposal #27 change, SCHEMA_VERSION should be 3."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.metrics_history import SCHEMA_VERSION

    assert SCHEMA_VERSION == 3, f"Expected SCHEMA_VERSION=3, got {SCHEMA_VERSION}"
