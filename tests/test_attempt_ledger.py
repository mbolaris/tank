"""Tests for the attempt ledger instrumentation.
"""

from __future__ import annotations

import json
from pathlib import Path
from core.research.attempt_ledger import log_attempt


def test_log_attempt(tmp_path: Path) -> None:
    ledger_file = tmp_path / "attempts.jsonl"

    # Log an accepted attempt
    log_attempt(
        benchmark_id="test_bench",
        verdict="accepted",
        candidate_score=1.23,
        champion_score=1.00,
        seed=42,
        config_hash="abc123hash",
        agent_id="test-agent",
        description="Improved speed slightly",
        ledger_path=ledger_file,
    )

    # Log a rejected attempt
    log_attempt(
        benchmark_id="test_bench",
        verdict="rejected",
        candidate_score=0.95,
        champion_score=1.00,
        seed=42,
        config_hash="abc123hash",
        agent_id="test-agent",
        description="Regressed speed",
        ledger_path=ledger_file,
    )

    # Read the file and assert
    assert ledger_file.exists()

    with open(ledger_file, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 2

    record1 = json.loads(lines[0])
    assert record1["benchmark_id"] == "test_bench"
    assert record1["verdict"] == "accepted"
    assert record1["candidate_score"] == 1.23
    assert record1["champion_score"] == 1.00
    assert record1["seed"] == 42
    assert record1["config_hash"] == "abc123hash"
    assert record1["agent_id"] == "test-agent"
    assert record1["description"] == "Improved speed slightly"
    assert "timestamp" in record1
    assert "timestamp_iso" in record1
    assert "branch" in record1
    assert "commit" in record1
    assert "diff_stat" in record1

    record2 = json.loads(lines[1])
    assert record2["benchmark_id"] == "test_bench"
    assert record2["verdict"] == "rejected"
    assert record2["candidate_score"] == 0.95
    assert record2["champion_score"] == 1.00
    assert record2["seed"] == 42
    assert record2["config_hash"] == "abc123hash"
    assert record2["agent_id"] == "test-agent"
    assert record2["description"] == "Regressed speed"
