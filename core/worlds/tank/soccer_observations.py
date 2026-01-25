"""Soccer-specific observation extensions for Tank world.

Adds ball and goal information to standard tank observations,
enabling agents to perceive and interact with soccer gameplay elements.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.ball import Ball
    from core.entities.goal_zone import GoalZone


def add_ball_observations(
    observation: dict[str, Any],
    fish: Fish,
    ball: Ball | None,
) -> None:
    """Add ball information to a fish's observation.

    Args:
        observation: The observation dict to update
        fish: The fish being observed
        ball: The ball entity (or None if no ball)
    """
    if ball is None:
        # No ball available
        observation["ball_position"] = None
        observation["ball_velocity"] = None
        observation["ball_distance"] = None
        observation["ball_angle"] = None
        observation["can_kick"] = False
        return

    # Ball position (absolute)
    observation["ball_position"] = (ball.pos.x, ball.pos.y)

    # Ball velocity
    observation["ball_velocity"] = (ball.vel.x, ball.vel.y)

    # Distance to ball
    dx = ball.pos.x - fish.pos.x
    dy = ball.pos.y - fish.pos.y
    distance = math.sqrt(dx * dx + dy * dy)
    observation["ball_distance"] = distance

    # Angle to ball (relative to world)
    if distance > 0:
        observation["ball_angle"] = math.atan2(dy, dx)
    else:
        observation["ball_angle"] = 0.0

    # Can this fish kick the ball?
    observation["can_kick"] = ball.is_kickable_by(fish, fish.pos)


def add_goal_observations(
    observation: dict[str, Any],
    fish: Fish,
    goal_zones: list[GoalZone] | None,
) -> None:
    """Add goal information to a fish's observation.

    Args:
        observation: The observation dict to update
        fish: The fish being observed
        goal_zones: List of goal zones (or None if none available)
    """
    if not goal_zones:
        observation["goals"] = []
        return

    goals_obs = []

    for goal in goal_zones:
        dx = goal.pos.x - fish.pos.x
        dy = goal.pos.y - fish.pos.y
        distance = math.sqrt(dx * dx + dy * dy)

        goals_obs.append(
            {
                "goal_id": goal.goal_id,
                "team": goal.team,  # Which team scores in this goal
                "position": (goal.pos.x, goal.pos.y),
                "radius": goal.radius,
                "distance": distance,
                "angle": math.atan2(dy, dx) if distance > 0 else 0.0,
                "dx": dx,
                "dy": dy,
                "is_own_goal": goal.team == fish.team,  # True if we defend this goal
            }
        )

    observation["goals"] = goals_obs


def add_team_info(
    observation: dict[str, Any],
    fish: Fish,
) -> None:
    """Add team information to a fish's observation.

    Args:
        observation: The observation dict to update
        fish: The fish being observed
    """
    observation["team"] = fish.team
    observation["is_on_team"] = fish.team is not None


def add_soccer_extras(
    observation: dict[str, Any],
    fish: Fish,
    ball: Ball | None,
    goal_zones: list[GoalZone] | None,
) -> None:
    """Add all soccer-specific extras to observation.

    Args:
        observation: The observation dict to update
        fish: The fish being observed
        ball: The ball entity
        goal_zones: List of goal zones
    """
    # Add team affiliation
    add_team_info(observation, fish)

    # Add ball info
    add_ball_observations(observation, fish, ball)

    # Add goal info
    add_goal_observations(observation, fish, goal_zones)

    # Add soccer-specific extras
    if "extra" not in observation:
        observation["extra"] = {}

    soccer_extras = {
        "soccer_enabled": True,
        "team": fish.team,
    }

    if ball:
        soccer_extras["ball_speed"] = ball.vel.length()
        soccer_extras["ball_decay"] = ball.decay_rate

    observation["extra"].update(soccer_extras)


def build_soccer_ball_observation(
    ball: Ball,
    frame_count: int,
) -> dict[str, Any]:
    """Build observation for the ball itself (for monitoring/analytics).

    Args:
        ball: The ball entity
        frame_count: Current frame number

    Returns:
        Observation dict for the ball
    """
    return {
        "entity_id": "ball",
        "entity_type": "ball",
        "position": (ball.pos.x, ball.pos.y),
        "velocity": (ball.vel.x, ball.vel.y),
        "speed": ball.vel.length(),
        "acceleration": (ball.acceleration.x, ball.acceleration.y),
        "decay_rate": ball.decay_rate,
        "max_speed": ball.max_speed,
        "last_kicker": ball.last_kicker,
        "frame": frame_count,
    }


def get_nearby_teammates(
    fish: Fish,
    all_fish: list[Fish],
    radius: float = 200.0,
) -> list[dict[str, Any]]:
    """Get observations of nearby teammates.

    Args:
        fish: The focal fish
        all_fish: All fish in the world
        radius: Perception radius

    Returns:
        List of teammate observations
    """
    teammates = []

    for other in all_fish:
        if other is fish or other.is_dead():
            continue

        # Must be on same team
        if other.team != fish.team or fish.team is None:
            continue

        dx = other.pos.x - fish.pos.x
        dy = other.pos.y - fish.pos.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance <= radius:
            teammates.append(
                {
                    "fish_id": other.fish_id,
                    "position": (other.pos.x, other.pos.y),
                    "velocity": (other.vel.x, other.vel.y),
                    "distance": distance,
                    "angle": math.atan2(dy, dx),
                    "energy": other.energy,
                    "age": other.age or 0,
                }
            )

    return teammates


def get_nearby_opponents(
    fish: Fish,
    all_fish: list[Fish],
    radius: float = 200.0,
) -> list[dict[str, Any]]:
    """Get observations of nearby opponents.

    Args:
        fish: The focal fish
        all_fish: All fish in the world
        radius: Perception radius

    Returns:
        List of opponent observations
    """
    opponents = []

    for other in all_fish:
        if other is fish or other.is_dead():
            continue

        # Must be on different team
        if other.team == fish.team or fish.team is None:
            continue

        dx = other.pos.x - fish.pos.x
        dy = other.pos.y - fish.pos.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance <= radius:
            opponents.append(
                {
                    "fish_id": other.fish_id,
                    "position": (other.pos.x, other.pos.y),
                    "velocity": (other.vel.x, other.vel.y),
                    "distance": distance,
                    "angle": math.atan2(dy, dx),
                    "energy": other.energy,
                    "team": other.team,
                }
            )

    return opponents
