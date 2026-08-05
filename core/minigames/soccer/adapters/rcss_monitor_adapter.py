"""RCSS monitor protocol -> canonical soccer state adapter.

This adapter is intentionally one-way and contains no render concepts
(ADR-017 rule 1). It converts *to* canonical space and stops there.

RCSS monitor `(show ...)` frames use the soccerserver field convention:
metres, field-centred, `+x` toward the right team's goal, **`+y` south**, and
body/neck angles in **degrees measured clockwise** from `+x`. That is the same
handedness as this project's legacy render space, so the conversion reuses the
pure coordinate utilities rather than open-coding a second sign flip - which is
exactly the multiplication of flip sites ADR-017 exists to prevent.

Scope note: this parses the monitor *view* of a match. It is not a client, it
sends nothing, and it does not implement the player-facing `(see ...)` /
`(sense_body ...)` messages `fake_server` speaks to policies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from core.minigames.soccer.coords import (
    LegacyPoint,
    legacy_angle_to_canonical,
    legacy_to_canonical,
)

# RCSS reports stamina on an 8000-point scale; the wire carries 0..1
# (SOCCER_ARENA_DESIGN.md §10.4 rule 8).
DEFAULT_STAMINA_MAX = 8000.0

_SIDE_NAMES = {"l": "left", "r": "right"}


class RcssMonitorParseError(ValueError):
    """Raised when a monitor frame cannot be read as a `(show ...)` message."""


# Recursive by nature: a monitor frame is a tree of bare atoms. Spelling that
# out keeps the parser honestly typed instead of degrading to `Any`.
SExpr: TypeAlias = "str | list[SExpr]"


def parse_sexpr(text: str) -> SExpr:
    """Parse one s-expression into nested lists of bare string atoms.

    Deliberately dumb: it does not interpret numbers, because which atoms are
    numeric depends on position, and a parser that guessed would silently turn
    a player-type id into a float.
    """
    tokens = text.replace("(", " ( ").replace(")", " ) ").split()
    if not tokens:
        raise RcssMonitorParseError("empty monitor frame")

    position = 0

    def parse_at(index: int) -> tuple[SExpr, int]:
        if tokens[index] != "(":
            return tokens[index], index + 1
        items: list[SExpr] = []
        index += 1
        while index < len(tokens) and tokens[index] != ")":
            item, index = parse_at(index)
            items.append(item)
        if index >= len(tokens):
            raise RcssMonitorParseError("unbalanced parentheses in monitor frame")
        return items, index + 1

    parsed, position = parse_at(position)
    return parsed


def _as_float(token: SExpr) -> float | None:
    if not isinstance(token, str):
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _leading_numbers(items: list[SExpr]) -> list[float]:
    """Numeric atoms up to the first nested list.

    The monitor format appends optional fields (`pointto`) before the tagged
    sub-lists, so the numeric run's *length* is what distinguishes them - it
    cannot be read off a fixed index.
    """
    numbers: list[float] = []
    for item in items:
        if isinstance(item, list):
            break
        value = _as_float(item)
        if value is None:
            # A non-numeric atom such as the hex state flag ends nothing; it is
            # a placeholder in the run and is preserved as NaN-free zero.
            numbers.append(_parse_state_atom(item))
            continue
        numbers.append(value)
    return numbers


def _parse_state_atom(token: str) -> float:
    try:
        return float(int(token, 16)) if token.lower().startswith("0x") else float(token)
    except ValueError:
        return 0.0


def _tagged(items: list[SExpr], tag: str) -> list[SExpr] | None:
    for item in items:
        if isinstance(item, list) and item and item[0] == tag:
            return item
    return None


@dataclass
class RcssPlayer:
    side: str
    uniform_number: int
    x: float
    y: float
    vel_x: float
    vel_y: float
    body_angle: float
    stamina: float | None = None

    @property
    def participant_id(self) -> str:
        return f"{self.side}_{self.uniform_number}"


@dataclass
class RcssShowFrame:
    cycle: int
    ball: dict[str, float]
    players: list[RcssPlayer] = field(default_factory=list)
    play_mode: str | None = None
    left_name: str | None = None
    right_name: str | None = None
    left_score: int = 0
    right_score: int = 0


def _parse_player(entry: list[SExpr]) -> RcssPlayer | None:
    identity = entry[0]
    if not isinstance(identity, list) or len(identity) < 2:
        return None
    side_token, number_token = identity[0], identity[1]
    # Both halves of the identity must be atoms. A nested list here is a
    # malformed frame, and coercing it with str() would invent a player.
    if not isinstance(side_token, str) or not isinstance(number_token, str):
        return None
    side = _SIDE_NAMES.get(side_token)
    if side is None:
        return None
    try:
        uniform_number = int(number_token)
    except ValueError:
        return None

    numbers = _leading_numbers(entry[1:])
    # type, state, x, y, vx, vy, body, neck
    if len(numbers) < 8:
        return None
    stamina_list = _tagged(entry[1:], "s")
    stamina_raw = _as_float(stamina_list[1]) if stamina_list and len(stamina_list) > 1 else None

    return RcssPlayer(
        side=side,
        uniform_number=uniform_number,
        x=numbers[2],
        y=numbers[3],
        vel_x=numbers[4],
        vel_y=numbers[5],
        body_angle=numbers[6],
        stamina=stamina_raw,
    )


def parse_show_frame(text: str) -> RcssShowFrame:
    """Parse an RCSS monitor `(show ...)` message into raw RCSS-space values."""
    parsed = parse_sexpr(text)
    if not isinstance(parsed, list) or not parsed or parsed[0] != "show":
        raise RcssMonitorParseError("monitor frame is not a (show ...) message")

    cycle_value = _as_float(parsed[1]) if len(parsed) > 1 else None
    frame = RcssShowFrame(
        cycle=int(cycle_value or 0), ball={"x": 0.0, "y": 0.0, "vel_x": 0.0, "vel_y": 0.0}
    )

    for item in parsed[2:]:
        if not isinstance(item, list) or not item:
            continue
        head = item[0]

        if head == "pm":
            # A numeric play-mode index is *not* a mode name. Emitting it as one
            # would need the rcssserver PlayMode enum ordering, which this
            # project has no way to verify; §10.4 rule 5's honest-unknown path
            # is strictly better than a confidently wrong label.
            frame.play_mode = f"pm:{item[1]}" if len(item) > 1 else None
            continue

        if head == "playmode":
            # The string form is passed through verbatim, per §10.4 rule 5.
            frame.play_mode = str(item[-1]) if len(item) > 1 else None
            continue

        if head == "tm" and len(item) >= 5:
            frame.left_name = str(item[1])
            frame.right_name = str(item[2])
            frame.left_score = int(_as_float(item[3]) or 0)
            frame.right_score = int(_as_float(item[4]) or 0)
            continue

        if isinstance(head, list) and head and head[0] == "b":
            numbers = _leading_numbers(item[1:])
            if len(numbers) >= 2:
                frame.ball = {
                    "x": numbers[0],
                    "y": numbers[1],
                    "vel_x": numbers[2] if len(numbers) > 2 else 0.0,
                    "vel_y": numbers[3] if len(numbers) > 3 else 0.0,
                }
            continue

        if isinstance(head, list):
            player = _parse_player(item)
            if player is not None:
                frame.players.append(player)

    return frame


def _canonical_player(player: RcssPlayer, stamina_max: float) -> dict[str, Any]:
    position = legacy_to_canonical(LegacyPoint(player.x, player.y))
    velocity = legacy_to_canonical(LegacyPoint(player.vel_x, player.vel_y))
    stamina: float | None = None
    if player.stamina is not None and stamina_max > 0:
        stamina = max(0.0, min(1.0, player.stamina / stamina_max))
    return {
        "participant_id": player.participant_id,
        "side": player.side,
        "uniform_number": player.uniform_number,
        "position": {"x": position.x, "y": position.y},
        "velocity": {"x": velocity.x, "y": velocity.y},
        # Monitor angles are degrees; canonical angles are radians CCW.
        "facing_angle": legacy_angle_to_canonical(math.radians(player.body_angle)),
        "stamina": stamina,
    }


def rcss_show_to_canonical(text: str, stamina_max: float = DEFAULT_STAMINA_MAX) -> dict[str, Any]:
    """One-way boundary: a monitor `(show ...)` frame to canonical state."""
    frame = parse_show_frame(text)
    ball_position = legacy_to_canonical(LegacyPoint(frame.ball["x"], frame.ball["y"]))
    ball_velocity = legacy_to_canonical(LegacyPoint(frame.ball["vel_x"], frame.ball["vel_y"]))
    return {
        "cycle": frame.cycle,
        "coord_space": "canonical",
        "play_mode": frame.play_mode,
        "score": {"left": frame.left_score, "right": frame.right_score},
        "left_name": frame.left_name,
        "right_name": frame.right_name,
        "ball": {
            "position": {"x": ball_position.x, "y": ball_position.y},
            "velocity": {"x": ball_velocity.x, "y": ball_velocity.y},
        },
        "players": [_canonical_player(player, stamina_max) for player in frame.players],
    }


def rcss_participants(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Participant records for a canonical RCSS state.

    `avatar_kind` is `external`: these players are not tank fish and have no
    genome to draw, so the renderer must use its neutral branch rather than
    inventing an avatar for them.
    """
    participants: list[dict[str, Any]] = []
    for player in state.get("players", []):
        participants.append(
            {
                "participant_id": player["participant_id"],
                "side": player["side"],
                "team_id": player["side"],
                "uniform_number": player["uniform_number"],
                "avatar_kind": "external",
            }
        )
    return participants


class RcssMonitorAdapter:
    """Explicit one-way monitor-to-canonical adapter boundary."""

    def __init__(self, stamina_max: float = DEFAULT_STAMINA_MAX) -> None:
        self._stamina_max = stamina_max

    def adapt_state(self, text: str) -> dict[str, Any]:
        return rcss_show_to_canonical(text, self._stamina_max)

    def adapt_participants(self, text: str) -> list[dict[str, Any]]:
        return rcss_participants(self.adapt_state(text))
