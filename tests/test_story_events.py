"""Tests for the structured story-event service (roadmap E3 / backlog U6).

Covers the record contract (``backend.story_events``), the three detectors
(``backend.story_detectors``) against synthetic sample sequences, the service
seam (``backend.story_event_service``), the read-only sampler
(``backend.runner.story_sampler``), and the REST endpoints wired through the app
factory.

The acceptance bar these pin, from ``docs/UI_IMPROVEMENTS.md`` U6:
identical samples produce identical ordered events; restart persistence does not
duplicate events; buffer limits work; old schema payloads fail safely; and no
event is emitted repeatedly while a metric remains on one side of a threshold.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.runner import story_sampler
from backend.story_detectors import (
    DEFAULT_POPULATION_DANGER,
    DEFAULT_POPULATION_RECOVERED,
    StoryDetectorConfig,
    StoryDetectorSuite,
    StorySample,
)
from backend.story_event_service import StoryEventService
from backend.story_events import (
    EVENT_TYPES,
    SCHEMA_VERSION,
    SEVERITIES,
    StoryEventStore,
    make_event,
)
from backend.world_manager import WorldManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sample(frame: int, population: int, max_generation: int = 0, lineages=None) -> StorySample:
    """A synthetic sample; simulation_time is derived so records stay realistic."""
    return StorySample(
        frame=frame,
        simulation_time=frame / 30.0,
        population=population,
        max_generation=max_generation,
        lineage_members=lineages or {},
    )


def run(suite: StoryDetectorSuite, samples: list[StorySample]) -> list[dict]:
    events: list[dict] = []
    for s in samples:
        events.extend(suite.observe(s))
    return events


# ---------------------------------------------------------------------------
# Record contract
# ---------------------------------------------------------------------------


def test_make_event_normalizes_every_contract_field():
    event = make_event(
        event_type="population_danger",
        frame=600,
        simulation_time=20.0,
        severity="concern",
        title="  Population fell to 4  ",
        detector_name="population_danger",
        detector_threshold={"population_danger_at_or_below": 15},
        entity_ids=[9, 3, 5],
        lineage_ids=["b", "a"],
        metrics_before={"population": 22},
        metrics_after={"population": 4},
    )
    # The full field set U6 specifies, minus the store-assigned id/schema_version.
    assert set(event) == {
        "event_type",
        "frame",
        "simulation_time",
        "severity",
        "title",
        "entity_ids",
        "lineage_ids",
        "metrics_before",
        "metrics_after",
        "detector_name",
        "detector_threshold",
        "replay_ref",
    }
    assert event["entity_ids"] == [3, 5, 9], "entity ids are sorted for stable records"
    assert event["lineage_ids"] == ["a", "b"]
    assert event["title"] == "Population fell to 4"
    assert event["replay_ref"] is None, "replay is not claimed unless data exists"


def test_make_event_rejects_unknown_type_and_coerces_unknown_severity():
    with pytest.raises(ValueError):
        make_event(
            event_type="fish_became_president",
            frame=1,
            simulation_time=0.0,
            severity="info",
            title="t",
            detector_name="d",
        )
    event = make_event(
        event_type="generation_milestone",
        frame=1,
        simulation_time=0.0,
        severity="apocalyptic",
        title="t",
        detector_name="d",
    )
    assert event["severity"] == "info"


def test_event_records_carry_no_wall_clock_field():
    """Records must be reproducible; a wall clock would make them run-specific."""
    service = StoryEventService()
    stored = service.observe(sample(frame=120, population=4))
    assert stored, "a collapsing population should produce an event"
    assert not {"created_at", "timestamp", "wall_time"} & set(stored[0])


def test_every_declared_severity_is_a_known_severity():
    assert set(SEVERITIES) >= {"info", "insight", "concern"}


# ---------------------------------------------------------------------------
# Detector 1: population danger / recovery
# ---------------------------------------------------------------------------


def test_population_danger_fires_once_while_below_threshold():
    suite = StoryDetectorSuite()
    events = run(suite, [sample(f, population=6) for f in (120, 240, 360, 480)])
    assert [e["event_type"] for e in events] == ["population_danger"]
    assert events[0]["metrics_after"] == {"population": 6}
    assert events[0]["detector_threshold"] == {
        "population_danger_at_or_below": DEFAULT_POPULATION_DANGER
    }


def test_population_recovery_needs_the_higher_threshold():
    suite = StoryDetectorSuite()
    # 20 clears the danger threshold but not the recovery threshold.
    events = run(suite, [sample(120, 6), sample(240, 20), sample(360, 20)])
    assert [e["event_type"] for e in events] == ["population_danger"]

    events = suite.observe(sample(480, 26))
    assert [e["event_type"] for e in events] == ["population_recovered"]
    assert events[0]["metrics_before"] == {"population": 20}
    assert events[0]["metrics_after"] == {"population": 26}


def test_population_hysteresis_prevents_chatter_on_the_boundary():
    """Oscillating between the two thresholds must not emit a second event."""
    suite = StoryDetectorSuite()
    low = DEFAULT_POPULATION_DANGER + 1
    high = DEFAULT_POPULATION_RECOVERED - 1
    samples = [sample(120, 2)] + [sample(120 * (i + 2), high if i % 2 else low) for i in range(20)]
    events = run(suite, samples)
    assert [e["event_type"] for e in events] == ["population_danger"]


def test_population_danger_and_recovery_can_alternate_across_real_cycles():
    suite = StoryDetectorSuite()
    events = run(
        suite,
        [sample(120, 5), sample(240, 40), sample(360, 5), sample(480, 40)],
    )
    assert [e["event_type"] for e in events] == [
        "population_danger",
        "population_recovered",
        "population_danger",
        "population_recovered",
    ]


def test_extinction_is_reported_as_danger():
    suite = StoryDetectorSuite()
    events = suite.observe(sample(120, 0))
    assert [e["event_type"] for e in events] == ["population_danger"]
    assert events[0]["metrics_after"] == {"population": 0}


# ---------------------------------------------------------------------------
# Detector 2: generation milestones
# ---------------------------------------------------------------------------


def test_generation_milestone_fires_on_each_new_multiple():
    suite = StoryDetectorSuite()
    events = run(
        suite,
        [sample(f, 40, max_generation=g) for f, g in [(120, 4), (240, 5), (360, 9), (480, 10)]],
    )
    assert [e["metrics_after"]["milestone"] for e in events] == [5, 10]
    assert events[0]["title"] == "Generation 5 reached"


def test_generation_milestone_is_silent_between_multiples():
    suite = StoryDetectorSuite()
    events = run(suite, [sample(120 * (i + 1), 40, max_generation=7) for i in range(10)])
    assert [e["metrics_after"]["milestone"] for e in events] == [5]


def test_generation_milestone_announces_only_the_highest_crossed():
    """A fast-forward that skips milestones yields one event, not a flood."""
    suite = StoryDetectorSuite()
    events = run(suite, [sample(120, 40, max_generation=2), sample(240, 40, max_generation=97)])
    assert len(events) == 1
    assert events[0]["metrics_after"] == {"milestone": 95, "max_generation": 97}
    assert events[0]["metrics_before"] == {"milestone": 0, "max_generation": 2}


def test_generation_milestone_never_fires_backwards():
    suite = StoryDetectorSuite()
    run(suite, [sample(120, 40, max_generation=20)])
    events = run(suite, [sample(240, 40, max_generation=6), sample(360, 40, max_generation=12)])
    assert events == [], "a falling max generation re-announces nothing"


# ---------------------------------------------------------------------------
# Detector 3: lineage share
# ---------------------------------------------------------------------------


# A healthy population (well above the danger threshold) so these samples
# exercise the lineage detector alone.
POP = 40


def split(first_count: int) -> dict[str, list[int]]:
    """Two lineages sharing a population of ``POP``, the first holding N members."""
    return {"1": list(range(1, first_count + 1)), "2": list(range(first_count + 1, POP + 1))}


def test_lineage_dominance_fires_when_share_crosses_the_threshold():
    suite = StoryDetectorSuite()
    events = run(
        suite,
        [sample(120, POP, lineages=split(16)), sample(240, POP, lineages=split(24))],
    )
    assert [e["event_type"] for e in events] == ["lineage_dominant", "lineage_dominant"]
    assert events[0]["lineage_ids"] == ["2"], "the 0.6 lineage is announced first"
    assert events[1]["lineage_ids"] == ["1"]
    assert events[1]["metrics_after"]["share"] == 0.6
    assert events[1]["metrics_before"]["share"] == 0.4


def test_lineage_dominance_is_latched_while_the_share_holds():
    suite = StoryDetectorSuite()
    events = run(suite, [sample(120 * (i + 1), POP, lineages=split(32)) for i in range(8)])
    assert [e["event_type"] for e in events] == ["lineage_dominant"]


def test_lineage_can_be_announced_again_after_falling_back():
    suite = StoryDetectorSuite()
    events = run(suite, [sample(120, POP, lineages=split(32))])
    assert [e["lineage_ids"] for e in events] == [["1"]]
    # 0.3 is below the 0.4 relinquish threshold, so lineage 1 un-latches; the
    # newly-dominant lineage 2 is announced on that same sample.
    events = run(
        suite,
        [sample(240, POP, lineages=split(12)), sample(360, POP, lineages=split(32))],
    )
    assert [e["lineage_ids"] for e in events] == [["2"], ["1"]]


def test_lineage_events_are_ordered_by_lineage_id_not_dict_order():
    forward = StoryDetectorSuite()
    reverse = StoryDetectorSuite()
    members = {"a": list(range(1, 21)), "b": list(range(21, 41))}
    first = forward.observe(sample(120, POP, lineages=members))
    second = reverse.observe(sample(120, POP, lineages=dict(reversed(list(members.items())))))
    assert [e["lineage_ids"] for e in first] == [["a"], ["b"]]
    assert first == second


def test_lineage_entity_ids_are_capped():
    suite = StoryDetectorSuite()
    events = suite.observe(sample(120, 20, lineages={"1": list(range(100, 120))}))
    assert len(events[0]["entity_ids"]) == StoryDetectorConfig().max_entity_ids
    assert events[0]["metrics_after"]["members"] == 20, "the true count is still reported"


def test_empty_population_yields_no_lineage_shares():
    assert sample(120, 0, lineages={"1": []}).shares() == {}


# ---------------------------------------------------------------------------
# Detector configuration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"population_danger_at_or_below": 20, "population_recovered_at_or_above": 20},
        {"generation_milestone_interval": 0},
        {"lineage_dominant_share": 0.0},
        {"lineage_dominant_share": 0.5, "lineage_relinquish_share": 0.6},
        {"max_entity_ids": -1},
    ],
)
def test_config_rejects_thresholds_without_hysteresis(kwargs):
    with pytest.raises(ValueError):
        StoryDetectorConfig(**kwargs)


def test_config_round_trips_and_falls_back_on_junk():
    config = StoryDetectorConfig(population_danger_at_or_below=4, generation_milestone_interval=25)
    assert StoryDetectorConfig.from_payload(config.to_payload()) == config
    assert StoryDetectorConfig.from_payload({"generation_milestone_interval": 0}) == (
        StoryDetectorConfig()
    )
    assert StoryDetectorConfig.from_payload("not a dict") == StoryDetectorConfig()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def build_sequence() -> list[StorySample]:
    samples: list[StorySample] = []
    for step in range(30):
        frame = 120 * (step + 1)
        population = max(0, 30 - 2 * step) if step < 20 else 10 + step
        lineages = {
            "1": list(range(0, max(1, population // 2))),
            "7": list(range(100, 100 + max(1, population // 2))),
        }
        samples.append(sample(frame, population, max_generation=step // 2, lineages=lineages))
    return samples


def test_identical_samples_produce_identical_ordered_events():
    first = StoryEventService()
    second = StoryEventService()
    sequence = build_sequence()
    a = [e for s in sequence for e in first.observe(s)]
    b = [e for s in sequence for e in second.observe(s)]
    assert a == b
    assert [e["id"] for e in a] == list(range(1, len(a) + 1)), "ids are dense and monotonic"


# ---------------------------------------------------------------------------
# Service: cadence, idempotence, persistence
# ---------------------------------------------------------------------------


def test_detection_is_due_only_on_interval_boundaries():
    service = StoryEventService(detect_interval_frames=120)
    assert not service.is_detection_due(0)
    assert not service.is_detection_due(119)
    assert service.is_detection_due(120)
    assert service.is_detection_due(240)


def test_replayed_or_duplicated_frames_do_not_duplicate_events():
    service = StoryEventService()
    assert len(service.observe(sample(120, 3))) == 1
    assert service.observe(sample(120, 3)) == []
    assert service.observe(sample(60, 3)) == []
    assert not service.is_detection_due(120)


def test_restart_persistence_does_not_duplicate_or_re_announce():
    service = StoryEventService()
    for s in build_sequence():
        service.observe(s)
    before = service.recent()
    assert before, "the synthetic run should have produced events"

    restored = StoryEventService()
    restored.load(service.to_payload())
    assert restored.recent() == before
    assert restored.to_payload() == service.to_payload()

    # Re-observing the same sequence after a restore adds nothing: the frames
    # are already observed and the latches are already set.
    for s in build_sequence():
        restored.observe(s)
    assert restored.recent() == before


def test_restored_latches_still_fire_on_a_genuine_new_transition():
    service = StoryEventService()
    service.observe(sample(120, 3))
    restored = StoryEventService()
    restored.load(service.to_payload())
    events = restored.observe(sample(240, 40))
    assert [e["event_type"] for e in events] == ["population_recovered"]
    assert events[0]["id"] == 2, "ids continue from the restored store"


def test_buffer_limit_drops_oldest_and_keeps_ids_unique():
    store = StoryEventStore(max_events=3)
    for index in range(10):
        store.add(
            make_event(
                event_type="generation_milestone",
                frame=index,
                simulation_time=0.0,
                severity="insight",
                title=f"m{index}",
                detector_name="generation_milestone",
            )
        )
    assert len(store.events) == 3
    assert [e["id"] for e in store.recent()] == [8, 9, 10]
    assert store.recent(since_id=9) == store.recent(limit=1)


def test_recent_filters_by_since_id_and_type():
    service = StoryEventService()
    service.observe(sample(120, 3, max_generation=10))
    types = {e["event_type"] for e in service.recent()}
    assert types == {"population_danger", "generation_milestone"}
    assert len(service.recent(event_type="population_danger")) == 1
    latest = service.recent()[-1]["id"]
    assert service.recent(since_id=latest) == []


def test_clear_empties_the_buffer_but_keeps_ids_monotonic():
    service = StoryEventService()
    service.observe(sample(120, 3))
    assert service.clear() == 1
    assert service.recent() == []
    service.observe(sample(240, 40))
    assert service.recent()[0]["id"] == 2


def test_unknown_schema_payload_fails_safe():
    service = StoryEventService()
    service.observe(sample(120, 3))
    payload = service.to_payload()
    payload["schema_version"] = SCHEMA_VERSION + 99

    restored = StoryEventService()
    restored.load(payload)
    assert restored.recent() == [], "an unreadable payload leaves an empty store"
    assert restored.last_observed_frame == 0, "and untouched detector state"
    # A fresh store on an unknown payload still works normally afterwards.
    assert len(restored.observe(sample(120, 3))) == 1


@pytest.mark.parametrize("payload", [None, {}, "nonsense", {"schema_version": None}])
def test_missing_or_junk_payloads_are_tolerated(payload):
    service = StoryEventService()
    service.load(payload)
    assert service.recent() == []


def test_world_id_rebinds_through_the_service():
    service = StoryEventService(world_id="old")
    service.world_id = "new"
    assert service.to_payload()["world_id"] == "new"


# ---------------------------------------------------------------------------
# Sampler: read-only observation of a runner
# ---------------------------------------------------------------------------


class FakeFish:
    def __init__(self, fish_id: int, generation: int) -> None:
        self.fish_id = fish_id
        self.generation = generation
        self.genome = object()


class FakeLineage:
    def __init__(self, records) -> None:
        self.lineage_log = records
        self.get_lineage_data_calls = 0

    def get_lineage_data(self, alive_fish_ids=None):  # pragma: no cover - must not be called
        self.get_lineage_data_calls += 1
        return self.lineage_log


class FakeWorld:
    def __init__(self, entities, lineage_records, frame=120) -> None:
        self.entities_list = entities
        self.frame_count = frame
        self.ecosystem = type("Eco", (), {"lineage": FakeLineage(lineage_records)})()


class FakeRunner:
    def __init__(self, world) -> None:
        self.world = world
        self.story_events = StoryEventService()


def lineage_record(fish_id: int, parent_id) -> dict:
    return {"id": str(fish_id), "parent_id": "root" if parent_id is None else str(parent_id)}


def test_sampler_groups_living_fish_under_their_founders():
    # 1 founds a line (2, 4 descend from it); 3 founds its own.
    world = FakeWorld(
        entities=[FakeFish(2, 3), FakeFish(4, 4), FakeFish(3, 1)],
        lineage_records=[
            lineage_record(1, None),
            lineage_record(2, 1),
            lineage_record(4, 2),
            lineage_record(3, None),
        ],
    )
    sampled = story_sampler.build_sample(FakeRunner(world), 120)
    assert sampled.population == 3
    assert sampled.max_generation == 4
    assert sampled.lineage_members == {"1": [2, 4], "3": [3]}
    assert sampled.shares() == pytest.approx({"1": 2 / 3, "3": 1 / 3})


def test_sampler_treats_an_unrecorded_fish_as_its_own_founder():
    world = FakeWorld(entities=[FakeFish(42, 0)], lineage_records=[])
    sampled = story_sampler.build_sample(FakeRunner(world), 120)
    assert sampled.lineage_members == {"42": [42]}


def test_sampler_survives_a_lineage_cycle():
    world = FakeWorld(
        entities=[FakeFish(1, 0)],
        lineage_records=[lineage_record(1, 2), lineage_record(2, 1)],
    )
    sampled = story_sampler.build_sample(FakeRunner(world), 120)
    assert len(sampled.lineage_members) == 1


def test_sampler_never_calls_the_mutating_lineage_accessor():
    """``get_lineage_data`` repairs orphans in place; detection must not mutate."""
    world = FakeWorld(entities=[FakeFish(1, 0)], lineage_records=[lineage_record(1, None)])
    story_sampler.build_sample(FakeRunner(world), 120)
    assert world.ecosystem.lineage.get_lineage_data_calls == 0


def test_observe_if_due_respects_the_cadence_and_stores_events():
    world = FakeWorld(entities=[FakeFish(1, 0)], lineage_records=[], frame=119)
    runner = FakeRunner(world)
    assert story_sampler.observe_if_due(runner) == []
    world.frame_count = 120
    events = story_sampler.observe_if_due(runner)
    # A lone survivor is both a population emergency and a total lineage sweep.
    assert [e["event_type"] for e in events] == ["population_danger", "lineage_dominant"]
    assert story_sampler.observe_if_due(runner) == []


def test_observe_if_due_is_inert_without_a_service_and_swallows_failures():
    world = FakeWorld(entities=[FakeFish(1, 0)], lineage_records=[])
    runner = FakeRunner(world)
    runner.story_events = None
    assert story_sampler.observe_if_due(runner) == []

    broken = FakeRunner(FakeWorld(entities=[FakeFish(1, 0)], lineage_records=[]))
    broken.world.entities_list = "not iterable in the way we expect"
    broken.world.frame_count = 120

    class Exploding:
        def __iter__(self):
            raise RuntimeError("boom")

    broken.world.entities_list = Exploding()
    assert story_sampler.observe_if_due(broken) == []


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


@pytest.fixture
def client_and_world():
    """A test client with one fresh, paused tank world; yields (client, world_id)."""
    context = AppContext(world_manager=WorldManager())
    app = create_app(context=context, server_id="test-server")
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "tank",
                "name": "Story Event Test",
                "persistent": False,
                "seed": 42,
                "start_paused": True,
            },
        )
        assert response.status_code == 201, response.text
        yield test_client, response.json()["world_id"]


def story_service(test_client, world_id):
    world_manager = test_client.app.state.context.world_manager
    return world_manager.get_world(world_id).runner.story_events


def seed_events(test_client, world_id) -> None:
    """Push a synthetic sample into a world's service without running frames."""
    story_service(test_client, world_id).observe(sample(120, 3, max_generation=10))


