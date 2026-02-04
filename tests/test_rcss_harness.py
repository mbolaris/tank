"""Tests for FakeRCSSServer command semantics and message stability."""

from __future__ import annotations

import math
from typing import Any

from core.minigames.soccer.fake_server import FakeRCSSServer
from core.minigames.soccer.params import RCSSParams


def _get_player_snapshot(snapshot: dict[str, Any], player_id: str) -> dict[str, Any]:
    for player in snapshot.get("players", []):
        if isinstance(player, dict) and player.get("id") == player_id:
            return player
    raise AssertionError(f"Player '{player_id}' not found in snapshot")


def test_rcss_harness_dash_timing_and_decay() -> None:
    """Dash commands advance cycle timing and decay velocity."""
    params = RCSSParams(player_decay=0.4, dash_power_rate=0.006, noise_enabled=False)
    server = FakeRCSSServer(params=params, seed=42)
    server.add_player("left_1", "left", (0.0, 0.0), body_angle=0.0)

    assert server.cycle == 0
    server.queue_command("left_1", "(dash 100 0)")
    server.step()

    snapshot = server.get_snapshot()
    player = _get_player_snapshot(snapshot, "left_1")

    assert snapshot["cycle"] == 1
    assert math.isclose(player["x"], 0.6, abs_tol=1e-4)
    assert math.isclose(player["vx"], 0.24, abs_tol=1e-4)


def test_rcss_harness_dash_clamps_speed() -> None:
    """Oversized dash power should clamp to max speed."""
    params = RCSSParams(player_speed_max=1.05, player_decay=0.4, noise_enabled=False)
    server = FakeRCSSServer(params=params, seed=7)
    server.add_player("left_1", "left", (0.0, 0.0), body_angle=0.0)

    server.queue_command("left_1", "(dash 1000 0)")
    server.step()

    snapshot = server.get_snapshot()
    player = _get_player_snapshot(snapshot, "left_1")
    speed = math.hypot(player["vx"], player["vy"])

    assert speed <= params.player_speed_max * params.player_decay + 1e-6


def test_rcss_harness_kickable_gating() -> None:
    """Kick commands only move the ball when the player is in range."""
    server = FakeRCSSServer(seed=42)
    server.add_player("left_1", "left", (20.0, 0.0), body_angle=0.0)

    server.queue_command("left_1", "(kick 100 0)")
    server.step()

    snapshot = server.get_snapshot()
    assert snapshot["ball"]["vx"] == 0.0
    assert snapshot["ball"]["vy"] == 0.0

    server.queue_command("left_1", "(move 0 0)")
    server.step()

    server.queue_command("left_1", "(kick 100 0)")
    server.step()

    snapshot = server.get_snapshot()
    assert math.hypot(snapshot["ball"]["vx"], snapshot["ball"]["vy"]) > 0.0


def test_rcss_harness_message_shapes() -> None:
    """See and sense_body messages include stable RCSS tokens."""
    server = FakeRCSSServer(seed=42)
    server.add_player("left_1", "left", (0.0, 0.0), body_angle=0.0)

    see_msg = server.get_see_message("left_1")
    sense_msg = server.get_sense_body_message("left_1")

    assert see_msg.startswith("(see ")
    assert "((b)" in see_msg or "((g" in see_msg
    assert sense_msg.startswith("(sense_body ")
    assert "(stamina" in sense_msg
    assert "(speed" in sense_msg
