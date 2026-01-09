"""Policy adapter for soccer minigame.

This module provides the bridge between genome policies and the RCSS-Lite engine.
It handles:
- Building observations for players
- Executing policies (via GenomeCodePool or fallback)
- Converting policy outputs to RCSS commands

IMPORTANT: The primary execution path is GenomeCodePool.execute_policy() which
provides safety checks and determinism guarantees. Direct callable execution
is only used as a fallback for legacy CodePool usage.
"""

import logging
import math
import random as pyrandom
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.minigames.soccer.engine import RCSSCommand, RCSSLiteEngine
from core.minigames.soccer.params import DEFAULT_RCSS_PARAMS, RCSSParams

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool
    from core.genetics import Genome

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
    code_source: Optional["GenomeCodePool"],
    genome: Optional["Genome"],
    observation: Dict[str, Any],
    rng: Optional[pyrandom.Random] = None,
    dt: float = 0.1,
) -> Dict[str, Any]:
    """Execute a genome's soccer policy using GenomeCodePool.execute_policy().

    This is the primary entry point for policy execution in soccer matches.
    It handles:
    1. Extracting policy ID and params from genome traits
    2. Calling GenomeCodePool.execute_policy() with safety guarantees
    3. Converting normalized policy output to RCSS command format
    4. Falling back to default_policy_action() on any error

    Args:
        code_source: GenomeCodePool containing the policy components
        genome: Genome with behavioral.soccer_policy_id trait
        observation: Soccer observation dict from build_observation()
        rng: Seeded RNG for determinism (REQUIRED for proper execution)
        dt: Delta time since last step (default 0.1 = 100ms RCSS cycle)

    Returns:
        Action dict in RCSS format, e.g. {"kick": [100, 30]} or {"dash": [50]}
    """
    if not genome or not code_source:
        return default_policy_action(observation)

    # Create fallback RNG if not provided (logs warning - caller should provide RNG)
    if rng is None:
        logger.warning("run_policy called without RNG - determinism not guaranteed")
        rng = pyrandom.Random()

    # Extract policy ID from genome.behavioral.soccer_policy_id.value
    policy_id = _get_policy_id(genome)
    if not policy_id:
        return default_policy_action(observation)

    # Extract policy params from genome.behavioral.soccer_policy_params.value
    policy_params = _get_policy_params(genome)

    # Execute via GenomeCodePool.execute_policy() - the correct API
    try:
        # Check if code_source has execute_policy (GenomeCodePool)
        if hasattr(code_source, "execute_policy"):
            result = code_source.execute_policy(
                component_id=policy_id,
                observation=observation,
                rng=rng,
                dt=dt,
                params=policy_params,
            )

            if not result.success:
                logger.debug(f"Policy {policy_id} execution failed: {result.error_message}")
                return default_policy_action(observation)

            # Convert normalized output to RCSS command format
            return _normalize_policy_output(result.output)

        # Fallback: legacy CodePool with get_callable (not recommended)
        elif hasattr(code_source, "get_callable"):
            policy_func = code_source.get_callable(policy_id)
            if policy_func:
                raw_output = policy_func(observation, rng)
                return _normalize_policy_output(raw_output)
            else:
                return default_policy_action(observation)

        else:
            logger.warning(f"Unknown code_source type: {type(code_source)}")
            return default_policy_action(observation)

    except Exception as e:
        logger.warning(f"Policy {policy_id} execution error: {e}")
        return default_policy_action(observation)


def _get_policy_id(genome: "Genome") -> Optional[str]:
    """Extract soccer_policy_id from genome behavioral traits."""
    try:
        if hasattr(genome, "behavioral") and hasattr(genome.behavioral, "soccer_policy_id"):
            trait = genome.behavioral.soccer_policy_id
            if trait is not None:
                return trait.value
    except Exception:
        pass
    return None


def _get_policy_params(genome: "Genome") -> Optional[Dict[str, float]]:
    """Extract soccer_policy_params from genome behavioral traits."""
    try:
        if hasattr(genome, "behavioral") and hasattr(genome.behavioral, "soccer_policy_params"):
            trait = genome.behavioral.soccer_policy_params
            if trait is not None and trait.value is not None:
                return dict(trait.value)
    except Exception:
        pass
    return None


def _normalize_policy_output(output: Any) -> Dict[str, Any]:
    """Convert policy output to RCSS command format.

    Policies may return either:
    1. Normalized format: {"turn": float, "dash": float, "kick_power": float, "kick_angle": float}
       - turn: [-1, 1] normalized
       - dash: [0, 1] normalized
       - kick_power: [0, 1] normalized
       - kick_angle: radians
    2. RCSS format: {"kick": [power, angle_deg]} or {"dash": [power]} or {"turn": [moment_deg]}
       - Values are lists with raw RCSS values

    This function detects the format by checking if values are lists (RCSS) or floats (normalized).
    """
    if not isinstance(output, dict):
        return {}

    # Detect format by checking if values are lists (RCSS format) or scalars (normalized)
    # RCSS format has list values: {"kick": [100, 45]} or {"dash": [80]}
    for key in ("kick", "dash", "turn"):
        if key in output and isinstance(output[key], (list, tuple)):
            # RCSS command format - validate and return
            return _validate_command_format(output)

    # Normalized format - convert to RCSS
    return _convert_normalized_to_rcss(output)


def _validate_command_format(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate RCSS command format output."""
    result = {}

    if "kick" in output:
        kick = output["kick"]
        if isinstance(kick, (list, tuple)) and len(kick) >= 2:
            result["kick"] = [_clamp(kick[0], 0, MAX_KICK_POWER), _clamp(kick[1], -180, 180)]
    elif "turn" in output:
        turn = output["turn"]
        if isinstance(turn, (list, tuple)) and len(turn) >= 1:
            result["turn"] = [_clamp(turn[0], -180, 180)]
    elif "dash" in output:
        dash = output["dash"]
        if isinstance(dash, (list, tuple)) and len(dash) >= 1:
            result["dash"] = [_clamp(dash[0], -MAX_DASH_POWER, MAX_DASH_POWER)]

    return result


def _convert_normalized_to_rcss(output: Dict[str, Any]) -> Dict[str, Any]:
    """Convert normalized policy output to RCSS command format.

    Normalized format:
    - turn: [-1, 1] -> moment in degrees [-180, 180]
    - dash: [0, 1] -> power [0, 100]
    - kick_power: [0, 1] -> power [0, 100]
    - kick_angle: radians -> degrees [-180, 180]
    """
    # Priority: kick > turn > dash
    kick_power = float(output.get("kick_power", 0.0))
    if kick_power > 0.1:
        # Convert kick
        power = _clamp(kick_power * MAX_KICK_POWER, 0, MAX_KICK_POWER)
        angle_rad = float(output.get("kick_angle", 0.0))
        angle_deg = math.degrees(angle_rad)
        angle_deg = _clamp(angle_deg, -180, 180)
        return {"kick": [power, angle_deg]}

    turn = float(output.get("turn", 0.0))
    if abs(turn) > 0.1:
        # Convert turn: [-1, 1] -> [-180, 180] degrees
        moment = turn * 180.0
        moment = _clamp(moment, -180, 180)
        return {"turn": [moment]}

    dash = float(output.get("dash", 0.0))
    if dash > 0.1:
        # Convert dash: [0, 1] -> [0, 100] power
        power = _clamp(dash * MAX_DASH_POWER, 0, MAX_DASH_POWER)
        return {"dash": [power]}

    # No significant action
    return {}


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
