"""PR 0 Soccer Arena contract tests."""

from __future__ import annotations

from types import SimpleNamespace

from core.minigames.soccer.adapters.tank_adapter import adapt_engine_state
from core.minigames.soccer.coords import (
    CanonicalPoint,
    LegacyPoint,
    canonical_to_legacy,
    legacy_to_canonical,
)
from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector
from core.minigames.soccer.field_profiles import (
    SoccerFieldGeometry,
    get_field_profile,
    rcss_standard_105x68,
    reset_profile_warning_state,
    tank_small_sided,
)
from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.evaluator import (
    create_soccer_match_from_participants,
    finalize_soccer_match,
)
from backend.state_payloads.soccer import SoccerParticipantPayload
from core.minigames.soccer.reconciliation import (
    InMemoryReconciliationStore,
    SoccerSettlement,
    SourceIdentity,
    build_world_source_resolver,
    reconcile_match,
)
from core.minigames.soccer.roster_snapshot import snapshot_roster
from core.minigames.soccer.participant import SoccerParticipant
from core.minigames.soccer.types import SoccerMinigameOutcome
from core.simulation.event_managers import SoccerEventManager


class _Fish:
    def __init__(self, fish_id: int, tank_id: str = "tank-a") -> None:
        self.fish_id = fish_id
        self.tank_id = tank_id
        self.energy = 100.0
        self.dead = False

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        self.energy += amount
        return amount


class _ReproComponent:
    def __init__(self, credits: float = 3.0, *, fail: bool = False) -> None:
        self.repro_credits = credits
        self.fail = fail

    def add_repro_credits(self, amount: float) -> float:
        if self.fail:
            raise RuntimeError("injected reproduction failure")
        self.repro_credits += amount
        return amount


def test_roster_snapshot_is_deep_and_match_isolated() -> None:
    fish = [_Fish(i) for i in range(4)]
    participants = [
        SoccerParticipant(
            participant_id=f"{'left' if i < 2 else 'right'}_{i % 2 + 1}",
            team="left" if i < 2 else "right",
            fish_id=item.fish_id,
            tank_id=item.tank_id,
        )
        for i, item in enumerate(fish)
    ]
    snapshot = snapshot_roster(participants)
    fish[0].tank_id = "changed"
    fish[0].energy = 1.0
    assert snapshot.participants[0].tank_id == "tank-a"
    assert not any("source_entity" in participant.__dict__ for participant in participants)

    first = SoccerMatch(
        match_id="contract-first",
        roster_snapshot=snapshot,
        duration_frames=20,
        seed=42,
    )
    for item in fish:
        item.energy = 0.0
    second = SoccerMatch.from_roster_snapshot(
        snapshot,
        match_id="contract-first",
        duration_frames=20,
        seed=42,
    )
    for match in (first, second):
        while not match.game_over:
            match.step(5)

    assert first.command_log == second.command_log
    assert first.events == second.events
    assert first.get_state()["entities"] == second.get_state()["entities"]
    assert first.get_state()["score"] == second.get_state()["score"]
    assert not hasattr(first, "_reconciliation_resolver")


def test_reconciliation_drops_dead_energy_keeps_statistics_and_is_idempotent() -> None:
    fish = _Fish(7)
    fish.dead = True
    identity = SourceIdentity(7, "tank-a")
    settlement = SoccerSettlement.for_match(
        "match-7",
        energy_deltas={identity: 12.0},
        statistics={identity: {"goals": 1}},
    )
    store = InMemoryReconciliationStore()
    first = reconcile_match(settlement, {(7, "tank-a"): fish}, store=store)
    second = reconcile_match(settlement, {(7, "tank-a"): fish}, store=store)
    assert fish.energy == 100.0
    assert first == second
    assert first.retained_statistics[identity]["goals"] == 1
    assert identity in first.dropped_dead_deltas


