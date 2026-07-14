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
    from backend.skill_observatory_scoring import _FORAGING_GYM_SUMMARY_CACHE

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

    from backend.skill_evaluation_service import SkillEvaluationService

    observatory_result = {
        "status": "success",
        "world_id": "world_1",
        "evaluated_at_frame": 12,
        "evaluated_at_generation": 5,
        "benchmark_hash": "test-hash",
        "subject": "Full production movement controller",
        "tank_average": 0.74,
        "best_species": {"name": "Silver Sailfins", "score": 0.74},
        "best_individual": {
            "id": 481,
            "name": "Silver Sailfins #481",
            "score": 0.74,
            "food_collected": 10,
            "food_available": 12.0,
            "legacy_prediction_skill": 0.71,
            "species_founder_legacy_prediction_skill": 0.48,
            "parent_legacy_prediction_skill": 0.65,
            "pursuit_prediction_strength": None,
            "parent_pursuit_prediction_strength": None,
            "percentage_of_species": 100.0,
            "species_median": 0.60,
            "module_fingerprint": "graph_a1b2c3d4",
            "similar_fraction": 0.23,
            "score_uncertainty": 0.045,
            "sample_size": 8,
        },
        "engine_baseline": 0.5,
        "wandering_mean": 0.2,
        "perfect_mean": 1.0,
    }
    evaluation_service = SkillEvaluationService(world_manager)
    evaluation_service.store_result("world_1", observatory_result)

    # Setup app with the mock world manager and a completed background result.
    app = FastAPI()
    app.include_router(
        skill.setup_router(
            champions_dir=tmp_path,
            world_manager=world_manager,
            evaluation_service=evaluation_service,
        )
    )
    client = TestClient(app)

    from unittest.mock import patch

    with patch("backend.skill_observatory_scoring.evaluate_custom_genome") as mock_eval:
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
        assert body["best_individual"]["legacy_prediction_skill"] == 0.71
        assert body["best_individual"]["species_founder_legacy_prediction_skill"] == 0.48
        assert body["best_individual"]["parent_legacy_prediction_skill"] == 0.65
        assert body["best_individual"]["pursuit_prediction_strength"] is None
        assert body["best_individual"]["parent_pursuit_prediction_strength"] is None
        assert body["best_individual"]["species_median"] == 0.60
        assert body["best_individual"]["module_fingerprint"] == "graph_a1b2c3d4"
        assert body["best_individual"]["similar_fraction"] == 0.23
        assert body["best_individual"]["score_uncertainty"] == 0.045
        assert body["best_individual"]["sample_size"] == 8
        mock_eval.assert_not_called()


def _make_test_fish(env, *, fish_id, prediction_skill, generation=0, parent_id=None):
    """Build a real (non-mock) Fish with a real Genome, for exercising the
    actual snapshot/scoring logic rather than just the router's passthrough."""
    import random

    from core.entities.fish import Fish
    from core.genetics.genome import Genome
    from core.genetics.trait import GeneticTrait
    from core.movement_strategy import AlgorithmicMovement

    genome = Genome.random(use_algorithm=True, rng=random.Random(fish_id))
    genome.behavioral.prediction_skill = GeneticTrait(prediction_skill)
    return Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=0.0,
        y=0.0,
        speed=2.0,
        genome=genome,
        fish_id=fish_id,
        generation=generation,
        parent_id=parent_id,
    )


def _wire_observatory(tmp_path, world_manager):
    """Construct the router (wiring snapshot_builder/evaluator into the
    service) and return the service, without needing a TestClient/HTTP call."""
    from backend.skill_evaluation_service import SkillEvaluationService

    evaluation_service = SkillEvaluationService(world_manager)
    skill.setup_router(
        champions_dir=tmp_path,
        world_manager=world_manager,
        evaluation_service=evaluation_service,
    )
    return evaluation_service


