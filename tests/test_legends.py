"""Tests for in-world legends (roadmap E6 / backlog U8b).

The acceptance bar from ``docs/UI_IMPROVEMENTS.md`` U8b: names are stable
across reloads, promotion is deterministic, duplicates are prevented, and
benchmark champions are not mixed with in-world legends.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.legend_criteria import LegendCriteriaConfig, LegendCriteriaSuite, LegendSample
from backend.legend_service import LegendService
from backend.legends import LEGEND_KINDS, SCHEMA_VERSION, LegendStore, legend_name, make_legend
from backend.world_manager import WorldManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sample(frame: int, population: int, ages=None, lineages=None) -> LegendSample:
    return LegendSample(
        frame=frame,
        simulation_time=frame / 30.0,
        population=population,
        ages=ages or {},
        lineage_members=lineages or {},
    )


def legend(**overrides):
    base = {
        "kind": "longevity_record",
        "subject_type": "fish",
        "subject_id": "1",
        "title": "t",
        "reason": "r",
        "frame": 1,
        "simulation_time": 0.0,
    }
    base.update(overrides)
    return make_legend(**base)


# ---------------------------------------------------------------------------
# Names are stable across reloads
# ---------------------------------------------------------------------------


def test_names_are_a_pure_function_of_the_subject_id():
    # Stability across reloads reduces to this: nothing but the id decides it.
    assert legend_name("7") == legend_name("7")
    assert legend_name("7") != legend_name("8")


def test_names_do_not_depend_on_process_hash_randomisation():
    """A name built on ``hash()`` would change every server restart."""
    import subprocess
    import sys

    script = "from backend.legends import legend_name; print(legend_name('lineage-42'))"
    runs = {
        subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
        ).stdout.strip()
        for seed in ("0", "1", "12345")
    }
    assert len(runs) == 1, f"name varied with hash seed: {runs}"


def test_names_stay_distinct_past_the_first_cycle():
    # 24 x 24 = 576 combinations, then a cycle suffix keeps them unique.
    names = {legend_name(str(i)) for i in range(1200)}
    assert len(names) == 1200


def test_name_survives_a_store_round_trip():
    store = LegendStore(world_id="w")
    stored = store.add(legend(subject_id="99"))
    restored = LegendStore()
    restored.load(store.to_payload())
    assert restored.recent()[0]["name"] == stored["name"] == legend_name("99")


# ---------------------------------------------------------------------------
# Duplicates are prevented
# ---------------------------------------------------------------------------


def test_the_same_subject_is_not_promoted_twice_for_the_same_reason():
    store = LegendStore()
    assert store.add(legend(subject_id="5")) is not None
    assert store.add(legend(subject_id="5")) is None
    assert len(store.recent()) == 1


def test_the_same_subject_may_hold_two_different_titles():
    store = LegendStore()
    assert store.add(legend(subject_id="5", kind="longevity_record")) is not None
    assert store.add(legend(subject_id="5", kind="collapse_survivor")) is not None
    assert len(store.recent()) == 2


def test_a_legend_dropped_by_the_buffer_cap_cannot_be_re_promoted():
    # The dedup set outlives the record, or a long run would re-crown the same
    # fish every time its legend scrolled off.
    store = LegendStore(max_legends=2)
    for i in range(4):
        store.add(legend(subject_id=str(i)))
    assert len(store.recent()) == 2
    assert store.add(legend(subject_id="0")) is None


def test_dedup_survives_a_restore():
    store = LegendStore()
    store.add(legend(subject_id="5"))
    restored = LegendStore()
    restored.load(store.to_payload())
    assert restored.add(legend(subject_id="5")) is None


def test_clear_allows_re_promotion():
    store = LegendStore()
    store.add(legend(subject_id="5"))
    assert store.clear() == 1
    assert store.add(legend(subject_id="5")) is not None


# ---------------------------------------------------------------------------
# Promotion is deterministic
# ---------------------------------------------------------------------------


def build_sequence() -> list[LegendSample]:
    samples = []
    for step in range(24):
        frame = 600 * (step + 1)
        population = max(0, 40 - 3 * step) if step < 13 else 4 + 3 * step
        ages = {i: 1000 + step * 500 + i for i in range(1, max(1, population // 2) + 1)}
        lineages = {"1": list(range(1, max(1, population // 2) + 1))}
        samples.append(sample(frame, population, ages=ages, lineages=lineages))
    return samples


def test_identical_samples_produce_identical_ordered_promotions():
    first, second = LegendService(), LegendService()
    sequence = build_sequence()
    a = [x for s in sequence for x in first.observe(s)]
    b = [x for s in sequence for x in second.observe(s)]
    assert a == b
    assert [x["id"] for x in a] == list(range(1, len(a) + 1))


def test_lineage_promotions_are_ordered_by_lineage_id_not_dict_order():
    members = {"a": list(range(1, 21)), "b": list(range(21, 41))}
    forward = LegendCriteriaSuite().evaluate(sample(600, 40, lineages=members))
    reverse = LegendCriteriaSuite().evaluate(
        sample(600, 40, lineages=dict(reversed(list(members.items()))))
    )
    assert [x["subject_id"] for x in forward] == ["a", "b"]
    assert forward == reverse


def test_a_replayed_frame_promotes_nothing_new():
    service = LegendService()
    first = service.observe(sample(600, 40, ages={1: 9000}))
    assert len(first) == 1
    assert service.observe(sample(600, 40, ages={1: 9000})) == []


# ---------------------------------------------------------------------------
# Criteria: longevity record
# ---------------------------------------------------------------------------


def test_longevity_requires_passing_the_minimum_age():
    suite = LegendCriteriaSuite()
    assert suite.evaluate(sample(600, 40, ages={1: 100})) == []
    assert suite.evaluate(sample(1200, 40, ages={1: 9000})) != []


def test_longevity_fires_once_until_the_record_is_beaten():
    suite = LegendCriteriaSuite()
    assert len(suite.evaluate(sample(600, 40, ages={1: 5000}))) == 1
    # Same fish, still the oldest, but no new record.
    assert suite.evaluate(sample(1200, 40, ages={1: 5000})) == []
    # A different fish passing it is a new record.
    promotions = suite.evaluate(sample(1800, 40, ages={1: 5000, 2: 6000}))
    assert [x["subject_id"] for x in promotions] == ["2"]


def test_longevity_records_its_evidence():
    suite = LegendCriteriaSuite()
    suite.evaluate(sample(600, 40, ages={1: 5000}))
    promotion = suite.evaluate(sample(1200, 40, ages={2: 7000}))[0]
    assert promotion["evidence"]["age_frames"] == 7000
    assert promotion["evidence"]["previous_record_frames"] == 5000


# ---------------------------------------------------------------------------
# Criteria: lineage founder
# ---------------------------------------------------------------------------


def test_lineage_founder_needs_both_share_and_absolute_size():
    suite = LegendCriteriaSuite()
    # 100% share but only 3 fish: a three-fish tank cannot mint a dynasty.
    assert suite.evaluate(sample(600, 3, lineages={"1": [1, 2, 3]})) == []
    # Enough members but too small a share.
    assert suite.evaluate(sample(1200, 100, lineages={"1": list(range(1, 11))})) == []
    # Both satisfied.
    assert suite.evaluate(sample(1800, 20, lineages={"1": list(range(1, 13))})) != []


def test_lineage_founder_subject_is_the_lineage_not_a_fish():
    suite = LegendCriteriaSuite()
    promotion = suite.evaluate(sample(600, 20, lineages={"7": list(range(1, 13))}))[0]
    assert promotion["subject_type"] == "lineage"
    assert promotion["subject_id"] == "7"
    assert promotion["evidence"]["living_descendants"] == 12


# ---------------------------------------------------------------------------
# Criteria: collapse survivor
# ---------------------------------------------------------------------------


def test_collapse_survivors_are_crowned_only_after_recovery():
    suite = LegendCriteriaSuite()
    # Crash. Nothing is promoted while the tank is still down.
    assert suite.evaluate(sample(600, 4, ages={1: 10, 2: 20, 3: 30, 4: 40})) == []
    assert suite.evaluate(sample(1200, 5, ages={1: 10, 2: 20, 3: 30, 4: 40, 9: 1})) == []
    # Recovery.
    promotions = suite.evaluate(sample(1800, 40, ages=dict.fromkeys([1, 2, 3, 4, 9], 100)))
    assert [x["subject_id"] for x in promotions] == ["1", "2", "3", "4"]
    assert promotions[0]["evidence"]["low_population"] == 4


def test_a_fish_that_arrived_after_the_crash_did_not_survive_it():
    suite = LegendCriteriaSuite()
    suite.evaluate(sample(600, 4, ages={1: 10, 2: 20}))
    promotions = suite.evaluate(sample(1200, 40, ages={1: 100, 2: 200, 77: 5}))
    assert "77" not in [x["subject_id"] for x in promotions]


def test_a_fish_that_died_before_recovery_did_not_survive_it():
    suite = LegendCriteriaSuite()
    suite.evaluate(sample(600, 4, ages={1: 10, 2: 20}))
    suite.evaluate(sample(1200, 12, ages={1: 30}))  # fish 2 is gone
    promotions = suite.evaluate(sample(1800, 40, ages={1: 100, 2: 200}))
    assert [x["subject_id"] for x in promotions] == ["1"]


def test_a_healthy_tank_never_enters_collapse():
    suite = LegendCriteriaSuite()
    for step in range(6):
        assert suite.collapse.evaluate(sample(600 * (step + 1), 40, ages={1: 10})) == []
    assert suite.collapse.in_collapse is False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_longevity_frames": 0},
        {"lineage_share": 0.0},
        {"lineage_min_members": 0},
        {"collapse_at_or_below": 20, "collapse_recovered_at_or_above": 20},
    ],
)
def test_config_rejects_incoherent_thresholds(kwargs):
    with pytest.raises(ValueError):
        LegendCriteriaConfig(**kwargs)


def test_config_round_trips_and_falls_back_on_junk():
    config = LegendCriteriaConfig(min_longevity_frames=99)
    assert LegendCriteriaConfig.from_payload(config.to_payload()) == config
    assert LegendCriteriaConfig.from_payload({"lineage_share": 0}) == LegendCriteriaConfig()
    assert LegendCriteriaConfig.from_payload("nonsense") == LegendCriteriaConfig()


# ---------------------------------------------------------------------------
# Record contract and persistence
# ---------------------------------------------------------------------------


def test_make_legend_rejects_unknown_kinds_and_subjects():
    with pytest.raises(ValueError):
        legend(kind="most_charming")
    with pytest.raises(ValueError):
        legend(subject_type="plant")


def test_records_carry_no_wall_clock_field():
    stored = LegendStore().add(legend())
    assert not {"created_at", "timestamp", "wall_time"} & set(stored)


def test_restore_keeps_legends_and_criterion_state():
    service = LegendService()
    for s in build_sequence():
        service.observe(s)
    before = service.recent()
    assert before

    restored = LegendService()
    restored.load(service.to_payload())
    assert restored.recent() == before
    assert restored.to_payload() == service.to_payload()

    # Re-running the same history promotes nobody new.
    for s in build_sequence():
        restored.observe(s)
    assert restored.recent() == before


def test_unknown_schema_payload_fails_safe():
    service = LegendService()
    service.observe(sample(600, 40, ages={1: 9000}))
    payload = service.to_payload()
    payload["schema_version"] = SCHEMA_VERSION + 99

    restored = LegendService()
    restored.load(payload)
    assert restored.recent() == []
    assert restored.last_evaluated_frame == 0


@pytest.mark.parametrize("payload", [None, {}, "nonsense", {"schema_version": None}])
def test_missing_or_junk_payloads_are_tolerated(payload):
    service = LegendService()
    service.load(payload)
    assert service.recent() == []


# ---------------------------------------------------------------------------
# Legends are not benchmark champions
# ---------------------------------------------------------------------------


def test_the_legend_modules_never_read_the_champion_registry():
    """U8b's hard line: an in-world legend is not a validated benchmark result.

    Enforced over the AST rather than by grepping the text, so prose explaining
    the distinction is fine while *code* that reaches for champion data is not.
    The two are easy to conflate and the consequence of conflating them is
    presenting a lucky in-world fish as a validated benchmark result.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    modules = (
        "backend/legends.py",
        "backend/legend_criteria.py",
        "backend/legend_service.py",
        "backend/routers/legends.py",
        "backend/runner/legend_sampler.py",
    )
    for name in modules:
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        identifiers: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                identifiers += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                identifiers.append(node.module or "")
                identifiers += [alias.name for alias in node.names]
            elif isinstance(node, ast.Name):
                identifiers.append(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.append(node.attr)
        offenders = [x for x in identifiers if "champion" in x.lower()]
        assert not offenders, f"{name} reaches for champion data: {offenders}"


def test_legend_kinds_are_a_closed_set():
    assert set(LEGEND_KINDS) == {
        "longevity_record",
        "lineage_founder",
        "collapse_survivor",
    }


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


@pytest.fixture
def client_and_world():
    context = AppContext(world_manager=WorldManager())
    app = create_app(context=context, server_id="test-server")
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "tank",
                "name": "Legend Test",
                "persistent": False,
                "seed": 42,
                "start_paused": True,
            },
        )
        assert response.status_code == 201, response.text
        yield test_client, response.json()["world_id"]


