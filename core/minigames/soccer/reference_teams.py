"""Frozen soccer reference teams: the immutable rulers of the soccer ladder.

Self-play soccer scores are relative - one evolving population plays itself, so
"the number went up" says nothing absolute. These reference teams are the fixed
opponents that make soccer skill measurable in absolute, longitudinally
comparable terms (see ``benchmarks/soccer/ladder_5k.py``).

Ladder rungs, weakest to strongest by design intent:

===== ============================ =================================================
Rung  Ruler                        Behavior
===== ============================ =================================================
L0    ``stationary_v1``            Never issues a command; the do-nothing floor.
L1    ``random_walk_v1``           Turns and dashes on RNG draws; ignores the ball.
L2    ``chase_shoot_v1``           All-out ball chasing, shoot/dribble toward goal.
L3    ``formation_v1``             Defender + chaser + striker with role geometry.
===== ============================ =================================================

**These functions are frozen.** They are deliberately self-contained - they do
not call ``core.behavior.primitives.steering``, do not read the evolvable
``soccer_policy_params``, and hard-code every constant - so that improving the
evolvable substrate can never move the ruler it is measured against. Editing
one silently invalidates every historical ladder row. To change a ruler, add a
new ``*_v2`` id and a new rung; never edit an existing one. ``L2`` in
particular is a snapshot of the neutral-default substrate chaser as it stood
when the ladder was frozen, which makes "goal difference vs L2" read directly
as "how much has the substrate improved since the freeze".
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool

# --- Frozen ruler component ids ------------------------------------------------

REFERENCE_STATIONARY_ID = "soccer_ref_stationary_v1"
REFERENCE_RANDOM_WALK_ID = "soccer_ref_random_walk_v1"
REFERENCE_CHASE_SHOOT_ID = "soccer_ref_chase_shoot_v1"
REFERENCE_FORMATION_ID = "soccer_ref_formation_v1"
REFERENCE_FORMATION_STRIKER_ID = "soccer_ref_formation_v1_striker"

# --- Frozen constants ----------------------------------------------------------
# Snapshotted from the neutral (all-zero param) evolvable soccer policy at the
# time the ladder was frozen. They are copies on purpose: the substrate's
# defaults may drift, the ruler may not.

_KICKABLE_DIST = 0.98
_INTERCEPT_LEAD = 5.0
_SHOT_RANGE = 40.0
_DRIBBLE_POWER = 0.65
_STAMINA_FLOOR = 0.35
_HOLD_DEPTH = 0.40
_PRESS_RADIUS = 14.0
_ALIGN_THRESHOLD = 0.25
_COMMIT_DIST = 0.40

_NO_ACTION: dict[str, float] = {"turn": 0.0, "dash": 0.0, "kick_power": 0.0, "kick_angle": 0.0}


def _frozen_normalize_angle(angle: float) -> float:
    """Frozen copy of angle normalization to ``[-pi, pi]``."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def _frozen_turn_then_dash(
    target_x: float,
    target_y: float,
    facing_angle: float,
    stamina_ratio: float,
) -> tuple[float, float]:
    """Frozen copy of turn-then-dash steering in the actor's relative frame."""
    distance = math.sqrt(target_x * target_x + target_y * target_y)
    angle_delta = _frozen_normalize_angle(math.atan2(target_y, target_x) - facing_angle)

    if abs(angle_delta) >= _ALIGN_THRESHOLD:
        return max(-1.0, min(1.0, (angle_delta * 1.5) / math.pi)), 0.0

    if distance > _COMMIT_DIST:
        dash = (
            1.0
            if stamina_ratio > _STAMINA_FLOOR
            else max(0.3, stamina_ratio / max(_STAMINA_FLOOR, 1e-6))
        )
    else:
        dash = 0.0
    return 0.0, dash


