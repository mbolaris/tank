"""Tests for champion provenance validation."""

import json
from pathlib import Path

from tools.validate_champion_provenance import validate_all, validate_file


def test_checked_in_champions_have_valid_provenance():
    assert validate_all() == []


def test_rejects_missing_retirement_reason(tmp_path: Path):
    champions = tmp_path / "champions"
    path = champions / "tank" / "sample.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "benchmark_id": "tank/sample",
                "version": 2,
                "champion": {
                    "seed": 42,
                    "score": 2.0,
                    "timestamp": 1_700_000_200,
                    "config_hash": "0123456789abcdef",
                    "metadata": {"population_scope": "fish"},
                },
                "history": [
                    {
                        "benchmark_id": "tank/sample",
                        "version": 1,
                        "seed": 42,
                        "score": 1.0,
                        "timestamp": 1_700_000_000,
                        "retired_at": 1_700_000_100,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert any("retired_reason" in error for error in validate_file(path))


def test_rejects_ambiguous_tank_population_metadata(tmp_path: Path):
    path = tmp_path / "champions" / "tank" / "sample.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "benchmark_id": "tank/sample",
                "seed": 42,
                "score": 1.0,
                "timestamp": 1_700_000_000,
                "config_hash": "0123456789abcdef",
                "metadata": {"final_total_entities": 100},
            }
        ),
        encoding="utf-8",
    )

    errors = validate_file(path)
    assert any("population_scope" in error for error in errors)
    assert any("diagnostic_only" in error for error in errors)
