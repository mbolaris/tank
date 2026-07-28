"""Append-only longitudinal records for frozen-ruler skill measurements."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from core.skill import SkillLadderSummary


def _git_sha() -> str | None:
    """Return the current commit when running inside a Git checkout."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def skill_history_records(
    summary: SkillLadderSummary,
    *,
    seeds: list[int],
    config_hash: str | None,
    timestamp: float | None = None,
    git_sha: str | None = None,
    command: str | None = None,
) -> list[dict[str, object]]:
    """Build one stable record per rung from a benchmark skill summary."""
    recorded_at = time.time() if timestamp is None else timestamp
    commit = _git_sha() if git_sha is None else git_sha
    records: list[dict[str, object]] = []
    for rung in summary.rungs:
        record: dict[str, object] = {
            "timestamp": recorded_at,
            "git_sha": commit,
            "config_hash": config_hash,
            "domain": summary.domain,
            "benchmark_id": summary.benchmark_id,
            "metric_name": summary.metric_name,
            "rung": rung.rung,
            "rung_id": rung.rung_id,
            "metric": rung.metric,
            "beaten": rung.beaten,
            "skill_index": summary.skill_index,
            "seeds": list(seeds),
        }
        if rung.ci_95 is not None:
            record["ci_95"] = [rung.ci_95[0], rung.ci_95[1]]
        if rung.detail:
            record["detail"] = dict(rung.detail)
        if command:
            record["command"] = command
        records.append(record)
    return records


def append_skill_history(
    summary: SkillLadderSummary,
    *,
    seeds: list[int],
    config_hash: str | None,
    ledger_path: str | Path,
    timestamp: float | None = None,
    git_sha: str | None = None,
    command: str | None = None,
) -> int:
    """Append a skill summary to JSONL and return the number of rows written."""
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = skill_history_records(
        summary,
        seeds=seeds,
        config_hash=config_hash,
        timestamp=timestamp,
        git_sha=git_sha,
        command=command,
    )
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return len(records)


def load_skill_history(path: str | Path) -> list[dict[str, object]]:
    """Read valid skill-history rows, ignoring missing or malformed lines."""
    history_path = Path(path)
    if not history_path.exists():
        return []
    records: list[dict[str, object]] = []
    with history_path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict):
                continue
            required = {"timestamp", "domain", "benchmark_id", "rung_id", "skill_index"}
            if required.issubset(value):
                records.append(value)
    return records
