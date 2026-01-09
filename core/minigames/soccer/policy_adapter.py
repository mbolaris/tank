import logging
import math
from typing import Any, Dict, Optional

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS, RCSSParams

logger = logging.getLogger(__name__)

# Constants for validation/clamping
MAX_DASH_POWER = 100.0
MAX_KICK_POWER = 100.0


def build_observation(
    engine: RCSSLiteEngine, player_id: str, config: RCSSParams = DEFAULT_RCSS_PARAMS
) -> Dict[str, Any]:
    """Build a standardized observation dictionary for a player.

    Args:
        engine: The running RCSS-Lite engine instance.
        player_id: The ID of the observing player.
        config: Physics profile for validation/constants.

    Returns:
        Dict containing self state, relative ball state, and relative goal state.
        All coordinates are field-space (meters). Angles in radians (usually).
    """
    player = engine.get_player(player_id)
    ball = engine.get_ball()

    if not player or not ball:
        return {}

    # 1. Self State
    obs = {
        "self_x": player.position.x,
        "self_y": player.position.y,
        "self_vel_x": player.velocity.x,
        "self_vel_y": player.velocity.y,
        "self_angle": player.body_angle,  # Radians [-pi, pi]
        "stamina": player.stamina,
        "team": player.team,
    }

    # 2. Ball Relative State
    dx = ball.position.x - player.position.x
    dy = ball.position.y - player.position.y
    dist_sq = dx * dx + dy * dy
    dist = math.sqrt(dist_sq)

    # Relative angle to ball from player's facing direction
    # angle_to_ball is global angle of vector (dx, dy)
    angle_to_ball = math.atan2(dy, dx)
    rel_angle_ball = _normalize_angle(angle_to_ball - player.body_angle)

    kickable_dist = config.player_size + config.ball_size + config.kickable_margin
    is_kickable = dist <= kickable_dist

    obs.update(
        {
            "ball_x": ball.position.x,
            "ball_y": ball.position.y,
            "ball_rel_x": dx,
            "ball_rel_y": dy,
            "ball_dist": dist,
            "ball_angle": rel_angle_ball,  # Radians relative to body
            "ball_vel_x": ball.velocity.x,
            "ball_vel_y": ball.velocity.y,
            "is_kickable": float(is_kickable),  # Float is safer for ML inputs
        }
    )

    # 3. Goal Relative State (Opponent's goal)
    # Left team attacks Right Goal (+length/2, 0)
    # Right team attacks Left Goal (-length/2, 0)
    goal_x = config.field_length / 2.0 if player.team == "left" else -config.field_length / 2.0
    goal_y = 0.0

    gdx = goal_x - player.position.x
    gdy = goal_y - player.position.y
    gdist = math.sqrt(gdx * gdx + gdy * gdy)
    angle_to_goal = math.atan2(gdy, gdx)
    rel_angle_goal = _normalize_angle(angle_to_goal - player.body_angle)

    obs.update(
        {
            "goal_rel_x": gdx,
            "goal_rel_y": gdy,
            "goal_dist": gdist,
            "goal_angle": rel_angle_goal,
        }
    )

    return obs


def run_policy(
    code_source: Any,  # GenomeCodePool or similar
    genome: Any,
    observation: Dict[str, Any],
    rng: Any = None,
) -> Dict[str, Any]:
    """Execute a genome's soccer policy.

    Returns:
        Action dict, e.g. {"kick": [100, 30]} or {"dash": [50]}
    """
    if not genome or not code_source:
        return default_policy_action(observation)

    # Resolve policy ID
    # Usually: genome.behavioral.soccer_policy_id.value
    policy_id = None
    try:
        if hasattr(genome, "behavioral") and hasattr(genome.behavioral, "soccer_policy_id"):
            policy_id = genome.behavioral.soccer_policy_id.value
    except Exception:
        pass

    if not policy_id:
        return default_policy_action(observation)

    # Execute
    try:
        # Assuming code_pool.execute(policy_id, inputs={"obs": obs}, ...) pattern
        # Or code_pool.get_callable(policy_id)(obs)
        # Based on user context, we might need to adapt to the specific CodePool API.
        # For now, let's assume get_callable or similar exists, or we use the `params` style.
        # Checking `match.py`: uses `self._code_pool.add_component`...
        # We need to know how to EXECUTE.
        # Let's try to get a callable.

        # If code_source is GenomeCodePool
        if hasattr(code_source, "get_callable"):
            policy_func = code_source.get_callable(policy_id)
            if policy_func:
                return policy_func(observation)

        # Fallback if specific execution API differs (will refine during integration)
        return default_policy_action(observation)

    except Exception as e:
        logger.warning(f"Policy {policy_id} execution failed: {e}")
        return default_policy_action(observation)


def default_policy_action(obs: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback chase-ball logic."""
    if not obs:
        return {}

    # Existing logic port
    # if kickable -> kick to goal
    if obs["is_kickable"] > 0.5:
        # Kick towards goal
        # obs["goal_angle"] is normalized relative angle to goal (radians)
        # convert to degrees for RCSS command
        kick_angle_deg = math.degrees(obs["goal_angle"])
        return {"kick": [80, kick_angle_deg]}

    # if facing ball -> dash
    # if not facing ball -> turn
    ball_angle = obs["ball_angle"]  # radians
    if abs(ball_angle) > 0.2:
        turn_deg = math.degrees(ball_angle) * 0.5
        # Clamp turn (though adapter will clamp too)
        return {"turn": [turn_deg]}
    else:
        # Dash
        dist = obs["ball_dist"]
        power = min(100, dist * 5)
        return {"dash": [power]}


def action_to_command(
    action: Dict[str, Any], config: RCSSParams = DEFAULT_RCSS_PARAMS
) -> Optional[RCSSCommand]:
    """Translate abstract action dict to RCSSCommand with strict clamping."""
    if not action:
        return None

    # Priority: Kick > Turn > Dash (Matches typical precedence or exclusive choice)

    if "kick" in action:
        # params: power, rel_dir
        args = action["kick"]
        if len(args) >= 2:
            power = _clamp(args[0], 0, MAX_KICK_POWER)
            angle = _clamp(args[1], -180, 180)  # Assume degrees input
            return RCSSCommand.kick(power, angle)

    if "turn" in action:
        args = action["turn"]
        if len(args) >= 1:
            moment = _clamp(args[0], config.min_moment, config.max_moment)
            return RCSSCommand.turn(moment)

    if "dash" in action:
        args = action["dash"]
        if len(args) >= 1:
            power = _clamp(args[0], -MAX_DASH_POWER, MAX_DASH_POWER)  # allow backward dash?
            # Standard RCSS dash is usually just power.
            return RCSSCommand.dash(power)

    return None


def _normalize_angle(angle: float) -> float:
    """Normalize angle to [-pi, pi]."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def _clamp(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))
