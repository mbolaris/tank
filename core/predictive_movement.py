"""Predictive movement system for fish.

This module provides functions to help fish predict where moving targets
will be and intercept them more effectively.
"""

import math
from typing import Optional, Tuple

from core.constants import (
    MOVEMENT_DISTANCE_EPSILON,
    MOVEMENT_ESCAPE_DIRECT_WEIGHT,
    MOVEMENT_ESCAPE_PERPENDICULAR_WEIGHT,
    MOVEMENT_FOV_ANGLE,
    MOVEMENT_SLOW_SPEED_MULTIPLIER,
)
from core.math_utils import Vector2


def predict_intercept_point(
    fish_pos: Vector2, fish_speed: float, target_pos: Vector2, target_vel: Vector2
) -> Tuple[Optional[Vector2], float]:
    """Predict where to move to intercept a moving target.

    Uses basic ballistic prediction to calculate where the fish should
    aim to intercept a moving target.

    Args:
        fish_pos: Current position of fish
        fish_speed: Speed of fish
        target_pos: Current position of target
        target_vel: Velocity of target

    Returns:
        Tuple of (intercept_point, time_to_intercept) or (None, 0) if impossible
    """
    # Calculate relative position
    rel_pos = target_pos - fish_pos

    # If target is stationary, just return target position
    target_speed = target_vel.length()
    if target_speed < 0.01:
        distance = rel_pos.length()
        time_to_reach = distance / max(fish_speed, 0.01)
        return target_pos, time_to_reach

    # Check if fish is fast enough to intercept
    # Using quadratic formula to solve interception problem
    # Let t be time to intercept:
    # |target_pos + target_vel*t - fish_pos| = fish_speed * t

    velocity_coefficient = target_vel.length_squared() - fish_speed * fish_speed
    position_velocity_coefficient = 2 * rel_pos.dot(target_vel)
    distance_coefficient = rel_pos.length_squared()

    # Solve quadratic equation
    discriminant = position_velocity_coefficient * position_velocity_coefficient - 4 * velocity_coefficient * distance_coefficient

    if discriminant < 0:
        # No solution - can't intercept
        # Aim for current target position + some prediction
        prediction_time = 1.0  # 1 second ahead
        predicted_pos = target_pos + target_vel * prediction_time
        return predicted_pos, prediction_time

    # Two solutions - we want the smaller positive one
    sqrt_discriminant = discriminant**0.5

    if abs(velocity_coefficient) < 0.001:  # Near zero, use linear approximation
        time_to_intercept = -distance_coefficient / position_velocity_coefficient if abs(position_velocity_coefficient) > 0.001 else 0.0
    else:
        time_solution_1 = (-position_velocity_coefficient + sqrt_discriminant) / (2 * velocity_coefficient)
        time_solution_2 = (-position_velocity_coefficient - sqrt_discriminant) / (2 * velocity_coefficient)

        # Choose smallest positive time
        if time_solution_1 > 0 and time_solution_2 > 0:
            time_to_intercept = min(time_solution_1, time_solution_2)
        elif time_solution_1 > 0:
            time_to_intercept = time_solution_1
        elif time_solution_2 > 0:
            time_to_intercept = time_solution_2
        else:
            # Both negative - aim for current position
            time_to_intercept = 0.0

    # Limit prediction time to reasonable value (2 seconds max)
    time_to_intercept = max(0.0, min(time_to_intercept, 2.0))

    # Calculate intercept point
    intercept_point = target_pos + target_vel * time_to_intercept

    return intercept_point, time_to_intercept


def predict_position(pos: Vector2, vel: Vector2, frames_ahead: float) -> Vector2:
    """Simple prediction of where an object will be.

    Args:
        pos: Current position
        vel: Current velocity
        frames_ahead: How many frames to predict ahead

    Returns:
        Predicted position
    """
    return pos + vel * frames_ahead


def get_avoidance_direction(
    fish_pos: Vector2,
    fish_vel: Vector2,
    threat_pos: Vector2,
    threat_vel: Vector2,
    prediction_time: float = 1.0,
) -> Vector2:
    """Calculate direction to avoid a predicted threat.

    Args:
        fish_pos: Current fish position
        fish_vel: Current fish velocity
        threat_pos: Current threat position
        threat_vel: Threat velocity
        prediction_time: How far ahead to predict (seconds)

    Returns:
        Normalized avoidance direction
    """
    # Predict where threat will be
    predicted_threat_pos = predict_position(threat_pos, threat_vel, prediction_time * 30)

    # Calculate escape direction (perpendicular to threat approach)
    threat_to_fish = fish_pos - predicted_threat_pos

    if threat_to_fish.length() < 0.01:
        # If directly on top of fish, use current velocity to escape
        if fish_vel.length() > 0.01:
            return fish_vel.normalize()
        # Otherwise pick random perpendicular direction
        return Vector2(1, 0)

    # Escape direction is away from predicted threat position
    escape_dir = threat_to_fish.normalize()

    # Add perpendicular component if threat is moving toward fish
    approach_vel = threat_vel - fish_vel  # Relative velocity
    if approach_vel.dot(threat_to_fish) < 0:  # Threat approaching
        # Add perpendicular escape component
        perpendicular = Vector2(-escape_dir.y, escape_dir.x)

        # Blend direct escape with perpendicular movement
        escape_dir = (
            escape_dir * MOVEMENT_ESCAPE_DIRECT_WEIGHT
            + perpendicular * MOVEMENT_ESCAPE_PERPENDICULAR_WEIGHT
        ).normalize()

    return escape_dir


