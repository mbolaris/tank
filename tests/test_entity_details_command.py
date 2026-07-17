"""Contract tests for the ``get_entity_details`` command (fish inspector, U4/E1).

The command must return rich fish details addressed by the *snapshot* id the
client sees in broadcasts, fail cleanly for unknown ids, and — critically —
never consume simulation RNG or mutate simulation state (guardrail #1 in
docs/EXPERIENCE_ROADMAP.md).
"""

from __future__ import annotations

import pytest

from backend.simulation_runner import SimulationRunner


@pytest.fixture(scope="module")
def runner() -> SimulationRunner:
    """A real tank runner (not started) so identity provider and fish exist."""
    return SimulationRunner(seed=42)


def _fish_snapshot(runner: SimulationRunner):
    snapshots = runner._collect_entities()
    fish = [s for s in snapshots if s.type == "fish"]
    assert fish, "expected the initial tank population to contain fish"
    return fish[0]


def test_fish_details_success(runner: SimulationRunner) -> None:
    snapshot = _fish_snapshot(runner)
    result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})

    assert result["success"] is True
    details = result["details"]
    assert details["id"] == snapshot.id
    assert details["type"] == "fish"

    # Vital signs
    assert details["energy"] >= 0
    assert details["max_energy"] > 0
    assert 0.0 <= details["energy_ratio"] <= 1.5
    assert details["status"] in {"critical", "hungry", "content", "full"}
    assert details["age"] >= 0
    assert details["max_age"] > 0
    assert details["life_stage"] is not None
    assert details["generation"] >= 0

    # Taxonomy is observational metadata: it is present for classified fish
    # and distinguishes an informal lineage from an established species.
    taxonomy = details["taxonomy"]
    assert snapshot.taxonomy is not None
    assert taxonomy["taxon_id"] == snapshot.taxonomy["taxon_id"]
    assert taxonomy["common_name"] == snapshot.taxonomy["common_name"]
    assert taxonomy["scientific_name"] == snapshot.taxonomy["scientific_name"]
    assert taxonomy["status"] in {"provisional", "established", "extinct"}

    # Lineage
    lineage = details["lineage"]
    assert "parent_id" in lineage
    assert lineage["is_soup_spawn"] == (lineage["parent_id"] is None)

    # Behavior: on-demand fields the broadcast strips
    behavior = details["behavior"]
    assert behavior["algorithm"], "expected a readable algorithm name"
    assert behavior["behavior_id"]
    assert isinstance(behavior["parameters"], dict) and behavior["parameters"]

    # Heritable traits
    assert details["traits"], "expected at least one trait value"

    # Game participation
    games = details["games"]
    assert isinstance(games["poker"]["eligible"], bool)
    assert games["poker"]["cooldown_frames"] >= 0
    assert isinstance(games["soccer"]["ball_present"], bool)
    assert isinstance(games["soccer"]["eligible"], bool)


def test_details_matches_broadcast_energy(runner: SimulationRunner) -> None:
    """The detail payload describes the same entity the broadcast id points at."""
    snapshot = _fish_snapshot(runner)
    result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})
    details = result["details"]
    assert details["energy"] == pytest.approx(snapshot.energy, abs=0.11)
    assert details["generation"] == snapshot.generation


def test_unknown_entity_id_is_clean_error(runner: SimulationRunner) -> None:
    result = runner.handle_command("get_entity_details", {"entity_id": 999_999_999})
    assert result["success"] is False
    assert result["error"] == "entity_not_found"
    assert result["entity_id"] == 999_999_999


def test_invalid_entity_id_is_clean_error(runner: SimulationRunner) -> None:
    result = runner.handle_command("get_entity_details", {"entity_id": "not-a-number"})
    assert result["success"] is False
    assert "Invalid entity_id" in result["error"]

    result = runner.handle_command("get_entity_details", {})
    assert result["success"] is False


def test_non_fish_entity_gets_generic_details(runner: SimulationRunner) -> None:
    snapshots = runner._collect_entities()
    others = [s for s in snapshots if s.type in ("plant", "castle", "crab")]
    assert others, "expected the initial tank to contain non-fish entities"
    snapshot = others[0]

    result = runner.handle_command("get_entity_details", {"entity_id": snapshot.id})
    assert result["success"] is True
    assert result["details"]["type"] == snapshot.type


def test_details_do_not_consume_rng_or_mutate_state(runner: SimulationRunner) -> None:
    """Telemetry purity: the handler must not perturb the simulation."""
    snapshot = _fish_snapshot(runner)
    rng_state_before = runner.world.rng.getstate()
    entity_states_before = [(s.id, s.x, s.y, s.energy, s.age) for s in runner._collect_entities()]

    runner.handle_command("get_entity_details", {"entity_id": snapshot.id})
    runner.handle_command("get_entity_details", {"entity_id": 999_999_999})

    assert runner.world.rng.getstate() == rng_state_before
    entity_states_after = [(s.id, s.x, s.y, s.energy, s.age) for s in runner._collect_entities()]
    assert entity_states_after == entity_states_before