def test_reconciliation_drops_known_dead_source_removed_before_finalize() -> None:
    identity = SourceIdentity(8, "tank-a")
    settlement = SoccerSettlement.for_match(
        "removed-dead-8",
        energy_deltas={identity: 12.0},
        statistics={identity: {"goals": 1}},
    )
    result = reconcile_match(
        settlement,
        {},
        store=InMemoryReconciliationStore(),
        missing_as_dead={identity},
    )

    assert result.applied_energy_deltas == {}
    assert result.retained_statistics[identity]["goals"] == 1
    assert result.dropped_dead_deltas == (identity,)


def test_finalize_match_survives_fish_removed_after_selection() -> None:
    fish = [_Fish(10), _Fish(11)]
    live_fish = list(fish)
    world = SimpleNamespace(
        entity_manager=SimpleNamespace(get_fish=lambda: list(live_fish)),
        environment=SimpleNamespace(),
    )
    source_resolver = build_world_source_resolver(world)
    setup = create_soccer_match_from_participants(
        fish,
        duration_frames=1,
        match_id="removed-during-match",
        seed=42,
    )
    setup.match.winner_team = "left"
    setup.match.game_over = True
    for item in fish:
        item.dead = True
    live_fish.clear()

    outcome = finalize_soccer_match(
        setup.match,
        entry_fees=setup.entry_fees,
        source_resolver=source_resolver,
        reconciliation_store=InMemoryReconciliationStore(),
    )

    assert outcome.match_id == "removed-during-match"
    assert outcome.reconciliation_id is not None


