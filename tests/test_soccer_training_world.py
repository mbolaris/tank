"""Tests for the in-process soccer training world."""

from __future__ import annotations

import math

from core.code_pool import CodePool
from core.worlds.soccer_training.world import SoccerTrainingWorldBackendAdapter


def test_soccer_training_initializes_with_22_agents() -> None:
    world = SoccerTrainingWorldBackendAdapter(seed=42)
    result = world.reset(seed=42)

    assert len(result.snapshot["players"]) == 22


def test_soccer_training_steps_without_nans() -> None:
    world = SoccerTrainingWorldBackendAdapter(seed=7)
    world.reset(seed=7)

    for _ in range(500):
        world.step()

    snapshot = world.get_current_snapshot()
    assert math.isfinite(snapshot["ball"]["x"])
    assert math.isfinite(snapshot["ball"]["y"])
    for player in snapshot["players"]:
        assert math.isfinite(player["x"])
        assert math.isfinite(player["y"])
        assert math.isfinite(player["vx"])
        assert math.isfinite(player["vy"])
        assert math.isfinite(player["energy"])


def test_soccer_training_deterministic_with_seed() -> None:
    world_a = SoccerTrainingWorldBackendAdapter(seed=11)
    world_b = SoccerTrainingWorldBackendAdapter(seed=11)

    world_a.reset(seed=11)
    world_b.reset(seed=11)

    for _ in range(50):
        world_a.step()
        world_b.step()

    snap_a = world_a.get_current_snapshot()
    snap_b = world_b.get_current_snapshot()

    assert snap_a["ball"]["x"] == snap_b["ball"]["x"]
    assert snap_a["ball"]["y"] == snap_b["ball"]["y"]

    players_a = sorted(snap_a["players"], key=lambda p: p["id"])
    players_b = sorted(snap_b["players"], key=lambda p: p["id"])
    for pa, pb in zip(players_a, players_b):
        assert pa["x"] == pb["x"]
        assert pa["y"] == pb["y"]


def test_soccer_training_code_pool_policy_controls_players() -> None:
    pool = CodePool()
    component_id = pool.add_component(
        kind="soccer_policy",
        name="dash_forward",
        source=(
            "def policy(obs, rng):\n"
            "    return {\n"
            "        'turn': 0.0,\n"
            "        'dash': 1.0,\n"
            "        'kick_power': 0.0,\n"
            "        'kick_angle': 0.0,\n"
            "    }\n"
        ),
    )
    world = SoccerTrainingWorldBackendAdapter(seed=5, code_pool=pool)
    world.reset(seed=5)
    world.assign_team_policy("left", component_id)

    before = world.get_current_snapshot()
    left_before = next(p for p in before["players"] if p["id"] == "left_1")

    world.step()

    after = world.get_current_snapshot()
    left_after = next(p for p in after["players"] if p["id"] == "left_1")

    assert left_after["x"] > left_before["x"]
