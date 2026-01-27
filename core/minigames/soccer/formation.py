"""Shared soccer player formation helpers.

The interactive match (`SoccerMatch`) and the training runner (`SoccerMatchRunner`)
must agree on initial spawn positions/angles for determinism and fairness.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from core.minigames.soccer.params import RCSSParams


@dataclass(frozen=True)
class SpawnSpec:
    player_id: str
    team: Literal["left", "right"]
    x: float
    y: float
    body_angle: float


def build_default_formation(team_size: int, params: RCSSParams) -> list[SpawnSpec]:
    """Build the default symmetric formation for both teams.

    Returns a deterministic list ordered as: left_1, right_1, left_2, right_2, ...
    """
    half_length = params.field_length / 2

    spawns: list[SpawnSpec] = []
    for i in range(team_size):
        y = (i // 4 - team_size // 8) * 12

        # Left team - face right (0 radians)
        left_id = f"left_{i + 1}"
        left_x = -half_length / 2 + (i % 4) * 8 - 10
        spawns.append(
            SpawnSpec(
                player_id=left_id,
                team="left",
                x=left_x,
                y=y,
                body_angle=0.0,
            )
        )

        # Right team - face left (pi radians)
        right_id = f"right_{i + 1}"
        right_x = half_length / 2 - (i % 4) * 8 + 10
        spawns.append(
            SpawnSpec(
                player_id=right_id,
                team="right",
                x=right_x,
                y=y,
                body_angle=math.pi,
            )
        )

    return spawns
