"""Tests for the Strict Soccer League Runtime."""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.broadcast_metadata import compute_ball_owner
from core.minigames.soccer.league.types import TeamSource
from core.minigames.soccer.league_runtime import SoccerLeagueRuntime
from core.minigames.soccer.presentation import (
    PRESENTATION_MATCH_HOLD_TICKS,
    build_presentation_snapshot,
)


class DummyFish:
    def __init__(self, fish_id: int, energy: float) -> None:
        self.fish_id = fish_id
        self.energy = energy
        self.max_energy = 100.0
        self.genome = None
        self._age = 10

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        self.energy = max(0, self.energy + amount)
        return amount

    def is_dead(self) -> bool:
        return False

    @property
    def age(self) -> int:
        return self._age


class DummyWorld:
    def __init__(self, fish: list[DummyFish]) -> None:
        self._fish = fish
        self.entity_manager = self
        self.genome_code_pool = None
        self.world_id = "Tank1"

    def get_fish(self) -> list[DummyFish]:
        return list(self._fish)


@pytest.fixture
def base_config():
    return SoccerConfig(
        enabled=True,
        match_every_frames=1,
        duration_frames=10,
        team_size=11,  # Strict Requirement
        entry_fee_energy=0.0,
        cycles_per_frame=1,
    )


def test_strict_availability(base_config):
    """Test that teams with fewer than 11 players are marked unavailable."""
    runtime = SoccerLeagueRuntime(base_config)

    # Only 10 fish -> Should be unavailable
    fish = [DummyFish(i, 100.0) for i in range(10)]
    world = DummyWorld(fish)

    runtime.tick(world, seed_base=1, cycle=1)
    state = runtime.get_live_state()
    assert state is not None

    av = state["availability"]
    # Tank1:A should exist but be unavailable
    assert "Tank1:A" in av
    assert av["Tank1:A"]["available"] is False
    assert av["Tank1:A"]["count"] == 10

    # Bot:Balanced should be available
    assert "Bot:Balanced" in av
    assert av["Bot:Balanced"]["available"] is True


def test_team_forming(base_config):
    """Test that if we have 22 fish, we form Tank A and Tank B."""
    runtime = SoccerLeagueRuntime(base_config)

    # 25 fish -> A (11), B (11), 3 leftover
    fish = [DummyFish(i, 100.0) for i in range(25)]
    world = DummyWorld(fish)

    runtime.tick(world, seed_base=1, cycle=1)
    state = runtime.get_live_state()
    assert state is not None
    av = state["availability"]

    assert av["Tank1:A"]["available"] is True
    assert av["Tank1:A"]["count"] == 11

    assert av["Tank1:B"]["available"] is True
    assert av["Tank1:B"]["count"] == 11


def test_scheduler_skipping(base_config):
    """Test that matches involving unavailable teams are skipped."""
    # Config: 2 Teams (Tank A, Bot).
    # But Tank A is unavailable (0 fish).

    runtime = SoccerLeagueRuntime(base_config)
    world = DummyWorld([])  # No fish

    # Tick should trigger schedule generation
    # Schedule: Tank1:A vs Bot:Balanced
    # Tank1:A is unavailable -> Skip

    runtime.tick(world, seed_base=1, cycle=1)

    # Check logic implicitly via state or verify active match is None or skipping happened
    # In my implementation, it loops until it finds a playable match or ends season.
    # Since only 2 teams and one is bad, it should end season or idle.

    state = runtime.get_live_state()
    assert state is not None
    assert state["active_match"] is None

    # However, if we add a 3rd team (e.g. Bot 2), it might skip one and play the other.
    # Currently only 1 bot.


