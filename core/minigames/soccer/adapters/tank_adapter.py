"""Tank/RCSS-lite engine -> canonical soccer state adapter.

This adapter is intentionally one-way. It contains no render concepts.
"""

from __future__ import annotations

from typing import Any

from core.minigames.soccer.coords import (
    LegacyPoint,
    legacy_angle_to_canonical,
    legacy_to_canonical,
)


def adapt_engine_player(player: Any) -> dict[str, Any]:
    position = legacy_to_canonical(LegacyPoint(float(player.position.x), float(player.position.y)))
    velocity = legacy_to_canonical(LegacyPoint(float(player.velocity.x), float(player.velocity.y)))
    raw_stamina = float(getattr(player, "stamina", 0.0))
    stamina_max = float(getattr(player, "stamina_max", 8000.0))
    stamina = 0.0 if stamina_max <= 0 else max(0.0, min(1.0, raw_stamina / stamina_max))
    return {
        "participant_id": str(player.player_id),
        "position": {"x": position.x, "y": position.y},
        "velocity": {"x": velocity.x, "y": velocity.y},
        "facing_angle": legacy_angle_to_canonical(float(player.body_angle)),
        "stamina": stamina,
        "has_ball": False,
    }


def adapt_engine_ball(ball: Any) -> dict[str, Any]:
    position = legacy_to_canonical(LegacyPoint(float(ball.position.x), float(ball.position.y)))
    velocity = legacy_to_canonical(LegacyPoint(float(ball.velocity.x), float(ball.velocity.y)))
    return {
        "position": {"x": position.x, "y": position.y},
        "velocity": {"x": velocity.x, "y": velocity.y},
    }


def adapt_engine_state(engine: Any) -> dict[str, Any]:
    """Adapt a deterministic engine snapshot without touching engine state."""
    player_map = engine.players() if callable(getattr(engine, "players", None)) else engine.players
    players = [adapt_engine_player(player_map[pid]) for pid in sorted(player_map)]
    return {"players": players, "ball": adapt_engine_ball(engine.get_ball())}


def tank_to_canonical(engine: Any) -> dict[str, Any]:
    """Named one-way boundary used by fixtures and replay tooling."""
    return adapt_engine_state(engine)


class TankMatchAdapter:
    """Explicit one-way engine-to-canonical adapter boundary."""

    def adapt_state(self, engine: Any) -> dict[str, Any]:
        return adapt_engine_state(engine)

    def adapt_player(self, player: Any) -> dict[str, Any]:
        return adapt_engine_player(player)

    def adapt_ball(self, ball: Any) -> dict[str, Any]:
        return adapt_engine_ball(ball)


engine_to_canonical = adapt_engine_state
adapt_tank_state = adapt_engine_state
