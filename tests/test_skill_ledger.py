"""Tests for append-only longitudinal skill records and reporting."""

from __future__ import annotations

import json
from pathlib import Path

from core.research.skill_ledger import append_skill_history, load_skill_history
from core.skill import RungResult, SkillLadderSummary
from tools.skill_report import render_html, render_text, summarize


def _summary() -> SkillLadderSummary:
    return SkillLadderSummary(
        domain="foraging",
        benchmark_id="tank/foraging_gym",
        metric_name="energy_ratio",
        skill_index=67.5,
        rungs=(
            RungResult("L0", "random_walk_v1", 0.2, beaten=True),
            RungResult("L1", "oracle_v1", 1.0, beaten=False),
        ),
    )


def test_skill_history_appends_one_row_per_rung(tmp_path: Path) -> None:
    path = tmp_path / "skill_history.jsonl"
    rows = append_skill_history(
        _summary(),
        seeds=[42, 7, 123],
        config_hash="abc123",
        ledger_path=path,
        timestamp=100.0,
        git_sha="deadbeef",
        command="benchmark command",
    )

    assert rows == 2
    records = load_skill_history(path)
    assert len(records) == 2
    assert records[0]["skill_index"] == 67.5
    assert records[0]["seeds"] == [42, 7, 123]
    assert records[0]["git_sha"] == "deadbeef"


def test_skill_report_summarizes_change_and_renders(tmp_path: Path) -> None:
    path = tmp_path / "skill_history.jsonl"
    first = append_skill_history(
        _summary(), seeds=[42], config_hash="a", ledger_path=path, timestamp=1.0
    )
    assert first == 2
    changed = _summary()
    changed = SkillLadderSummary(
        changed.domain,
        changed.benchmark_id,
        changed.metric_name,
        82.0,
        changed.rungs,
    )
    append_skill_history(changed, seeds=[42], config_hash="b", ledger_path=path, timestamp=2.0)

    rows = summarize(load_skill_history(path))
    assert rows[0]["skill_index"] == 82.0
    assert rows[0]["change"] == 14.5
    assert "SKILL HISTORY" in render_text(rows)
    assert "Tank World Skill History" in render_html(rows, source=str(path))


def test_skill_history_rows_are_json_objects(tmp_path: Path) -> None:
    path = tmp_path / "skill_history.jsonl"
    append_skill_history(_summary(), seeds=[42], config_hash=None, ledger_path=path)
    assert all(isinstance(json.loads(line), dict) for line in path.read_text().splitlines())