def seed_legends(test_client, world_id):
    manager = test_client.app.state.context.world_manager
    service = manager.get_world(world_id).runner.legends
    service.observe(sample(600, 20, ages={1: 9000}, lineages={"3": list(range(1, 13))}))
    return service


def test_get_legends_returns_the_contract_envelope(client_and_world):
    test_client, world_id = client_and_world
    seed_legends(test_client, world_id)
    body = test_client.get(f"/api/world/{world_id}/legends").json()
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["kinds"] == list(LEGEND_KINDS)
    assert body["count"] == len(body["legends"]) == 2
    assert {x["kind"] for x in body["legends"]} == {"longevity_record", "lineage_founder"}


def test_get_legends_filters_by_kind_and_rejects_unknown_kinds(client_and_world):
    test_client, world_id = client_and_world
    seed_legends(test_client, world_id)
    filtered = test_client.get(f"/api/world/{world_id}/legends?kind=lineage_founder").json()
    assert filtered["count"] == 1
    assert test_client.get(f"/api/world/{world_id}/legends?kind=nope").status_code == 400


def test_legends_endpoint_is_read_only(client_and_world):
    test_client, world_id = client_and_world
    assert test_client.post(f"/api/world/{world_id}/legends", json={}).status_code == 405


def test_delete_legends_clears_the_roster(client_and_world):
    test_client, world_id = client_and_world
    seed_legends(test_client, world_id)
    assert test_client.delete(f"/api/world/{world_id}/legends").json()["cleared"] == 2
    assert test_client.get(f"/api/world/{world_id}/legends").json()["count"] == 0