def test_full_match_flow(base_config):
    """Test a full match execution between available teams."""
    # We need 11 fish for Tank A to play against Bot.
    fish = [DummyFish(i, 100.0) for i in range(11)]
    world = DummyWorld(fish)

    runtime = SoccerLeagueRuntime(base_config)

    # 1. Start Match (Cycle 0 matches config.match_every_frames=1 if checked properly)
    runtime.tick(world, seed_base=1, cycle=100)
    state = runtime.get_live_state()
    assert state is not None

    assert state["active_match"] is not None
    match = state["active_match"]
    assert match["frame"] == 1  # Initial frame (stepped once)
    assert "Tank1:A" in [match["home_id"], match["away_id"]]
    assert "Bot:Balanced" in [match["home_id"], match["away_id"]]

    # 2. Step Match until end
    for _ in range(20):  # Duration is 10, should finish
        runtime.tick(world, seed_base=1, cycle=101 + _)

    state = runtime.get_live_state()
    assert state is not None

    # Should be game over or cleared
    # Runtime clears active match immediately after finalization in tick()
    # So active_match might be None now, but Leaderboard updated.

    lb = state["leaderboard"]
    tank_entry = next((e for e in lb if e["team_id"] == "Tank1:A"), None)
    bot_entry = next((e for e in lb if e["team_id"] == "Bot:Balanced"), None)

    assert tank_entry is not None
    assert bot_entry is not None
    assert tank_entry["matches_played"] >= 1
    assert bot_entry["matches_played"] >= 1

    # Verify strict outcome
    assert (
        tank_entry["wins"] + tank_entry["draws"] + tank_entry["losses"]
        == tank_entry["matches_played"]
    )


def test_derived_team_size():
    """Team size derives from num_players when team_size == 0."""
    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        duration_frames=10,
        team_size=0,
        num_players=8,
        entry_fee_energy=0.0,
        cycles_per_frame=1,
    )
    runtime = SoccerLeagueRuntime(config)

    # 8 fish, team_size = 8 // 2 = 4 → A (4), B (4)
    fish = [DummyFish(i, 100.0) for i in range(8)]
    world = DummyWorld(fish)

    runtime.tick(world, seed_base=1, cycle=1)
    state = runtime.get_live_state()
    assert state is not None
    av = state["availability"]

    assert av["Tank1:A"]["available"] is True
    assert av["Tank1:A"]["count"] == 4
    assert av["Tank1:B"]["available"] is True
    assert av["Tank1:B"]["count"] == 4


def test_smoke_league_produces_match_outcome():
    """Smoke test: with 10 fish and derived 3v3, the league completes a match."""
    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        duration_frames=10,
        team_size=0,
        num_players=6,  # derives team_size = 3
        entry_fee_energy=0.0,
        cycles_per_frame=1,
    )
    runtime = SoccerLeagueRuntime(config)

    fish = [DummyFish(i, 100.0) for i in range(10)]
    world = DummyWorld(fish)

    # Tick enough frames to start and complete at least one match
    match_started = False
    match_completed = False
    for cycle in range(50):
        runtime.tick(world, seed_base=42, cycle=cycle)

        state = runtime.get_live_state()
        if state and state["active_match"] is not None:
            match_started = True

        events = runtime.drain_events()
        if events:
            match_completed = True
            break

    assert match_started, "Expected at least one match to start within 50 frames"
    assert match_completed, "Expected at least one match outcome within 50 frames"


def test_default_config_is_self_funded_and_shaped():
    """The shipped league defaults reward skill via a self-funded shaped pot."""
    config = SoccerConfig()
    assert config.reward_mode == "shaped_pot"
    assert config.entry_fee_energy > 0.0


def test_entry_fee_filters_unaffordable_participants_without_crashing():
    """A nonzero entry fee must not raise when some rostered fish are too poor.

    Poor fish are dropped before match creation; the match still forms and
    completes from the affording fish, and the league records an outcome.
    """
    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        duration_frames=10,
        team_size=0,
        num_players=6,  # derives team_size = 3
        entry_fee_energy=5.0,
        reward_mode="shaped_pot",
        cycles_per_frame=1,
    )
    runtime = SoccerLeagueRuntime(config)

    # 6 wealthy fish (can afford the fee) + 4 broke fish (cannot).
    wealthy = [DummyFish(i, 100.0) for i in range(6)]
    broke = [DummyFish(100 + i, 1.0) for i in range(4)]
    world = DummyWorld(wealthy + broke)

    match_completed = False
    for cycle in range(50):
        # Must never raise even though broke fish are on the roster.
        runtime.tick(world, seed_base=42, cycle=cycle)
        if runtime.drain_events():
            match_completed = True
            break

    assert match_completed, "Expected a match to complete despite unaffordable fish on roster"
    # Broke fish never paid the fee (they were filtered out before match creation).
    for fish in broke:
        assert fish.energy == 1.0


