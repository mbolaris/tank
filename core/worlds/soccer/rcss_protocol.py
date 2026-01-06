"""RoboCup Soccer Simulator (rcssserver) protocol implementation.

This module provides parsing and command building for the rcssserver protocol.
It handles the translation between:
- Server messages (see, sense_body, hear) → structured observations
- High-level SoccerAction → server commands (dash, turn, kick, move)

References:
- RoboCup Soccer Simulator: https://github.com/rcsoccersim/rcssserver
- Protocol documentation: https://rcsoccersim.github.io/manual/
"""

import math
import re
from dataclasses import dataclass
from typing import List, Optional

from core.worlds.soccer.types import PlayerState, SoccerAction, Vector2D

# ============================================================================
# Structured output models for parsed messages
# ============================================================================


@dataclass
class ObjectInfo:
    """Information about a visible object from see message."""

    obj_type: str  # "ball", "player", "goal", "line", etc.
    distance: Optional[float] = None
    direction: Optional[float] = None  # degrees relative to player's view
    dist_change: Optional[float] = None
    dir_change: Optional[float] = None
    # For players
    team: Optional[str] = None
    uniform_number: Optional[int] = None
    body_facing_dir: Optional[float] = None
    head_facing_dir: Optional[float] = None


@dataclass
class SeeInfo:
    """Parsed visual sensor information."""

    time: int
    objects: List[ObjectInfo]

    def get_ball(self) -> Optional[ObjectInfo]:
        """Get ball object if visible."""
        for obj in self.objects:
            if obj.obj_type == "ball":
                return obj
        return None

    def get_players(self, team: Optional[str] = None) -> List[ObjectInfo]:
        """Get visible players, optionally filtered by team."""
        players = [obj for obj in self.objects if obj.obj_type == "player"]
        if team:
            players = [p for p in players if p.team == team]
        return players


@dataclass
class SenseBodyInfo:
    """Parsed body sensor information."""

    time: int
    view_quality: str  # "high" or "low"
    view_width: str  # "narrow", "normal", or "wide"
    stamina: float
    effort: float
    speed_amount: float
    speed_direction: float  # degrees
    head_angle: float  # degrees
    kick_count: int
    dash_count: int
    turn_count: int
    say_count: int
    turn_neck_count: int
    catch_count: int
    move_count: int
    change_view_count: int


@dataclass
class HearInfo:
    """Parsed audio sensor information."""

    time: int
    sender: str  # "self", "referee", direction (-180 to 180), or coach
    message: str


# ============================================================================
# Message parsers
# ============================================================================


