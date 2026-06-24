"""Predictive movement system for fish.

This module provides functions to help fish predict where moving targets
will be and intercept them more effectively.
"""

from core.math_utils import Vector2


def predict_intercept_point(
    fish_pos: Vector2, fish_speed: float, target_pos: Vector2, target_vel: Vector2
) -> tuple[Vector2 | None, float]:
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
    discriminant = (
        position_velocity_coefficient * position_velocity_coefficient
        - 4 * velocity_coefficient * distance_coefficient
    )

    if discriminant < 0:
        # No solution - can't intercept
        # Aim for current target position + some prediction
        prediction_time = 1.0  # 1 second ahead
        predicted_pos = target_pos + target_vel * prediction_time
        return predicted_pos, prediction_time

    # Two solutions - we want the smaller positive one
    sqrt_discriminant = discriminant**0.5

    if abs(velocity_coefficient) < 0.001:  # Near zero, use linear approximation
        time_to_intercept = (
            -distance_coefficient / position_velocity_coefficient
            if abs(position_velocity_coefficient) > 0.001
            else 0.0
        )
    else:
        time_solution_1 = (-position_velocity_coefficient + sqrt_discriminant) / (
            2 * velocity_coefficient
        )
        time_solution_2 = (-position_velocity_coefficient - sqrt_discriminant) / (
            2 * velocity_coefficient
        )

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


def predict_falling_intercept(
    fish_pos: Vector2,
    fish_speed: float,
    target_pos: Vector2,
    target_vel: Vector2,
    acceleration: float = 0.01,
) -> tuple[Vector2, float]:
    """Predict intercept point for accelerating target (like sinking food).

    Unlike predict_intercept_point which assumes constant velocity, this
    accounts for acceleration in the Y direction (sinking).

    Uses kinematic equation: y = y0 + v0*t + 0.5*a*t^2

    Args:
        fish_pos: Current position of fish
        fish_speed: Speed of fish
        target_pos: Current position of target
        target_vel: Current velocity of target
        acceleration: Y-axis acceleration (positive = downward, default 0.01)

    Returns:
        Tuple of (intercept_point, time_to_intercept)
    """
    # Iterative approach: estimate time, then refine
    # Start with simple distance/speed estimate
    distance = (target_pos - fish_pos).length()

    if fish_speed < 0.01:
        # Fish too slow, just return current target position
        return target_pos, 0.0

    # Initial time estimate
    time_estimate = distance / fish_speed

    # Refine 3 times (converges quickly)
    for _ in range(3):
        # Predict where target will be with acceleration
        # x = x0 + vx * t (constant horizontal velocity)
        # y = y0 + vy * t + 0.5 * a * t^2 (accelerating vertical)
        predicted_x = target_pos.x + target_vel.x * time_estimate
        predicted_y = (
            target_pos.y
            + target_vel.y * time_estimate
            + 0.5 * acceleration * time_estimate * time_estimate
        )

        predicted_pos = Vector2(predicted_x, predicted_y)

        # Recalculate time to reach predicted position
        new_distance = (predicted_pos - fish_pos).length()
        time_estimate = new_distance / fish_speed

        # Clamp to reasonable value
        time_estimate = max(0.0, min(time_estimate, 60.0))  # ~2 seconds at 30fps

    # Final prediction
    final_x = target_pos.x + target_vel.x * time_estimate
    final_y = (
        target_pos.y
        + target_vel.y * time_estimate
        + 0.5 * acceleration * time_estimate * time_estimate
    )

    return Vector2(final_x, final_y), time_estimate