def _reference_core(observation: dict[str, Any], role: str) -> dict[str, float]:
    """Frozen scripted soccer play for one role.

    Geometry is derived from ``goal_direction``, which ``build_observation``
    already makes side- and half-swap-aware, so a ruler plays identically on
    either team.
    """
    self_pos = observation.get("position", {})
    sx = float(self_pos.get("x", 0.0))
    sy = float(self_pos.get("y", 0.0))

    ball_rel = observation.get("ball_relative_pos", {})
    brx = float(ball_rel.get("x", 0.0))
    bry = float(ball_rel.get("y", 0.0))
    ball_dist = math.sqrt(brx * brx + bry * bry)

    ball_vx = float(observation.get("ball_vel_x", 0.0))
    ball_vy = float(observation.get("ball_vel_y", 0.0))

    goal_rel = observation.get("goal_direction", {})
    grx = float(goal_rel.get("x", 0.0))
    gry = float(goal_rel.get("y", 0.0))
    goal_dist = math.sqrt(grx * grx + gry * gry)

    facing_angle = float(observation.get("facing_angle", 0.0))
    stamina_ratio = float(observation.get("stamina_ratio", 1.0))
    field_length = float(observation.get("field_length", 100.0))

    # --- On the ball: shoot in range, otherwise dribble goalward ---
    if ball_dist <= _KICKABLE_DIST:
        kick_angle = _frozen_normalize_angle(math.atan2(gry, grx) - facing_angle)
        kick_power = 1.0 if (goal_dist <= _SHOT_RANGE or role == "defender") else _DRIBBLE_POWER
        return {"turn": 0.0, "dash": 0.0, "kick_power": kick_power, "kick_angle": kick_angle}

    # --- Off the ball: lead the ball, then position by role ---
    ix = brx + ball_vx * _INTERCEPT_LEAD
    iy = bry + ball_vy * _INTERCEPT_LEAD

    if role == "striker":
        ball_to_goal_x = grx - brx
        ball_to_goal_y = gry - bry
        ball_goal_dist = math.sqrt(ball_to_goal_x**2 + ball_to_goal_y**2)
        if ball_dist <= _PRESS_RADIUS or ball_goal_dist <= field_length * 0.5:
            tx, ty = ix, iy
        else:
            goal_x, goal_y = sx + grx, sy + gry
            ball_x, ball_y = sx + brx, sy + bry
            tx = (goal_x + (ball_x - goal_x) * _HOLD_DEPTH) - sx
            ty = (goal_y + (ball_y - goal_y) * _HOLD_DEPTH) - sy
    elif role == "defender":
        if ball_dist <= _PRESS_RADIUS:
            tx, ty = ix, iy
        else:
            # Goals are mirrored across the field center: own goal = -(opponent goal).
            goal_x, goal_y = sx + grx, sy + gry
            own_goal_x, own_goal_y = -goal_x, -goal_y
            ball_x, ball_y = sx + brx, sy + bry
            tx = (own_goal_x + (ball_x - own_goal_x) * _HOLD_DEPTH) - sx
            ty = (own_goal_y + (ball_y - own_goal_y) * _HOLD_DEPTH) - sy
    else:
        tx, ty = ix, iy

    turn, dash = _frozen_turn_then_dash(tx, ty, facing_angle, stamina_ratio)
    return {"turn": turn, "dash": dash, "kick_power": 0.0, "kick_angle": 0.0}


# --- Frozen ruler policies -----------------------------------------------------


def stationary_reference_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """L0 ruler: stand still forever. The do-nothing floor."""
    _ = observation, rng
    return dict(_NO_ACTION)


def random_walk_reference_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """L1 ruler: turn and dash on RNG draws, never looking at the ball.

    Draw order is fixed (turn, then dash) and both draws happen on every call,
    so the ruler's RNG consumption is stable regardless of observation content.
    """
    _ = observation
    if rng is None:
        return dict(_NO_ACTION)
    turn = rng.uniform(-1.0, 1.0)
    dash = rng.uniform(0.0, 1.0)
    return {"turn": turn, "dash": dash, "kick_power": 0.0, "kick_angle": 0.0}


def chase_shoot_reference_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """L2 ruler: every player intercepts the ball and works it toward goal."""
    _ = rng
    try:
        return _reference_core(observation, role="chaser")
    except (AttributeError, TypeError, ValueError, KeyError):
        return dict(_NO_ACTION)


