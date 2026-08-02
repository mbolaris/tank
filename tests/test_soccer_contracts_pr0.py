"""PR 0 Soccer Arena contract tests."""

from __future__ import annotations

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
    rcss_standard_105x68,
    tank_small_sided,
)
from core.minigames.soccer.match import SoccerMatch
from backend.state_payloads.soccer import SoccerParticipantPayload
from core.minigames.soccer.reconciliation import (
    InMemoryReconciliationStore,
    SoccerSettlement,
    SourceIdentity,
    reconcile_match,
)
from core.minigames.soccer.roster_snapshot import snapshot_roster
from core.minigames.soccer.participant import SoccerParticipant


class _Fish:
    def __init__(self, fish_id: int, tank_id: str = "tank-a") -> None:
        self.fish_id = fish_id
        self.tank_id = tank_id
        self.energy = 100.0
        self.dead = False

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        self.energy += amount
        return amount


def _match(seed: int, fish: list[_Fish]) -> SoccerMatch:
    return SoccerMatch(match_id=f"contract-{seed}", entities=fish, duration_frames=20, seed=seed)


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

    first = _match(42, fish)
    for item in fish:
        item.energy = 0.0
    second = _match(42, fish)
    for match in (first, second):
        while not match.game_over:
            match.step(5)

    assert first.command_log == second.command_log
    assert first.events == second.events
    assert first.get_state()["entities"] == second.get_state()["entities"]
    assert first.get_state()["score"] == second.get_state()["score"]


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


def test_tank_adapter_is_engine_to_canonical_without_render_knowledge() -> None:
    engine = RCSSLiteEngine(seed=1)
    engine.add_player("left_1", "left", RCSSVector(-10, 4), body_angle=0.5)
    engine.get_player("left_1").stamina = 4000.0  # type: ignore[union-attr]
    engine.set_ball_position(2, -3)
    state = adapt_engine_state(engine)
    assert state["players"][0]["position"] == {"x": -10.0, "y": 4.0}
    assert state["ball"]["velocity"] == {"x": 0.0, "y": 0.0}
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
