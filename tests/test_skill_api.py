"""Tests for the skill-ladder standings REST endpoint."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import skill
from core.skill import RungResult, SkillLadderSummary


def _client_for(champions_dir: Path) -> TestClient:
    app = FastAPI()
    app.include_router(skill.setup_router(champions_dir=champions_dir))
    return TestClient(app)


def _write_champion(path: Path, summary: SkillLadderSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"champion": {"metadata": {"skill": summary.to_dict()}}}),
        encoding="utf-8",
    )


def test_ladders_endpoint_returns_summaries(tmp_path):
    summary = SkillLadderSummary(
        domain="poker",
        benchmark_id="poker/ladder_20k",
        metric_name="bb_per_100",
        skill_index=100.0,
        rungs=(RungResult("L0", "random", 1000.0, beaten=True),),
    )
    _write_champion(tmp_path / "poker" / "ladder_20k.json", summary)

    resp = _client_for(tmp_path).get("/api/skill/ladders")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == skill.SCHEMA_VERSION
    assert len(body["ladders"]) == 1
    assert body["ladders"][0]["domain"] == "poker"
    assert body["ladders"][0]["skill_index"] == 100.0


def test_ladders_endpoint_skips_skilless_champions(tmp_path):
    (tmp_path / "tank").mkdir(parents=True)
    (tmp_path / "tank" / "survival_5k.json").write_text(
        json.dumps({"champion": {"metadata": {"avg_pop": 50}}}), encoding="utf-8"
    )

    resp = _client_for(tmp_path).get("/api/skill/ladders")
    assert resp.status_code == 200
    assert resp.json()["ladders"] == []


def test_ladders_endpoint_handles_empty_dir(tmp_path):
    resp = _client_for(tmp_path).get("/api/skill/ladders")
    assert resp.status_code == 200
    assert resp.json()["ladders"] == []


def test_foraging_gym_endpoint_evaluates_current_substrate(tmp_path):
    response = _client_for(tmp_path).get("/api/skill/foraging-gym?seed=42")

    assert response.status_code == 200
    body = response.json()
    assert body["benchmark_id"] == "tank/foraging_gym"
    assert 0.0 <= body["score"] <= 1.0
    assert body["score_breakdown"]["oracle_energy_ratio"] == 1.0
    assert body["metadata"]["skill"]["domain"] == "foraging"
