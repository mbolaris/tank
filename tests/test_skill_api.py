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


def test_foraging_gym_summary_endpoint(tmp_path):
    client = _client_for(tmp_path)
    response = client.get("/api/skill/foraging-gym/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "engine_baseline"
    assert body["benchmark_id"] == "tank/foraging_gym"
    assert "config_hash" in body
    assert 0.0 <= body["mean"] <= 1.0
    assert 0.0 <= body["wandering_mean"] <= 1.0
    assert body["perfect_mean"] == 1.0
    assert len(body["confidence_interval"]) == 2
    assert body["confidence_interval"][0] <= body["mean"] <= body["confidence_interval"][1]
    assert len(body["range"]) == 2
    assert body["range"][0] <= body["mean"] <= body["range"][1]
    assert body["average_food"] > 0
    assert body["average_food_available"] == 12.0
    assert body["average_energy"] > 0
    assert "metadata" in body
    assert len(body["metadata"]["seeds"]) == 8
    assert "42" in body["metadata"]["per_seed"]

    # Verify caching (should use cached result and not call benchmarks.run again)
    from unittest.mock import patch
    from benchmarks.tank.foraging_gym import run as real_run
    from backend.routers.skill import _FORAGING_GYM_SUMMARY_CACHE

    with patch("benchmarks.tank.foraging_gym.run", wraps=real_run) as mock_run:
        _FORAGING_GYM_SUMMARY_CACHE.clear()

        response1 = client.get("/api/skill/foraging-gym/summary")
        assert response1.status_code == 200
        assert mock_run.call_count == 8

        response2 = client.get("/api/skill/foraging-gym/summary")
        assert response2.status_code == 200
        assert mock_run.call_count == 8


def test_foraging_gym_observatory_no_world_manager(tmp_path):
    client = _client_for(tmp_path)
    response = client.get("/api/skill/foraging-gym/observatory")
    assert response.status_code == 200
    assert response.json()["status"] == "no_data"


def test_foraging_gym_observatory_with_fish(tmp_path):
    from unittest.mock import MagicMock
    from core.entities.fish import Fish
    from core.taxonomy.registry import SpeciesRecord
    from core.taxonomy.profile import TaxonomyProfile

    # Mock species record
    type_profile = TaxonomyProfile(traits={"prediction_skill": 0.48}, is_microbe=False)
    spec_rec = MagicMock(spec=SpeciesRecord)
    spec_rec.taxon_id = "spec_1"
    spec_rec.common_name = "Silver Sailfins"
    spec_rec.living_member_ids = {481}
    spec_rec.max_generation = 5
    spec_rec.type_profile = type_profile

    # Mock taxonomy registry
    registry = MagicMock()
    registry.species = {"spec_1": spec_rec}

    # Mock taxonomy system
    taxonomy = MagicMock()
    taxonomy.registry = registry

    # Mock fish
    mock_fish = MagicMock(spec=Fish)
    mock_fish.fish_id = 481
    mock_fish.taxon_id = "spec_1"
    mock_fish.common_name = "Silver Sailfins"
    mock_fish.generation = 5

    # genome setup
    mock_fish.genome = MagicMock()
    mock_fish.genome.behavioral = MagicMock()
    mock_fish.genome.behavioral.prediction_skill = MagicMock()
    mock_fish.genome.behavioral.prediction_skill.value = 0.71

    # Mock world/runner
    world = MagicMock()
    world.entities_list = [mock_fish]
    world.ecosystem = MagicMock()
    world.ecosystem.taxonomy = taxonomy

    runner = MagicMock()
    runner.world = world

    instance = MagicMock()
    instance.runner = runner
    instance.world_id = "world_1"

    world_manager = MagicMock()
    world_manager.list_worlds.return_value = [instance]
    world_manager.get_world.return_value = instance

    # Setup app with the mock world manager
    app = FastAPI()
    app.include_router(skill.setup_router(champions_dir=tmp_path, world_manager=world_manager))
    client = TestClient(app)

    from unittest.mock import patch

    with (
        patch("backend.routers.skill.evaluate_custom_genome") as mock_eval,
        patch("core.genetics.genome_codec.genome_to_dict") as mock_g_dict,
    ):

        # Mock evaluation results in gym
        mock_res = MagicMock()
        mock_res.composable_ratio = 0.74
        mock_res.composable = MagicMock()
        mock_res.composable.food_collected = 10
        mock_eval.return_value = mock_res
        mock_g_dict.return_value = {"some": "traits"}

        response = client.get("/api/skill/foraging-gym/observatory")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        import pytest

        assert body["tank_average"] == pytest.approx(0.74)
        assert body["best_species"]["name"] == "Silver Sailfins"
        assert body["best_species"]["score"] == pytest.approx(0.74)
        assert body["best_individual"]["id"] == 481
        assert body["best_individual"]["score"] == pytest.approx(0.74)
        assert body["best_individual"]["food_collected"] == 10
        assert body["best_individual"]["prediction_strength_before"] == 0.48
        assert body["best_individual"]["prediction_strength_after"] == 0.71