def test_build_observatory_snapshot_is_immune_to_later_taxon_id_mutation(tmp_path):
    """A living fish's taxon_id can be reassigned by the taxonomy system on any
    simulation tick (species promotion swaps the record's id - see
    SpeciesRegistry.establish_species). The snapshot must capture the value at
    build time; it must not be a live reference that later mutation affects.
    """
    import random
    from unittest.mock import MagicMock

    from core.environment import Environment
    from core.taxonomy.profile import TaxonomyProfile

    env = Environment(width=800, height=600, rng=random.Random(1))
    fish = _make_test_fish(env, fish_id=1, prediction_skill=0.6)
    fish.taxon_id = "spec_1"
    fish.common_name = "Original Species"

    spec_rec = MagicMock()
    spec_rec.common_name = "Original Species"
    spec_rec.living_member_ids = {1}
    spec_rec.type_profile = TaxonomyProfile(traits={"prediction_skill": 0.5}, is_microbe=False)

    taxonomy = MagicMock()
    taxonomy.registry.species = {"spec_1": spec_rec}

    world = MagicMock()
    world.entities_list = [fish]
    world.ecosystem.taxonomy = taxonomy
    world.simulation_config = None
    world.genome_code_pool = None

    instance = MagicMock()
    instance.runner.world = world

    world_manager = MagicMock()
    world_manager.list_worlds.return_value = [instance]
    world_manager.get_world.return_value = instance

    evaluation_service = _wire_observatory(tmp_path, world_manager)

    snapshot = evaluation_service._snapshot_builder("world_1")
    assert not isinstance(snapshot, dict)
    assert snapshot.living_fish[0].taxon_id == "spec_1"

    # Simulate TaxonomySystem.update() promoting/renaming the species on a
    # later tick, after the snapshot was already captured.
    fish.taxon_id = "spec_1_established"

    assert snapshot.living_fish[0].taxon_id == "spec_1"


async def test_evaluate_observatory_snapshot_reports_independent_provenance_fields(
    tmp_path,
) -> None:
    """The four parent/self provenance fields must never conflate the legacy
    prediction_skill trait with the newer pursuit-module prediction_strength
    parameter - they measure genuinely different things, and a living parent's
    current value vs. a birth-time snapshot are different data sources too.
    """
    import random
    from unittest.mock import MagicMock, patch

    import pytest

    from core.behavior.pursuit_nodes import (
        default_pursuit_module_graph,
        pursuit_module_parameters,
    )
    from core.environment import Environment
    from core.foraging.gym import ForagingGymEvaluation, GymResult
    from core.genetics.trait import GeneticTrait
    from core.taxonomy.profile import TaxonomyProfile

    import backend.skill_observatory_scoring as skill_observatory_scoring

    skill_observatory_scoring._OBSERVATORY_EVALUATION_CACHE.clear()

    env = Environment(width=800, height=600, rng=random.Random(1))

    parent = _make_test_fish(env, fish_id=100, prediction_skill=0.30, generation=4)
    parent.taxon_id = "spec_1"
    parent.common_name = "Parent Fish"

    child = _make_test_fish(env, fish_id=101, prediction_skill=0.70, generation=5, parent_id=100)
    child.taxon_id = "spec_1"
    child.common_name = "Child Fish"
    child.parent_pursuit_params = {"prediction_strength": 0.55}
    pursuit_graph = default_pursuit_module_graph()
    child.genome.behavioral.target_pursuit_module = GeneticTrait(pursuit_graph)
    expected_pursuit_strength = pursuit_module_parameters(pursuit_graph)["prediction_strength"]

    spec_rec = MagicMock()
    spec_rec.common_name = "Spec One"
    spec_rec.living_member_ids = {100, 101}
    spec_rec.type_profile = TaxonomyProfile(traits={"prediction_skill": 0.4}, is_microbe=False)

    taxonomy = MagicMock()
    taxonomy.registry.species = {"spec_1": spec_rec}

    world = MagicMock()
    world.entities_list = [parent, child]
    world.ecosystem.taxonomy = taxonomy
    world.frame_count = 42
    world.simulation_config = None
    world.genome_code_pool = None

    instance = MagicMock()
    instance.runner.world = world

    world_manager = MagicMock()
    world_manager.list_worlds.return_value = [instance]
    world_manager.get_world.return_value = instance

    evaluation_service = _wire_observatory(tmp_path, world_manager)

    def fake_eval(genome, seed, **kwargs):
        score = genome.behavioral.prediction_skill.value
        return ForagingGymEvaluation(
            oracle_energy=100.0,
            oracle=GymResult(100.0, 10, 0.0, 0.0),
            random_walk=GymResult(20.0, 2, 0.0, 0.0),
            composable=GymResult(score * 100.0, 8, 0.0, 0.0),
        )

    with patch("backend.skill_observatory_scoring.evaluate_custom_genome", side_effect=fake_eval):
        result = await evaluation_service.refresh_world("world_1")

    assert result["status"] == "success"
    best = result["best_individual"]
    # The child has the higher prediction_skill (0.70 > 0.30), so it wins "best".
    assert best["id"] == 101
    assert best["legacy_prediction_skill"] == pytest.approx(0.70)
    assert best["parent_legacy_prediction_skill"] == pytest.approx(0.30)
    assert best["pursuit_prediction_strength"] == pytest.approx(expected_pursuit_strength)
    assert best["parent_pursuit_prediction_strength"] == pytest.approx(0.55)
    # The two "parent" fields must be genuinely different values - proof they
    # are no longer conflated into a single ambiguous field.
    assert best["parent_legacy_prediction_skill"] != best["parent_pursuit_prediction_strength"]


