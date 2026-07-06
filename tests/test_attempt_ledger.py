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
    assert "attempt_id" in record1
    assert len(record1["attempt_id"]) == 36  # UUID length
    assert "files_changed" in record1
    assert "benchmark_command" in record1

    # Log with explicit rich fields
    log_attempt(
        benchmark_id="test_bench",
        verdict="error",
        candidate_score=None,
        champion_score=1.00,
        ledger_path=ledger_file,
        attempt_id="custom-uuid-123",
        parent_attempt_id="parent-uuid-456",
        base_commit="basecommitsha",
        agent_model="claude-3-5-sonnet",
        prompt_template_id="v1-prompt",
        files_changed=["core/reproduction/reproduction_service.py"],
        tests_run=["tests/test_reproduction_params.py"],
        benchmark_command="python tools/run_bench.py custom",
        duration=4.56,
        exit_code=1,
        failure_reason="Mating threshold too high",
        accepted_by_gate=False,
        champion_updated=False,
    )

    with open(ledger_file, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 3
    record3 = json.loads(lines[2])
    assert record3["attempt_id"] == "custom-uuid-123"
    assert record3["parent_attempt_id"] == "parent-uuid-456"
    assert record3["base_commit"] == "basecommitsha"
    assert record3["agent_model"] == "claude-3-5-sonnet"
    assert record3["prompt_template_id"] == "v1-prompt"
    assert record3["files_changed"] == ["core/reproduction/reproduction_service.py"]
    assert record3["tests_run"] == ["tests/test_reproduction_params.py"]
    assert record3["benchmark_command"] == "python tools/run_bench.py custom"
    assert record3["duration"] == 4.56
    assert record3["exit_code"] == 1
    assert record3["failure_reason"] == "Mating threshold too high"
    assert record3["accepted_by_gate"] is False
    assert record3["champion_updated"] is False

    record2 = json.loads(lines[1])
    assert record2["benchmark_id"] == "test_bench"
    assert record2["verdict"] == "rejected"
    assert record2["candidate_score"] == 0.95
    assert record2["champion_score"] == 1.00
    assert record2["seed"] == 42
    assert record2["config_hash"] == "abc123hash"
    assert record2["agent_id"] == "test-agent"
    assert record2["description"] == "Regressed speed"