def parse_see_message(msg: str) -> Optional[SeeInfo]:
    """Parse visual sensor message from rcssserver.

    Format: (see Time ObjInfo ObjInfo ...)
    ObjInfo: (ObjName Distance Direction [DistChange DirChange [BodyDir HeadDir]])
             or (ObjName Direction)

    Example:
        "(see 0 ((b) 5.2 30) ((p left 2) 10.1 -15))"

    Args:
        msg: Raw see message string

    Returns:
        SeeInfo object or None if parsing fails
    """
    msg = msg.strip()
    if not msg.startswith("(see "):
        return None

    try:
        # Extract time
        time_match = re.match(r"\(see\s+(\d+)", msg)
        if not time_match:
            return None
        time = int(time_match.group(1))

        objects = []

        # Find all object info blocks - they start with (( and end with ))
        # We'll use a simple state machine to parse nested parens
        i = msg.find("((")
        while i != -1 and i < len(msg):
            # Find matching close parens
            depth = 0
            start = i
            j = i
            while j < len(msg):
                if msg[j] == "(":
                    depth += 1
                elif msg[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1

            if depth == 0:
                obj_str = msg[start : j + 1]
                obj = _parse_object_info(obj_str)
                if obj:
                    objects.append(obj)

            # Find next object
            i = msg.find("((", j)

        return SeeInfo(time=time, objects=objects)

    except Exception:
        return None


def _parse_object_info(obj_str: str) -> Optional[ObjectInfo]:
    """Parse a single object info string.

    Examples:
        "((b) 5.2 30.5)" -> ball at distance 5.2, direction 30.5
        "((p left 2) 10.1 -15.0)" -> player left 2 at distance 10.1, direction -15
        "((g r) 45)" -> right goal at direction 45 (distance unknown)
    """
    obj_str = obj_str.strip()

    # Extract object name (first parenthesized group)
    name_match = re.match(r"\(\(([^)]+)\)", obj_str)
    if not name_match:
        return None

    name_parts = name_match.group(1).split()

    # Determine object type
    obj_type = name_parts[0]
    team = None
    uniform_number = None

    if obj_type == "b":
        obj_type = "ball"
    elif obj_type == "p":
        obj_type = "player"
        if len(name_parts) >= 2:
            team = name_parts[1]
        if len(name_parts) >= 3:
            try:
                uniform_number = int(name_parts[2])
            except ValueError:
                pass
    elif obj_type == "g":
        obj_type = "goal"
        if len(name_parts) >= 2:
            team = name_parts[1]  # "l" or "r"

    # Extract numeric values after object name
    rest = obj_str[name_match.end() :].strip().rstrip(")")
    values = []
    for part in rest.split():
        try:
            values.append(float(part))
        except ValueError:
            pass

    # Parse values based on count
    distance = None
    direction = None
    dist_change = None
    dir_change = None
    body_facing_dir = None
    head_facing_dir = None

    if len(values) >= 1:
        if len(values) == 1:
            # Only direction (object too far for distance)
            direction = values[0]
        else:
            # Distance and direction
            distance = values[0]
            direction = values[1]

    if len(values) >= 4:
        dist_change = values[2]
        dir_change = values[3]

    if len(values) >= 6:
        body_facing_dir = values[4]
        head_facing_dir = values[5]

    return ObjectInfo(
        obj_type=obj_type,
        distance=distance,
        direction=direction,
        dist_change=dist_change,
        dir_change=dir_change,
        team=team,
        uniform_number=uniform_number,
        body_facing_dir=body_facing_dir,
        head_facing_dir=head_facing_dir,
    )


def parse_sense_body_message(msg: str) -> Optional[SenseBodyInfo]:
    """Parse body sensor message from rcssserver.

    Format: (sense_body Time (view_mode Quality Width) (stamina Stamina Effort)
             (speed Amount Direction) (head_angle Angle) (kick Count) ...)

    Example:
        "(sense_body 0 (view_mode high normal) (stamina 4000 1) (speed 0 0) ...)"

    Args:
        msg: Raw sense_body message string

    Returns:
        SenseBodyInfo object or None if parsing fails
    """
    msg = msg.strip()
    if not msg.startswith("(sense_body "):
        return None

    try:
        # Extract time
        time_match = re.match(r"\(sense_body\s+(\d+)", msg)
        if not time_match:
            return None
        time = int(time_match.group(1))

        # Extract view_mode
        view_match = re.search(r"\(view_mode\s+(\w+)\s+(\w+)\)", msg)
        view_quality = view_match.group(1) if view_match else "high"
        view_width = view_match.group(2) if view_match else "normal"

        # Extract stamina
        stamina_match = re.search(r"\(stamina\s+([\d.]+)\s+([\d.]+)", msg)
        stamina = float(stamina_match.group(1)) if stamina_match else 0.0
        effort = float(stamina_match.group(2)) if stamina_match else 1.0

        # Extract speed
        speed_match = re.search(r"\(speed\s+([\d.]+)\s+([-\d.]+)", msg)
        speed_amount = float(speed_match.group(1)) if speed_match else 0.0
        speed_direction = float(speed_match.group(2)) if speed_match else 0.0

        # Extract head_angle
        head_match = re.search(r"\(head_angle\s+([-\d.]+)", msg)
        head_angle = float(head_match.group(1)) if head_match else 0.0

        # Extract action counts
        kick_match = re.search(r"\(kick\s+(\d+)", msg)
        dash_match = re.search(r"\(dash\s+(\d+)", msg)
        turn_match = re.search(r"\(turn\s+(\d+)", msg)
        say_match = re.search(r"\(say\s+(\d+)", msg)
        turn_neck_match = re.search(r"\(turn_neck\s+(\d+)", msg)
        catch_match = re.search(r"\(catch\s+(\d+)", msg)
        move_match = re.search(r"\(move\s+(\d+)", msg)
        change_view_match = re.search(r"\(change_view\s+(\d+)", msg)

        return SenseBodyInfo(
            time=time,
            view_quality=view_quality,
            view_width=view_width,
            stamina=stamina,
            effort=effort,
            speed_amount=speed_amount,
            speed_direction=speed_direction,
            head_angle=head_angle,
            kick_count=int(kick_match.group(1)) if kick_match else 0,
            dash_count=int(dash_match.group(1)) if dash_match else 0,
            turn_count=int(turn_match.group(1)) if turn_match else 0,
            say_count=int(say_match.group(1)) if say_match else 0,
            turn_neck_count=int(turn_neck_match.group(1)) if turn_neck_match else 0,
            catch_count=int(catch_match.group(1)) if catch_match else 0,
            move_count=int(move_match.group(1)) if move_match else 0,
            change_view_count=int(change_view_match.group(1)) if change_view_match else 0,
        )

    except Exception:
        return None


def parse_hear_message(msg: str) -> Optional[HearInfo]:
    """Parse audio sensor message from rcssserver.

    Format: (hear Time Sender "Message")
    Sender can be: self, referee, online_coach_left, online_coach_right, or direction

    Example:
        "(hear 120 referee \"kick_off_left\")"
        "(hear 125 -45 \"pass\")"

    Args:
        msg: Raw hear message string

    Returns:
        HearInfo object or None if parsing fails
    """
    msg = msg.strip()
    if not msg.startswith("(hear "):
        return None

    try:
        # Extract time and sender
        match = re.match(r'\(hear\s+(\d+)\s+([^\s"]+)\s+"([^"]*)"', msg)
        if not match:
            return None

        time = int(match.group(1))
        sender = match.group(2)
        message = match.group(3)

        return HearInfo(time=time, sender=sender, message=message)

    except Exception:
        return None


# ============================================================================
# Command builders
# ============================================================================


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def build_dash_command(power: float, direction: float = 0.0) -> str:
    """Build dash command for rcssserver.

    Args:
        power: Dash power [-100, 100]
        direction: Dash direction in degrees [-180, 180] (0 = forward)

    Returns:
        Command string: "(dash {power} {direction})"
    """
    power = clamp(power, -100.0, 100.0)
    direction = clamp(direction, -180.0, 180.0)
    return f"(dash {power:.1f} {direction:.1f})"


def build_turn_command(moment: float) -> str:
    """Build turn command for rcssserver.

    Args:
        moment: Turn angle in degrees [-180, 180]

    Returns:
        Command string: "(turn {moment})"
    """
    moment = clamp(moment, -180.0, 180.0)
    return f"(turn {moment:.1f})"


def build_kick_command(power: float, direction: float) -> str:
    """Build kick command for rcssserver.

    Args:
        power: Kick power [0, 100]
        direction: Kick direction in degrees [-180, 180] relative to body

    Returns:
        Command string: "(kick {power} {direction})"
    """
    power = clamp(power, 0.0, 100.0)
    direction = clamp(direction, -180.0, 180.0)
    return f"(kick {power:.1f} {direction:.1f})"


def build_move_command(x: float, y: float) -> str:
    """Build move command for rcssserver (before kick-off only).

    Args:
        x: X coordinate on field
        y: Y coordinate on field

    Returns:
        Command string: "(move {x} {y})"
    """
    return f"(move {x:.2f} {y:.2f})"


def build_init_command(team_name: str, version: int = 15) -> str:
    """Build initialization command for rcssserver.

    Args:
        team_name: Name of the team
        version: Protocol version (default: 15)

    Returns:
        Command string: "(init {team_name} (version {version}))"
    """
    return f"(init {team_name} (version {version}))"


# ============================================================================
# Translation helpers
# ============================================================================


def action_to_commands(
    action: SoccerAction,
    player_state: PlayerState,
    turn_rate: float = 1.0,
) -> List[str]:
    """Translate high-level SoccerAction to rcssserver command strings.

    Supports the normalized action format (turn/dash/kick_power/kick_angle).

    Args:
        action: High-level action intent
        player_state: Current player state (for calculating relative angles)
        turn_rate: Maximum turn rate in radians (for scaling turn command)

    Returns:
        List of command strings to send to server
    """
    commands = []

    # Handle normalized turn command
    if action.turn != 0.0:
        # Scale normalized [-1, 1] to degrees [-180, 180]
        turn_degrees = action.turn * 180.0
        commands.append(build_turn_command(turn_degrees))

    # Handle normalized dash command
    if action.dash != 0.0:
        # Scale normalized [-1, 1] to power [-100, 100]
        power = action.dash * 100.0
        commands.append(build_dash_command(power))

    # Handle kick
    if action.kick_power > 0:
        power = action.kick_power * 100  # Scale [0,1] to [0,100]
        direction_deg = math.degrees(action.kick_angle)
        commands.append(build_kick_command(power, direction_deg))

    return commands


def estimate_position_from_polar(
    observer_pos: Vector2D,
    observer_facing: float,
    distance: float,
    direction_deg: float,
) -> Vector2D:
    """Estimate absolute position from polar observation.

    Args:
        observer_pos: Observer's position
        observer_facing: Observer's facing angle in radians
        distance: Distance to object
        direction_deg: Direction to object in degrees (relative to observer's view)

    Returns:
        Estimated absolute position
    """
    # Convert direction to radians and make absolute
    direction_rad = math.radians(direction_deg)
    absolute_angle = observer_facing + direction_rad

    # Calculate position
    x = observer_pos.x + distance * math.cos(absolute_angle)
    y = observer_pos.y + distance * math.sin(absolute_angle)

    return Vector2D(x, y)