def test_get_story_events_returns_the_contract_envelope(client_and_world):
    test_client, world_id = client_and_world
    seed_events(test_client, world_id)
    response = test_client.get(f"/api/world/{world_id}/story-events")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["world_id"] == world_id
    assert body["event_types"] == list(EVENT_TYPES)
    assert body["last_observed_frame"] == 120
    assert body["count"] == len(body["events"]) == 2
    assert [e["event_type"] for e in body["events"]] == [
        "population_danger",
        "generation_milestone",
    ]


def test_get_story_events_supports_incremental_polling(client_and_world):
    test_client, world_id = client_and_world
    seed_events(test_client, world_id)
    everything = test_client.get(f"/api/world/{world_id}/story-events").json()["events"]
    assert len(everything) == 2

    # ``limit`` keeps the *most recent* N, the way a feed opens on the latest rows.
    latest = test_client.get(f"/api/world/{world_id}/story-events?limit=1").json()["events"]
    assert [e["id"] for e in latest] == [everything[-1]["id"]]

    # ``since_id`` is the incremental poll: only what arrived after that id.
    tail = test_client.get(
        f"/api/world/{world_id}/story-events?since_id={everything[0]['id']}"
    ).json()
    assert [e["id"] for e in tail["events"]] == [everything[-1]["id"]]
    assert tail["count"] == 1