def test_unknown_world_returns_404(client_and_world):
    test_client, _ = client_and_world
    assert test_client.get("/api/world/nope/legends").status_code == 404


def test_runner_owns_a_legend_service_that_persists_through_a_snapshot(client_and_world):
    test_client, world_id = client_and_world
    runner = test_client.app.state.context.world_manager.get_world(world_id).runner
    assert isinstance(runner.legends, LegendService)
    seed_legends(test_client, world_id)

    from backend.runner_stores import capture_runner_stores, restore_runner_stores

    snapshot: dict = {}
    capture_runner_stores(runner, snapshot)
    assert "legends" in snapshot

    runner.legends = LegendService()
    restore_runner_stores(runner, snapshot)
    assert len(runner.legends.recent()) == 2


def test_frontend_legend_type_declares_every_record_field():
    """The TS ``Legend`` interface must cover the whole backend record."""
    import re
    from pathlib import Path

    record = LegendStore(world_id="w").add(legend())
    source = (
        Path(__file__).resolve().parents[1] / "frontend" / "src" / "types" / "legend.ts"
    ).read_text(encoding="utf-8")
    start = source.index("export interface Legend {")
    body = source[start : source.index("}", start)]

    missing = [key for key in record if f"{key}:" not in body and f"{key}?:" not in body]
    assert not missing, f"frontend Legend is missing fields: {missing}"

    start = source.index("export type LegendKind =")
    declared = set(re.findall(r"'([a-z_]+)'", source[start : source.index(";", start)]))
    assert declared == set(LEGEND_KINDS)