async def test_evaluate_observatory_snapshot_when_parent_not_living(tmp_path) -> None:
    """When the parent isn't among the living fish, parent_legacy_prediction_skill
    must be None rather than silently substituted with the pursuit-module
    snapshot, while parent_pursuit_prediction_strength still independently
    reports the birth-time value stashed on the fish itself.
    """
    import random
    from unittest.mock import MagicMock, patch

    import pytest

    from core.environment import Environment
    from core.foraging.gym import ForagingGymEvaluation, GymResult
    from core.taxonomy.profile import TaxonomyProfile

    import backend.skill_observatory_scoring as skill_observatory_scoring

    skill_observatory_scoring._OBSERVATORY_EVALUATION_CACHE.clear()

    env = Environment(width=800, height=600, rng=random.Random(1))

    # parent_id points at a fish that is not present in living_fish (departed
    # or dead), simulating exactly the case the legacy code silently mishandled.
    orphan = _make_test_fish(env, fish_id=201, prediction_skill=0.6, parent_id=999)
    orphan.taxon_id = "spec_2"
    orphan.common_name = "Orphan Fish"
    orphan.parent_pursuit_params = {"prediction_strength": 0.42}

    spec_rec = MagicMock()
    spec_rec.common_name = "Spec Two"
    spec_rec.living_member_ids = {201}
    spec_rec.type_profile = TaxonomyProfile(traits={"prediction_skill": 0.35}, is_microbe=False)

    taxonomy = MagicMock()
    taxonomy.registry.species = {"spec_2": spec_rec}

    world = MagicMock()
    world.entities_list = [orphan]
    world.ecosystem.taxonomy = taxonomy
    world.frame_count = 10
    world.simulation_config = None
    world.genome_code_pool = None

    instance = MagicMock()
    instance.runner.world = world

    world_manager = MagicMock()
    world_manager.list_worlds.return_value = [instance]
    world_manager.get_world.return_value = instance

    evaluation_service = _wire_observatory(tmp_path, world_manager)

    def fake_eval(genome, seed, **kwargs):
        return ForagingGymEvaluation(
            oracle_energy=100.0,
            oracle=GymResult(100.0, 10, 0.0, 0.0),
            random_walk=GymResult(20.0, 2, 0.0, 0.0),
            composable=GymResult(60.0, 8, 0.0, 0.0),
        )

    with patch("backend.skill_observatory_scoring.evaluate_custom_genome", side_effect=fake_eval):
        result = await evaluation_service.refresh_world("world_2")

    assert result["status"] == "success"
    best = result["best_individual"]
    assert best["parent_legacy_prediction_skill"] is None
    assert best["parent_pursuit_prediction_strength"] == pytest.approx(0.42)
    assert best["species_founder_legacy_prediction_skill"] == pytest.approx(0.35)
