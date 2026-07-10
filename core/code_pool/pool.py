from __future__ import annotations

import math
import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.behavior.primitives.steering import (
    flee_components,
    lead_target,
    normalize_angle,
    normalized_components,
    turn_then_dash,
)

from .models import CodeComponent, CompilationError, ComponentNotFoundError
from .sandbox import build_restricted_globals, parse_and_validate

# Builtin component IDs for default policies
BUILTIN_SEEK_NEAREST_FOOD_ID = "builtin_seek_nearest_food"
BUILTIN_FLEE_FROM_THREAT_ID = "builtin_flee_from_threat"
BUILTIN_CHASE_BALL_SOCCER_ID = "builtin_chase_ball_soccer"
BUILTIN_DEFENSIVE_SOCCER_ID = "builtin_defensive_soccer"
BUILTIN_STRIKER_SOCCER_ID = "builtin_striker_soccer"


@dataclass(frozen=True)
class CompiledComponent:
    component_id: str
    version: int
    kind: str
    entrypoint: str
    func: Callable[..., Any]


class CodePool:
    def __init__(self, components: dict[str, CodeComponent] | None = None) -> None:
        self._components: dict[str, CodeComponent] = dict(components or {})
        self._compiled: dict[tuple[str, int], CompiledComponent] = {}

    def register(self, component_id: str, func: Callable[..., Any]) -> None:
        """Register a pre-compiled callable directly (for builtins).

        This bypasses validation and compilation since the function is already
        a trusted Python callable.
        """
        compiled = CompiledComponent(
            component_id=component_id,
            version=1,
            kind="builtin",
            entrypoint="policy",
            func=func,
        )
        self._compiled[(component_id, 1)] = compiled

    def add_component(
        self,
        *,
        kind: str,
        name: str,
        source: str,
        entrypoint: str = "policy",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        # Validate source before storing - fail fast on unsafe code
        from .safety import SafetyConfig, validate_source_safety

        validate_source_safety(source, SafetyConfig())

        component_id = str(uuid.uuid4())
        component = CodeComponent(
            component_id=component_id,
            kind=kind,
            name=name,
            source=source,
            entrypoint=entrypoint,
            version=1,
            metadata=dict(metadata or {}),
        )
        self._components[component_id] = component
        return component_id

    def remove_component(self, component_id: str) -> None:
        if component_id not in self._components:
            raise ComponentNotFoundError(f"Component not found: {component_id}")
        del self._components[component_id]
        self._compiled = {
            key: value for key, value in self._compiled.items() if key[0] != component_id
        }

    def list_components(self) -> list[CodeComponent]:
        return list(self._components.values())

    def get_component(self, component_id: str) -> CodeComponent:
        try:
            return self._components[component_id]
        except KeyError as exc:
            raise ComponentNotFoundError(f"Component not found: {component_id}") from exc

    def _compile_component(self, component: CodeComponent) -> CompiledComponent:
        tree = parse_and_validate(component.source)
        code = compile(tree, f"code_pool:{component.component_id}", "exec")
        exec_globals = build_restricted_globals()
        exec_locals: dict[str, Any] = {}
        try:
            exec(code, exec_globals, exec_locals)
        except Exception as exc:
            raise CompilationError(f"Execution failed: {exc}") from exc

        func = exec_locals.get(component.entrypoint) or exec_globals.get(component.entrypoint)
        if not callable(func):
            raise CompilationError(f"Entrypoint '{component.entrypoint}' not found or not callable")

        return CompiledComponent(
            component_id=component.component_id,
            version=component.version,
            kind=component.kind,
            entrypoint=component.entrypoint,
            func=func,
        )

    def compile(self, component_id: str) -> CompiledComponent:
        component = self.get_component(component_id)
        cache_key = (component_id, component.version)
        cached = self._compiled.get(cache_key)
        if cached is not None:
            return cached
        compiled = self._compile_component(component)
        self._compiled[cache_key] = compiled
        return compiled

    def get_callable(self, component_id: str) -> Callable[..., Any] | None:
        """Get the callable for a component by ID.

        This handles both registered builtins (which are cached directly)
        and source-based components (which require compilation).

        Args:
            component_id: The component ID to look up

        Returns:
            The callable function, or None if not found
        """
        # Check for registered builtin first
        cached = self._compiled.get((component_id, 1))
        if cached is not None:
            return cached.func

        # Try to compile from source
        if component_id in self._components:
            return self.compile(component_id).func

        return None

    def to_dict(self) -> dict[str, Any]:
        components = [component.to_dict() for component in self._components.values()]
        components.sort(key=lambda item: item["component_id"])
        return {"components": components}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodePool:
        components_data = data.get("components", [])
        components = {
            entry["component_id"]: CodeComponent.from_dict(entry) for entry in components_data
        }
        return cls(components=components)


# =============================================================================
# Builtin Policies
# =============================================================================


def seek_nearest_food_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> tuple[float, float]:
    """Simple built-in movement policy that heads toward the nearest food vector.

    Args:
        observation: Dictionary containing fish sensor data including 'nearest_food_vector'
        rng: Random number generator (unused but required for policy signature)

    Returns:
        Tuple of (vx, vy) normalized direction toward nearest food, or (0, 0) if no food
    """
    _ = rng
    food_vector = observation.get("nearest_food_vector")
    if isinstance(food_vector, dict):
        try:
            dx = float(food_vector.get("x", 0.0))
            dy = float(food_vector.get("y", 0.0))
        except (TypeError, ValueError):
            dx = 0.0
            dy = 0.0
        return normalized_components(dx, dy)
    return (0.0, 0.0)


def flee_from_threat_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> tuple[float, float]:
    """Built-in movement policy that flees from the nearest threat.

    Args:
        observation: Dictionary containing 'nearest_threat_vector'
        rng: Random number generator (unused but required for policy signature)

    Returns:
        Tuple of (vx, vy) normalized direction away from threat, or (0, 0) if no threat
    """
    _ = rng
    threat_vector = observation.get("nearest_threat_vector")
    if isinstance(threat_vector, dict):
        try:
            dx = float(threat_vector.get("x", 0.0))
            dy = float(threat_vector.get("y", 0.0))
        except (TypeError, ValueError):
            dx = 0.0
            dy = 0.0
        return flee_components(dx, dy)
    return (0.0, 0.0)


# Evolvable parameter keys shared by all builtin soccer policies.
# Every key defaults to 0.0 (= hand-tuned baseline behavior) and is mapped
# through a clamped scale inside the policy, so any mutated value in the
# genome's [-10, 10] range stays physically sane. Seeding these keys into
# soccer_policy_params is what gives selection heritable material to act on
# (mutation only perturbs keys that already exist).
SOCCER_POLICY_PARAM_KEYS: tuple[str, ...] = (
    "intercept_lead",
    "shot_range",
    "dribble_power",
    "stamina_floor",
    "hold_depth",
    "press_radius",
    # On-ball / pursuit control. Neutral at raw 0.0 (they reproduce the old
    # hard-coded steering constants), so the substrate widens without shifting
    # the hand-tuned baseline; variation enters only via mutation.
    "approach_precision",
    "pursuit_commit",
)

# The engine only applies kicks when the ball center is within
# kickable_margin + player_size (= 1.0m with canonical params) of the player
# center; beyond that the command is silently dropped and the cycle is wasted.
# Gate kicks slightly inside that radius so every kick we issue lands.
_ENGINE_KICKABLE_DIST = 0.98


def _norm_angle(angle: float) -> float:
    """Normalize an angle to [-pi, pi]."""
    return normalize_angle(angle)


def _scaled_param(
    params: dict[str, float],
    key: str,
    base: float,
    scale: float,
    lo: float,
    hi: float,
) -> float:
    """Map an evolvable param (raw genome value, ~[-10, 10]) onto a bounded knob."""
    try:
        raw = float(params.get(key, 0.0))
    except (TypeError, ValueError):
        raw = 0.0
    return max(lo, min(hi, base + scale * raw))


def _steer_action(
    tx: float,
    ty: float,
    facing_angle: float,
    stamina_ratio: float,
    stamina_floor: float,
    align_threshold: float = 0.25,
    commit_dist: float = 0.4,
) -> dict[str, float]:
    """Turn toward, then dash at, the relative target (tx, ty).

    Turning is far more effective at low speed (RCSS divides the turn moment
    by 1 + inertia_moment * speed), so we stop dashing while a large turn is
    needed instead of sliding past the target.

    ``align_threshold`` (from the ``approach_precision`` gene) sets how tightly
    the player aligns before dashing; ``commit_dist`` (``pursuit_commit``) is
    how close to the target it keeps dashing before easing off.
    """
    turn, dash = turn_then_dash(
        tx,
        ty,
        facing_angle,
        stamina_ratio,
        stamina_floor,
        align_threshold=align_threshold,
        commit_dist=commit_dist,
    )
    return {"turn": turn, "dash": dash, "kick_power": 0.0, "kick_angle": 0.0}


def _soccer_policy_core(observation: dict[str, Any], role: str) -> dict[str, float]:
    """Shared param-driven core for the builtin soccer policies.

    Roles differ only in off-ball positioning:
    - "chaser": always intercepts the ball
    - "striker": lurks between the ball and the opponent goal, presses when close
    - "defender": holds the line between own goal and the ball, presses when close

    All geometry is derived from goal_direction (already side- and
    half-time-swap-aware via build_observation), so every role works on both
    teams and in both halves.
    """
    params_raw = observation.get("params")
    params: dict[str, float] = params_raw if isinstance(params_raw, dict) else {}

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

    # Evolvable knobs (base values are the hand-tuned baseline; a raw genome
    # value of 0.0 reproduces it exactly).
    intercept_lead = _scaled_param(params, "intercept_lead", 5.0, 1.2, 0.0, 16.0)
    shot_range = _scaled_param(params, "shot_range", 40.0, 2.0, 10.0, 60.0)
    dribble_power = _scaled_param(params, "dribble_power", 0.65, 0.035, 0.15, 1.0)
    stamina_floor = _scaled_param(params, "stamina_floor", 0.35, 0.04, 0.05, 0.85)
    hold_depth = _scaled_param(params, "hold_depth", 0.40, 0.035, 0.10, 0.80)
    press_radius = _scaled_param(params, "press_radius", 14.0, 1.6, 3.0, 40.0)
    # On-ball pursuit control (raw 0.0 -> the old hard-coded 0.25 / 0.40).
    # approach_precision uses a negative scale so a *higher* gene value means a
    # *tighter* align-before-dash threshold (more precise), matching the name.
    approach_precision = _scaled_param(params, "approach_precision", 0.25, -0.03, 0.08, 0.55)
    pursuit_commit = _scaled_param(params, "pursuit_commit", 0.40, 0.05, 0.10, 0.90)

    # --- On the ball: shoot or dribble toward the opponent goal ---
    if ball_dist <= _ENGINE_KICKABLE_DIST:
        kick_angle = _norm_angle(math.atan2(gry, grx) - facing_angle)
        if goal_dist <= shot_range or role == "defender":
            # In range: shoot full power. Defenders always clear hard.
            kick_power = 1.0
        else:
            # Out of range: dribble - a soft touch toward goal we can chase,
            # instead of a long ball the defense collects.
            kick_power = dribble_power
        return {"turn": 0.0, "dash": 0.0, "kick_power": kick_power, "kick_angle": kick_angle}

    # --- Off the ball: role-specific positioning ---
    # Lead the ball's velocity to intercept where it is going, not where it is.
    ix, iy = lead_target(brx, bry, ball_vx, ball_vy, intercept_lead)

    if role == "striker":
        # Ball in the offensive zone (near opponent goal) or close by: press.
        ball_to_goal_x = grx - brx
        ball_to_goal_y = gry - bry
        ball_goal_dist = math.sqrt(ball_to_goal_x**2 + ball_to_goal_y**2)
        if ball_dist <= press_radius or ball_goal_dist <= field_length * 0.5:
            tx, ty = ix, iy
        else:
            # Lurk between the ball and the opponent goal, hold_depth of the
            # way back from the goal toward the ball.
            goal_x, goal_y = sx + grx, sy + gry
            ball_x, ball_y = sx + brx, sy + bry
            tx = (goal_x + (ball_x - goal_x) * hold_depth) - sx
            ty = (goal_y + (ball_y - goal_y) * hold_depth) - sy
    elif role == "defender":
        if ball_dist <= press_radius:
            tx, ty = ix, iy
        else:
            # Hold the line between own goal and the ball. Goals are mirrored
            # across the field center, so own goal = -(opponent goal).
            goal_x, goal_y = sx + grx, sy + gry
            own_goal_x, own_goal_y = -goal_x, -goal_y
            ball_x, ball_y = sx + brx, sy + bry
            tx = (own_goal_x + (ball_x - own_goal_x) * hold_depth) - sx
            ty = (own_goal_y + (ball_y - own_goal_y) * hold_depth) - sy
    else:
        tx, ty = ix, iy

    return _steer_action(
        tx,
        ty,
        facing_angle,
        stamina_ratio,
        stamina_floor,
        align_threshold=approach_precision,
        commit_dist=pursuit_commit,
    )


def default_soccer_policy_params(
    policy_id: str | None = None,
    rng: random.Random | None = None,
    jitter: float = 0.0,
) -> dict[str, float]:
    """Default (zero) values for all evolvable soccer policy params.

    Seed these into soccer_policy_params when a soccer policy is assigned so
    mutation/crossover (which only touch existing keys) have material to work
    with. Optional Gaussian jitter gives the founding population initial
    variance for selection to act on.
    """
    _ = policy_id  # All builtin policies share the same param space.
    values: dict[str, float] = {}
    for key in SOCCER_POLICY_PARAM_KEYS:
        value = 0.0
        if rng is not None and jitter > 0.0:
            value = max(-10.0, min(10.0, rng.gauss(0.0, jitter)))
        values[key] = value
    return values


def chase_ball_soccer_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """Built-in soccer policy that intercepts the ball and works it toward goal."""
    _ = rng
    try:
        return _soccer_policy_core(observation, role="chaser")
    except (TypeError, ValueError, KeyError):
        return {"turn": 0.0, "dash": 0.0, "kick_power": 0.0, "kick_angle": 0.0}


def defensive_soccer_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """Built-in soccer policy that screens its own goal and clears the ball."""
    _ = rng
    try:
        return _soccer_policy_core(observation, role="defender")
    except (TypeError, ValueError, KeyError):
        return {"turn": 0.0, "dash": 0.0, "kick_power": 0.0, "kick_angle": 0.0}


def striker_soccer_policy(
    observation: dict[str, Any], rng: random.Random | None
) -> dict[str, float]:
    """Built-in soccer policy that lurks upfield and presses in the offensive zone."""
    _ = rng
    try:
        return _soccer_policy_core(observation, role="striker")
    except (TypeError, ValueError, KeyError):
        return {"turn": 0.0, "dash": 0.0, "kick_power": 0.0, "kick_angle": 0.0}