def test_get_story_events_filters_by_type_and_rejects_unknown_types(client_and_world):
    test_client, world_id = client_and_world
    seed_events(test_client, world_id)
    filtered = test_client.get(
        f"/api/world/{world_id}/story-events?event_type=population_danger"
    ).json()
    assert filtered["count"] == 1
    assert test_client.get(f"/api/world/{world_id}/story-events?event_type=nope").status_code == 400


def test_story_events_endpoint_is_read_only(client_and_world):
    """Story events are measured, not submitted; the Board is the write surface."""
    test_client, world_id = client_and_world
    assert test_client.post(f"/api/world/{world_id}/story-events", json={}).status_code == 405


def test_default_world_alias_resolves(client_and_world):
    test_client, _ = client_and_world
    assert test_client.get("/api/world/default/story-events").status_code == 200


def test_delete_story_events_clears_the_buffer(client_and_world):
    test_client, world_id = client_and_world
    seed_events(test_client, world_id)
    assert test_client.delete(f"/api/world/{world_id}/story-events").json()["cleared"] == 2
    assert test_client.get(f"/api/world/{world_id}/story-events").json()["count"] == 0


def test_unknown_world_returns_404(client_and_world):
    test_client, _ = client_and_world
    assert test_client.get("/api/world/does-not-exist/story-events").status_code == 404