def test_reconciliation_rolls_back_energy_and_repro_credits_atomically() -> None:
    first = _Fish(1)
    second = _Fish(2)
    first._reproduction_component = _ReproComponent()
    second._reproduction_component = _ReproComponent(fail=True)
    identities = [SourceIdentity(1, "tank-a"), SourceIdentity(2, "tank-a")]
    settlement = SoccerSettlement.for_match(
        "atomic-repro",
        energy_deltas={identities[0]: 10.0, identities[1]: 10.0},
        repro_credit_deltas={identities[0]: 2.0, identities[1]: 2.0},
    )
    before_energy = (first.energy, second.energy)
    before_credits = (
        first._reproduction_component.repro_credits,
        second._reproduction_component.repro_credits,
    )
    try:
        reconcile_match(
            settlement,
            {(1, "tank-a"): first, (2, "tank-a"): second},
            store=InMemoryReconciliationStore(),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("reproduction failure should abort settlement")
    assert (first.energy, second.energy) == before_energy
    assert (
        first._reproduction_component.repro_credits,
        second._reproduction_component.repro_credits,
    ) == before_credits


def test_reconciliation_store_round_trip_preserves_idempotency_result() -> None:
    fish = _Fish(3)
    identity = SourceIdentity(3, "tank-a")
    settlement = SoccerSettlement.for_match("persisted", energy_deltas={identity: 5.0})
    store = InMemoryReconciliationStore()
    result = reconcile_match(settlement, {(3, "tank-a"): fish}, store=store)
    restored = InMemoryReconciliationStore.from_dict(store.to_dict())
    assert restored.get(settlement.reconciliation_id) == result


def test_world_source_resolver_reads_transferred_entity_at_reconciliation_time() -> None:
    fish = _Fish(9, tank_id="tank-origin")
    fish.origin_tank_id = "tank-origin"
    world = SimpleNamespace(
        entity_manager=SimpleNamespace(get_fish=lambda: [fish]),
        environment=SimpleNamespace(),
    )
    resolver = build_world_source_resolver(world)
    fish.tank_id = "tank-current"
    assert resolver.resolve_fish(9, "tank-origin") is fish


def test_event_manager_deduplicates_statistics_and_outcomes() -> None:
    outcome = SoccerMinigameOutcome(
        match_id="stats-once",
        match_counter=1,
        winner_team="left",
        score_left=1,
        score_right=0,
        frames=10,
        seed=42,
        selection_seed=43,
        message="",
        rewarded={"left_1": 5.0},
        entry_fees={7: 1.0},
        energy_deltas={7: 4.0},
        repro_credit_deltas={},
        teams={"left": [7], "right": [8]},
        reconciliation_id="stats-once-id",
    )
    manager = SoccerEventManager()
    manager.add_outcome(10, outcome)
    manager.add_outcome(11, outcome)
    assert len(manager.get_recent(11, max_age_frames=100)) == 1
    assert manager.fish_leaders()[0]["matches"] == 1
    restored = SoccerEventManager()
    restored.restore_state(manager.to_dict())
    restored.add_outcome(12, outcome)
    assert restored.fish_leaders()[0]["matches"] == 1


def test_geometry_and_coordinate_contracts() -> None:
    assert rcss_standard_105x68.to_dict()["centre_circle_radius"] == 9.15
    assert "centre_circle_radius" not in SoccerFieldGeometry("no-circle", 10, 8, 2, 1).to_dict()
    assert (
        tank_small_sided.goal_width / tank_small_sided.width
        > rcss_standard_105x68.goal_width / rcss_standard_105x68.width
    )
    point = LegacyPoint(2.5, 3.0)
    assert canonical_to_legacy(legacy_to_canonical(point)) == point
    assert isinstance(legacy_to_canonical(point), CanonicalPoint)


def test_unknown_field_profile_warns_once_and_uses_complete_fallback(caplog) -> None:
    reset_profile_warning_state()
    with caplog.at_level("WARNING"):
        assert get_field_profile("missing-profile") == rcss_standard_105x68
        assert get_field_profile("missing-profile") == rcss_standard_105x68
    warnings = [
        record for record in caplog.records if "Unknown soccer field profile" in record.message
    ]
    assert len(warnings) == 1


def test_generic_participants_have_stable_team_wire_ids() -> None:
    match = SoccerMatch(
        match_id="generic-teams",
        entities=[
            SoccerParticipant(participant_id="left_bot", team="left"),
            SoccerParticipant(participant_id="right_bot", team="right"),
        ],
        duration_frames=1,
        seed=1,
    )
    state = match.get_state()
    assert state["teams"] == {"left": ["left_bot"], "right": ["right_bot"]}


def test_tank_adapter_is_engine_to_canonical_without_render_knowledge() -> None:
    engine = RCSSLiteEngine(seed=1)
    engine.add_player("left_1", "left", RCSSVector(-10, 4), body_angle=0.5)
    player = engine.get_player("left_1")
    player.stamina = 4000.0  # type: ignore[union-attr]
    player.velocity = RCSSVector(1.0, 2.0)  # type: ignore[union-attr]
    engine.set_ball_position(2, -3)
    engine.get_ball().velocity = RCSSVector(-1.0, 4.0)
    state = adapt_engine_state(engine)
    assert state["players"][0]["position"] == {"x": -10.0, "y": -4.0}
    assert state["players"][0]["velocity"] == {"x": 1.0, "y": -2.0}
    assert state["players"][0]["facing_angle"] == -0.5
    assert state["ball"]["position"] == {"x": 2.0, "y": 3.0}
    assert state["ball"]["velocity"] == {"x": -1.0, "y": -4.0}
    assert state["players"][0]["stamina"] == 0.5


def test_participant_wire_round_trip_covers_all_avatar_kinds() -> None:
    for avatar_kind in ("fish", "reference", "external", "bot"):
        payload = SoccerParticipantPayload(
            participant_id=f"{avatar_kind}_1",
            side="left",
            team_id="team-a",
            uniform_number=1,
            avatar_kind=avatar_kind,
            display_name="Example",
            fish_id=7 if avatar_kind == "fish" else None,
            tank_id="tank-a" if avatar_kind == "fish" else None,
            policy_label="chase_shoot_v1" if avatar_kind != "fish" else None,
        )
        restored = SoccerParticipantPayload(**payload.to_dict())
        assert restored.to_dict() == payload.to_dict()