def test_leaderboard_sorting(base_config):
    """Test leaderboard is sorted by Points then GD."""
    runtime = SoccerLeagueRuntime(base_config)

    # Hack in some state for testing get_live_state sorting
    from core.minigames.soccer.league.types import LeagueLeaderboardEntry

    runtime._leaderboard = {
        "A": LeagueLeaderboardEntry(
            "A", "A", TeamSource.TANK, points=3, goals_for=5, goals_against=1
        ),
        "B": LeagueLeaderboardEntry(
            "B", "B", TeamSource.TANK, points=3, goals_for=2, goals_against=1
        ),  # Worse GD
        "C": LeagueLeaderboardEntry("C", "C", TeamSource.TANK, points=0),
    }

    state = runtime.get_live_state()
    assert state is not None
    lb = state["leaderboard"]

    assert lb[0]["team_id"] == "A"
    assert lb[1]["team_id"] == "B"
    assert lb[2]["team_id"] == "C"


class _TankCfg:
    def __init__(self, enabled: bool) -> None:
        self.target_pursuit_module_enabled = enabled


class _SimCfg:
    def __init__(self, enabled: bool) -> None:
        self.tank = _TankCfg(enabled)


class _Env:
    def __init__(self, enabled: bool) -> None:
        self.simulation_config = _SimCfg(enabled)


class _Engine:
    """Stand-in for SimulationEngine: config lives on .environment, not here."""

    def __init__(self, enabled: bool) -> None:
        self.environment = _Env(enabled)


def test_pursuit_module_flag_read_from_engine_environment():
    """The league arm must find the flag on engine.environment.

    Regression: ``tick`` is called with the SimulationEngine, which has no
    ``simulation_config`` attribute. Reading the flag off the engine returned
    None unconditionally, so league matches always ran with the shared Target
    Pursuit Module disabled and tank-ball pursuit skill never transferred.
    """
    from core.minigames.soccer.league_runtime import _target_pursuit_module_enabled

    assert _target_pursuit_module_enabled(_Engine(True)) is True
    assert _target_pursuit_module_enabled(_Engine(False)) is False


def test_pursuit_module_flag_prefers_direct_config_then_environment():
    """A config on the world_state itself still wins; missing config is False."""
    from core.minigames.soccer.league_runtime import _target_pursuit_module_enabled

    class _Direct:
        def __init__(self) -> None:
            self.simulation_config = _SimCfg(True)
            self.environment = _Env(False)

    assert _target_pursuit_module_enabled(_Direct()) is True
    assert _target_pursuit_module_enabled(object()) is False
    assert _target_pursuit_module_enabled(None) is False


def _run_to_full_time(runtime, world, *, start_cycle: int, max_ticks: int = 50) -> int:
    """Tick a fixture from kickoff up to and including finalization.

    Stops on the tick that finalizes, so the presentation hold budget has not
    been spent yet. Returns the next cycle to use.
    """
    cycle = start_cycle
    runtime.tick(world, seed_base=1, cycle=cycle)
    assert runtime.get_live_state()["active_match"] is not None
    for _ in range(max_ticks):
        cycle += 1
        runtime.tick(world, seed_base=1, cycle=cycle)
        if runtime._active_match is None:
            return cycle + 1
    raise AssertionError("fixture never reached full time")


@pytest.fixture
def presentation_config(base_config):
    """A short fixture that will not immediately re-kickoff after full time."""
    base_config.duration_frames = 5
    base_config.match_every_frames = 100_000
    return base_config


def test_finalizing_clears_the_engine_but_retains_a_detached_snapshot(
    presentation_config,
):
    runtime = SoccerLeagueRuntime(presentation_config)
    world = DummyWorld([DummyFish(i, 100.0) for i in range(11)])

    _run_to_full_time(runtime, world, start_cycle=100_000)

    state = runtime.get_live_state()
    # The real match is gone: no engine, no setup, no live fixture metadata.
    assert state["active_match"] is None
    assert runtime._active_match is None
    assert runtime._active_setup is None

    snapshot = state["presentation_match"]
    assert snapshot is not None
    assert snapshot["game_over"] is True
    assert snapshot["play_mode"] == "time_over"
    # Identity is enriched exactly like a live match.
    assert snapshot["home_id"] and snapshot["away_id"]
    assert snapshot["home_name"] and snapshot["away_name"]
    assert snapshot["participants"]
    assert snapshot["geometry"]
    assert snapshot["entities"]