# ---------------------------------------------------------------------------
# Runner wiring
# ---------------------------------------------------------------------------


def test_runner_owns_a_story_service_that_persists_through_a_snapshot(client_and_world):
    test_client, world_id = client_and_world
    runner = test_client.app.state.context.world_manager.get_world(world_id).runner
    assert isinstance(runner.story_events, StoryEventService)

    runner.story_events.observe(sample(120, 3))

    from backend.runner_stores import capture_runner_stores, restore_runner_stores

    snapshot: dict = {}
    capture_runner_stores(runner, snapshot)
    assert "story_events" in snapshot
    assert "commentary" in snapshot and "metrics_history" in snapshot

    runner.story_events = StoryEventService()
    restore_runner_stores(runner, snapshot)
    assert len(runner.story_events.recent()) == 1
    assert runner.story_events.last_observed_frame == 120


def test_set_world_identity_rebinds_every_telemetry_store(client_and_world):
    test_client, world_id = client_and_world
    runner = test_client.app.state.context.world_manager.get_world(world_id).runner
    try:
        runner.set_world_identity("renamed-world")
        assert runner.story_events.world_id == "renamed-world"
        assert runner.commentary.world_id == "renamed-world"
        assert runner.metrics_history.world_id == "renamed-world"
    finally:
        runner.set_world_identity(world_id)