def formation_defender_reference_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """L3 ruler slot: hold the line between own goal and the ball."""
    _ = rng
    try:
        return _reference_core(observation, role="defender")
    except (AttributeError, TypeError, ValueError, KeyError):
        return dict(_NO_ACTION)


def formation_striker_reference_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """L3 ruler slot: lurk upfield and press in the offensive zone."""
    _ = rng
    try:
        return _reference_core(observation, role="striker")
    except (AttributeError, TypeError, ValueError, KeyError):
        return dict(_NO_ACTION)


# The L3 formation needs three distinct role behaviors, so its slots bind to
# three ids. Chasing is shared with L2 (identical frozen code), which keeps the
# roles honest: L3 differs from L2 only by the two positional roles.
REFERENCE_FORMATION_SLOT_IDS: tuple[str, ...] = (
    REFERENCE_FORMATION_ID,
    REFERENCE_CHASE_SHOOT_ID,
    REFERENCE_FORMATION_STRIKER_ID,
)


@dataclass(frozen=True)
class ReferenceTeam:
    """One frozen rung of the soccer ladder."""

    rung: str
    """Ladder position label, e.g. ``"L0"``."""

    rung_id: str
    """Stable ruler identifier; never reused for different behavior."""

    slot_policy_ids: tuple[str, ...]
    """Policy id per team slot, cycled if the team is larger than the tuple."""

    description: str
    """One-line description of what this ruler does."""

    def policy_id_for_slot(self, slot: int) -> str:
        """Return the frozen policy id for team slot ``slot`` (0-indexed)."""
        return self.slot_policy_ids[slot % len(self.slot_policy_ids)]


REFERENCE_LADDER: tuple[ReferenceTeam, ...] = (
    ReferenceTeam(
        rung="L0",
        rung_id="stationary_v1",
        slot_policy_ids=(REFERENCE_STATIONARY_ID,),
        description="Never moves; the do-nothing floor.",
    ),
    ReferenceTeam(
        rung="L1",
        rung_id="random_walk_v1",
        slot_policy_ids=(REFERENCE_RANDOM_WALK_ID,),
        description="Turns and dashes at random, ignoring the ball.",
    ),
    ReferenceTeam(
        rung="L2",
        rung_id="chase_shoot_v1",
        slot_policy_ids=(REFERENCE_CHASE_SHOOT_ID,),
        description="All players chase the ball and shoot or dribble goalward.",
    ),
    ReferenceTeam(
        rung="L3",
        rung_id="formation_v1",
        slot_policy_ids=REFERENCE_FORMATION_SLOT_IDS,
        description="Defender, chaser, and striker playing role geometry.",
    ),
)


# Rulers register under their own kind, never "soccer_policy". Policy execution
# looks components up by id and ignores kind, but mutation and crossover draw
# candidates from get_components_by_kind("soccer_policy") - so sharing that kind
# would let an evolving genome mutate *onto* a frozen ruler, both corrupting the
# population and making the ruler part of the thing it measures.
REFERENCE_POLICY_KIND = "soccer_reference_policy"

_REFERENCE_POLICIES: tuple[tuple[str, Any], ...] = (
    (REFERENCE_STATIONARY_ID, stationary_reference_policy),
    (REFERENCE_RANDOM_WALK_ID, random_walk_reference_policy),
    (REFERENCE_CHASE_SHOOT_ID, chase_shoot_reference_policy),
    (REFERENCE_FORMATION_ID, formation_defender_reference_policy),
    (REFERENCE_FORMATION_STRIKER_ID, formation_striker_reference_policy),
)


def register_reference_policies(pool: GenomeCodePool) -> None:
    """Register every frozen ruler policy into ``pool`` under its stable id.

    Registration is idempotent and never touches the pool's registered defaults
    or its evolvable ``soccer_policy`` roster, so a pool carrying the rulers
    behaves identically for every genome that does not explicitly name one.
    """
    for component_id, policy in _REFERENCE_POLICIES:
        pool.register_builtin(component_id, REFERENCE_POLICY_KIND, policy)