def test_snapshot_carries_final_score_and_one_full_time_event(presentation_config):
    runtime = SoccerLeagueRuntime(presentation_config)
    world = DummyWorld([DummyFish(i, 100.0) for i in range(11)])

    _run_to_full_time(runtime, world, start_cycle=100_000)
    snapshot = runtime.get_live_state()["presentation_match"]

    assert set(snapshot["score"]) == {"left", "right"}
    full_time = [e for e in snapshot["events"] if e["kind"] == "full_time"]
    assert len(full_time) == 1
    # Deterministic id derived only from match identity and event data.
    event = full_time[0]
    assert event["event_id"] == (
        f"{snapshot['match_id']}-full_time-{event['frame']}-{event['seq']}"
    )


def test_snapshot_survives_the_documented_ticks_then_expires(presentation_config):
    runtime = SoccerLeagueRuntime(presentation_config)
    world = DummyWorld([DummyFish(i, 100.0) for i in range(11)])

    cycle = _run_to_full_time(runtime, world, start_cycle=100_000)
    assert runtime.get_live_state()["presentation_match"] is not None

    for _ in range(PRESENTATION_MATCH_HOLD_TICKS - 1):
        runtime.tick(world, seed_base=1, cycle=cycle)
        cycle += 1
    assert runtime.get_live_state()["presentation_match"] is not None

    runtime.tick(world, seed_base=1, cycle=cycle)
    assert runtime.get_live_state()["presentation_match"] is None


def test_a_new_active_fixture_supersedes_the_retained_presentation(base_config):
    base_config.duration_frames = 5
    base_config.match_every_frames = 1  # Next tick starts the next fixture.
    runtime = SoccerLeagueRuntime(base_config)
    world = DummyWorld([DummyFish(i, 100.0) for i in range(11)])

    cycle = _run_to_full_time(runtime, world, start_cycle=1)
    assert runtime.get_live_state()["presentation_match"] is not None

    # match_every_frames=1 means the very next tick kicks off the next fixture.
    runtime.tick(world, seed_base=1, cycle=cycle)

    state = runtime.get_live_state()
    assert state["active_match"] is not None
    assert state["presentation_match"] is None


def test_snapshot_is_immune_to_later_mutation_of_the_match(presentation_config):
    runtime = SoccerLeagueRuntime(presentation_config)
    world = DummyWorld([DummyFish(i, 100.0) for i in range(11)])

    _run_to_full_time(runtime, world, start_cycle=100_000)
    snapshot = runtime.get_live_state()["presentation_match"]
    original_entity_x = snapshot["entities"][0]["x"]
    original_event_count = len(snapshot["events"])

    # Mutating the retained payload in place must not be visible through a
    # nested alias, and there is no live match left to write back into it.
    detached = copy.deepcopy(snapshot)
    detached["entities"][0]["x"] = 999.0
    detached["events"].append({"kind": "goal", "frame": 0, "seq": 99})

    refetched = runtime.get_live_state()["presentation_match"]
    assert refetched["entities"][0]["x"] == original_entity_x
    assert len(refetched["events"]) == original_event_count


def test_retaining_a_snapshot_does_not_delay_the_next_fixture(base_config):
    """Scheduling is untouched: the round advances at finalization as before."""
    base_config.duration_frames = 5
    base_config.match_every_frames = 100_000
    runtime = SoccerLeagueRuntime(base_config)
    world = DummyWorld([DummyFish(i, 100.0) for i in range(22)])

    _run_to_full_time(runtime, world, start_cycle=100_000)

    assert runtime.get_live_state()["presentation_match"] is not None
    # One completed result recorded, and the scheduler has moved on.
    assert len(runtime._recent_results) == 1
    assert runtime._recent_results[0].played is True


