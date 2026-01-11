"""Tests for the Strict Soccer League Runtime."""

from __future__ import annotations

import pytest

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.league.types import TeamSource
from core.minigames.soccer.league_runtime import SoccerLeagueRuntime


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
        self.genome_code_pool = None
        self.world_id = "Tank1"

    def get_fish_list(self) -> list[DummyFish]:
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

    assert state["active_match"] is not None
    match = state["active_match"]
    assert match["frame"] == 1  # Initial frame (stepped once)
    assert "Tank1:A" in [match["home_id"], match["away_id"]]
    assert "Bot:Balanced" in [match["home_id"], match["away_id"]]

    # 2. Step Match until end
    for _ in range(20):  # Duration is 10, should finish
        runtime.tick(world, seed_base=1, cycle=101 + _)

    state = runtime.get_live_state()

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
    lb = state["leaderboard"]

    assert lb[0]["team_id"] == "A"
    assert lb[1]["team_id"] == "B"
    assert lb[2]["team_id"] == "C"


def test_entry_fee_filtering():
    """Test that fish without enough energy are filtered out, preventing crashes."""
    config = SoccerConfig(
        enabled=True,
        match_every_frames=1,
        team_size=11,
        entry_fee_energy=50.0,  # High fee
        cycles_per_frame=1,
    )
    runtime = SoccerLeagueRuntime(config)

    # 20 fish with only 10 energy (cannot pay)
    fish = [DummyFish(i, 10.0) for i in range(20)]
    world = DummyWorld(fish)

    runtime.tick(world, seed_base=1, cycle=1)
    state = runtime.get_live_state()

    # Tank1:A should be unavailable because no fish can pay
    av = state["availability"]
    assert "Tank1:A" in av
    assert av["Tank1:A"]["available"] is False
    assert av["Tank1:A"]["count"] == 0  # All filtered out

    # Start a match and ensure it doesn't crash (should just skip)
    assert state["active_match"] is None
