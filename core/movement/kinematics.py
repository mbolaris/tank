"""Shared kinematics that turn an arbitrated *desired* velocity into motion.

Movement arbitration (:mod:`core.movement.considerations`) answers "which
drive wins and where does it want to go". This module answers the separate
question of "how does the body actually move", and it is deliberately the
only implementation of that answer: the live simulation
(:meth:`core.movement_strategy.AlgorithmicMovement.move`) and every offline
gym replica of the production controller call the same function, so an
offline arm can never silently drift away from what the tank really does.

The steps - clamp to the kinematic action bound, scale by the fish's speed,
smooth toward the target, nudge out of a dead stop, cap at top speed - are
unchanged from the inline version this replaced. They are float-order
sensitive: the tank's champion scores depend on this arithmetic executing in
exactly this sequence, so reorder it only with a champion re-baseline.
"""

from __future__ import annotations

import math
import random

from core.math_utils import Vector2

# Kinematic action bound for tank-like worlds, mirroring
# TankLikeActionTranslator(max_velocity=5.0). The internal movement path clamps
# inline rather than round-tripping every fish every frame through the
# external-brain action-translation registry, which only re-applied this same
# clamp while allocating an Action object. The translation layer is still the
# correct seam for *external* brains; it is just not needed on the internal
# composable-behavior path. See ADR-007 (silent-fallback removal).
MAX_ACTION_VELOCITY = 5.0

# Movement smoothing constants (lower = smoother, higher = more responsive)
# INCREASED from 0.02 to 0.10 - fish were too sluggish to catch food
# At 2% per frame, it took ~150 frames (5s) to reach target velocity
# At 10% per frame, it takes ~30 frames (1s) - much better for food pursuit
ALGORITHMIC_MOVEMENT_SMOOTHING = 0.10
ALGORITHMIC_MAX_SPEED_MULTIPLIER = 1.0  # Cap at base speed (was 0.6)
ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ = (
    ALGORITHMIC_MAX_SPEED_MULTIPLIER * ALGORITHMIC_MAX_SPEED_MULTIPLIER
)

# The anti-stuck nudge's turn angle. Spelled as this literal rather than
# math.tau because the tank's recorded champion scores were produced with it;
# math.tau differs in the last few digits and would perturb every replay.
_NUDGE_FULL_TURN = 6.283185307
_NUDGE_SPEED_FRACTION = 0.3
_STUCK_SPEED_SQ = 0.01

VelocityComponents = tuple[float, float]

__all__ = [
    "ALGORITHMIC_MAX_SPEED_MULTIPLIER",
    "ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ",
    "ALGORITHMIC_MOVEMENT_SMOOTHING",
    "MAX_ACTION_VELOCITY",
    "VelocityComponents",
    "apply_movement_kinematics",
    "clamp_action_velocity",
]


def clamp_action_velocity(value: float) -> float:
    """Clamp one desired-velocity component to the kinematic action bound."""
    return max(-MAX_ACTION_VELOCITY, min(MAX_ACTION_VELOCITY, value))


def apply_movement_kinematics(
    velocity: Vector2,
    desired: VelocityComponents,
    speed: float,
    rng: random.Random,
) -> Vector2:
    """Advance ``velocity`` one frame toward ``desired``, in place.

    ``desired`` is the winning drive's direction-and-urgency vector, in
    pre-speed units; it is scaled by ``speed`` here, which is why a
    unit-magnitude controller (a normalized behavior graph) and a
    1.5-magnitude one (the composable behavior) both end up travelling at the
    same top speed. ``rng`` is consumed only on the anti-stuck branch, so a
    fish that is moving costs no draws and the replay schedule is unchanged.
    """
    desired_vx = clamp_action_velocity(float(desired[0]))
    desired_vy = clamp_action_velocity(float(desired[1]))

    target_vx = desired_vx * speed
    target_vy = desired_vy * speed

    velocity.x += (target_vx - velocity.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
    velocity.y += (target_vy - velocity.y) * ALGORITHMIC_MOVEMENT_SMOOTHING

    vel_x = velocity.x
    vel_y = velocity.y
    vel_length_sq = vel_x * vel_x + vel_y * vel_y

    if vel_length_sq < _STUCK_SPEED_SQ:
        angle = rng.random() * _NUDGE_FULL_TURN
        nudge_speed = speed * _NUDGE_SPEED_FRACTION
        velocity.x = nudge_speed * math.cos(angle)
        velocity.y = nudge_speed * math.sin(angle)
        # A nudge is a fraction of top speed, so it can never trip the cap
        # below; vel_x / vel_y stay at their pre-nudge values on purpose.
        vel_length_sq = velocity.x * velocity.x + velocity.y * velocity.y

    if vel_length_sq > 0:
        max_speed_sq = speed * speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ
        if vel_length_sq > max_speed_sq:
            max_speed = speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER
            scale = max_speed / math.sqrt(vel_length_sq)
            velocity.x = vel_x * scale
            velocity.y = vel_y * scale

    return velocity