def calculate_pursuit_angle(fish_pos: Vector2, fish_heading: Vector2, target_pos: Vector2) -> float:
    """Calculate angle to turn to pursue target.

    Args:
        fish_pos: Fish position
        fish_heading: Fish current heading (normalized)
        target_pos: Target position

    Returns:
        Angle in radians (-pi to pi)
    """
    to_target = (target_pos - fish_pos).normalize()

    # Calculate angle between heading and target
    dot = fish_heading.dot(to_target)
    det = fish_heading.x * to_target.y - fish_heading.y * to_target.x

    angle = math.atan2(det, dot)

    return angle


def is_target_ahead(
    fish_pos: Vector2,
    fish_heading: Vector2,
    target_pos: Vector2,
    fov_angle: float = MOVEMENT_FOV_ANGLE,  # ~90 degrees in radians
) -> bool:
    """Check if target is in front of fish within field of view.

    Args:
        fish_pos: Fish position
        fish_heading: Fish heading direction (normalized)
        target_pos: Target position
        fov_angle: Field of view angle in radians (default 90 degrees)

    Returns:
        True if target is ahead within FOV
    """
    to_target = (target_pos - fish_pos).normalize()
    dot = fish_heading.dot(to_target)

    # dot = cos(angle), so angle = acos(dot)
    # Check if angle is within FOV
    return dot > math.cos(fov_angle / 2)


def calculate_smooth_approach(
    fish_pos: Vector2, target_pos: Vector2, approach_distance: float, slowdown_distance: float
) -> Tuple[Vector2, float]:
    """Calculate smooth approach to target with slowdown.

    Args:
        fish_pos: Fish position
        target_pos: Target position
        approach_distance: Minimum distance to maintain
        slowdown_distance: Distance at which to start slowing

    Returns:
        Tuple of (direction, speed_multiplier)
    """
    to_target = target_pos - fish_pos
    distance = to_target.length()

    if distance < MOVEMENT_DISTANCE_EPSILON:
        return Vector2(0, 0), 0.0

    direction = to_target.normalize()

    # Calculate speed multiplier based on distance
    if distance < approach_distance:
        # Too close - back away slowly
        direction = -direction
        speed_mult = MOVEMENT_SLOW_SPEED_MULTIPLIER
    elif distance < slowdown_distance:
        # Slow down as approaching
        progress = (distance - approach_distance) / (slowdown_distance - approach_distance)
        speed_mult = MOVEMENT_SLOW_SPEED_MULTIPLIER + progress * (
            1.0 - MOVEMENT_SLOW_SPEED_MULTIPLIER
        )
    else:
        # Far away - full speed
        speed_mult = 1.0

    return direction, speed_mult


def calculate_circling_movement(
    fish_pos: Vector2, target_pos: Vector2, circle_radius: float, clockwise: bool = True
) -> Vector2:
    """Calculate movement to circle around a target.

    Args:
        fish_pos: Fish position
        target_pos: Target to circle
        circle_radius: Desired circling radius
        clockwise: Direction to circle

    Returns:
        Direction vector for circling movement
    """
    to_target = target_pos - fish_pos
    distance = to_target.length()

    if distance < 0.01:
        return Vector2(1, 0)

    # Direction toward/away from target to maintain radius
    radial_dir = to_target.normalize()

    # Tangent direction for circling
    if clockwise:
        tangent_dir = Vector2(radial_dir.y, -radial_dir.x)
    else:
        tangent_dir = Vector2(-radial_dir.y, radial_dir.x)

    # Adjust based on distance from desired radius
    distance_error = distance - circle_radius

    if abs(distance_error) < 10:
        # At correct radius - pure tangent movement
        return tangent_dir
    elif distance < circle_radius:
        # Too close - move away while circling
        return (tangent_dir * 0.7 + radial_dir * 0.3).normalize()
    else:
        # Too far - move in while circling
        return (tangent_dir * 0.7 - radial_dir * 0.3).normalize()
