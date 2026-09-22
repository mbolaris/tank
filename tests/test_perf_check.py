"""Unit tests for tools/perf_check.py's verdict logic (no benchmark runs)."""

from __future__ import annotations

import json
from pathlib import Path

from tools.perf_check import count_checkpoints, speedup_summary, trajectory_verdict


def test_speedup_summary_reports_faster_and_slower() -> None:
    assert speedup_summary(62.0, 55.0) == "-11.3% runtime, 1.13x faster"
    assert speedup_summary(50.0, 60.0) == "+20.0% runtime, 1.20x slower"
    assert speedup_summary(0.0, 1.0) == "runtime unavailable"


def test_identical_needs_matching_fingerprints_and_scores() -> None:
    clean = {"exact": None, "rounded": None}
    identical, verdict = trajectory_verdict(818.4, 818.4, clean, 21)
    assert identical
    assert "IDENTICAL" in verdict and "21 fingerprint checkpoints" in verdict

    identical, verdict = trajectory_verdict(818.4, 818.5, clean, 21)
    assert not identical and "score moved" in verdict


def test_exact_only_divergence_is_still_a_behavior_change() -> None:
    """compare_fingerprint_streams tolerates last-ulp drift across machines;
    an optimization claim on one machine must not."""
    comparison = {"exact": {"frame": 1500}, "rounded": None}
    identical, verdict = trajectory_verdict(818.4, 818.4, comparison, 21)
    assert not identical
    assert verdict.startswith("DIFFERENT")


def test_count_checkpoints_ignores_header_and_result(tmp_path: Path) -> None:
    stream = tmp_path / "s.jsonl"
    records = [
        {"type": "header", "frame": 0},
        {"type": "checkpoint", "frame": 250},
        {"type": "checkpoint", "frame": 500},
        {"type": "result", "frame": 500},
    ]
    stream.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    assert count_checkpoints(stream) == 2