def test_build_presentation_snapshot_is_a_pure_detached_copy():
    source = {
        "match_id": "m-1",
        "frame": 40,
        "game_over": False,
        "play_mode": "play_on",
        "half": 1,
        "score": {"left": 1, "right": 2},
        "events": [{"frame": 4, "seq": 0, "kind": "kickoff", "event_id": "m-1-kickoff-4-0"}],
        "entities": [{"id": 1, "type": "ball", "x": 3.0, "y": 0.0}],
    }
    snapshot = build_presentation_snapshot(
        source, league_round=2, home_id="A", away_id="B", home_name="A FC", away_name="B FC"
    )

    assert snapshot["game_over"] is True
    assert snapshot["play_mode"] == "time_over"
    assert snapshot["league_round"] == 2
    assert snapshot["home_name"] == "A FC"
    assert snapshot["score"] == {"left": 1, "right": 2}
    # half is reported as the match saw it, never forced to 2.
    assert snapshot["half"] == 1

    # Source is untouched, and mutating it afterwards cannot reach the snapshot.
    assert source["game_over"] is False
    assert source["play_mode"] == "play_on"
    source["entities"][0]["x"] = 999.0
    source["events"].clear()
    assert snapshot["entities"][0]["x"] == 3.0
    assert snapshot["events"][0]["kind"] == "kickoff"


def test_build_presentation_snapshot_synthesizes_full_time_only_when_missing():
    without = build_presentation_snapshot({"match_id": "m-1", "frame": 10, "events": []})
    kinds = [event["kind"] for event in without["events"]]
    assert kinds == ["full_time"]
    assert without["events"][0]["event_id"] == "m-1-full_time-10-0"

    already = build_presentation_snapshot(
        {
            "match_id": "m-1",
            "frame": 10,
            "events": [
                {"frame": 10, "seq": 3, "kind": "full_time", "event_id": "m-1-full_time-10-3"}
            ],
        }
    )
    assert [event["kind"] for event in already["events"]] == ["full_time"]
    assert already["events"][0]["seq"] == 3


class _FakePlayer:
    def __init__(self, player_id: str, distance: float) -> None:
        self.player_id = player_id
        self._distance = distance

    def distance_to(self, _position) -> float:
        return self._distance


class _FakeEngine:
    """Minimal stand-in exposing the kickable geometry compute_ball_owner reads."""

    def __init__(self, players, *, kickable_margin=0.7, player_size=0.3) -> None:
        self._players = players
        self.params = SimpleNamespace(kickable_margin=kickable_margin, player_size=player_size)

    def get_ball(self):
        return SimpleNamespace(position=SimpleNamespace(x=0.0, y=0.0))

    def iter_players(self):
        return list(self._players)


def test_ball_owner_is_the_single_player_within_kickable_distance():
    engine = _FakeEngine([_FakePlayer("left_1", 0.5), _FakePlayer("right_1", 4.0)])
    assert compute_ball_owner(engine) == "left_1"


def test_ball_owner_is_none_when_the_ball_is_loose():
    engine = _FakeEngine([_FakePlayer("left_1", 1.5), _FakePlayer("right_1", 2.0)])
    assert compute_ball_owner(engine) is None
    # Exactly on the boundary still counts as control, matching _apply_kick.
    assert compute_ball_owner(_FakeEngine([_FakePlayer("left_1", 1.0)])) == "left_1"


def test_ball_owner_resolves_contention_deterministically():
    # Nearest wins regardless of iteration order.
    assert (
        compute_ball_owner(_FakeEngine([_FakePlayer("left_1", 0.8), _FakePlayer("right_1", 0.3)]))
        == "right_1"
    )
    assert (
        compute_ball_owner(_FakeEngine([_FakePlayer("right_1", 0.3), _FakePlayer("left_1", 0.8)]))
        == "right_1"
    )
    # An exact tie falls back to the stable participant id, order-independently.
    tie = [_FakePlayer("right_2", 0.4), _FakePlayer("left_3", 0.4)]
    assert compute_ball_owner(_FakeEngine(tie)) == "left_3"
    assert compute_ball_owner(_FakeEngine(list(reversed(tie)))) == "left_3"


def test_leaderboard_carries_the_authoritative_origin_world(base_config):
    runtime = SoccerLeagueRuntime(base_config)
    world = DummyWorld([DummyFish(i, 100.0) for i in range(22)])

    runtime.tick(world, seed_base=1, cycle=1)
    state = runtime.get_live_state()

    by_id = {entry["team_id"]: entry for entry in state["leaderboard"]}
    assert by_id["Tank1:A"]["world_id"] == "Tank1"
    assert by_id["Tank1:B"]["world_id"] == "Tank1"
    # Bot teams belong to no world and must never be attributed to one.
    assert by_id["Bot:Balanced"]["world_id"] is None

    assert state["team_world_ids"] == {"Tank1:A": "Tank1", "Tank1:B": "Tank1"}
