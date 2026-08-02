"""Tank/RCSS-lite engine -> canonical soccer state adapter.

This adapter is intentionally one-way. It contains no render concepts.
"""

from __future__ import annotations

from typing import Any


def _vector(value: Any) -> dict[str, float]:
    return {"x": float(value.x), "y": float(value.y)}


def adapt_engine_player(player: Any) -> dict[str, Any]:
    raw_stamina = float(getattr(player, "stamina", 0.0))
    stamina_max = float(getattr(player, "stamina_max", 8000.0))
    stamina = 0.0 if stamina_max <= 0 else max(0.0, min(1.0, raw_stamina / stamina_max))
    return {
        "participant_id": str(player.player_id),
        "position": _vector(player.position),
        "velocity": _vector(player.velocity),
        "facing_angle": float(player.body_angle),
        "stamina": stamina,
        "has_ball": False,
    }


def adapt_engine_ball(ball: Any) -> dict[str, Any]:
    return {"position": _vector(ball.position), "velocity": _vector(ball.velocity)}


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
