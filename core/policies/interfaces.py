"""Policy interfaces and observation builders for code-driven behavior.

This module defines the canonical policy interface that all genome-driven
policies must follow, regardless of world type (Tank, Petri, Soccer, etc).

Policy Protocol
===============
All policies are callables with the signature:
    policy(observation: dict, rng: Random) -> output

Where:
- observation: A dict containing all sensory inputs + metadata
  - Always includes 'dt' (float): time delta for frame-rate independence
  - May include 'params' (dict): policy-specific tuning parameters
  - Rest is policy-kind specific (position, velocity, game state, etc.)

- rng: A seeded Random instance for determinism (never use global random!)

- output: Policy-kind specific action or decision
  - movement_policy: (vx, vy) tuple, dict, or MovementAction
  - soccer_policy: dict representing SoccerAction
  - poker_policy: dict representing poker decision

Safety Guarantees
=================
All policies executed through GenomeCodePool are subject to:
- AST-level validation (no imports, no file I/O, limited builtins)
- Runtime safety (no infinite loops, clamped outputs, NaN/Inf handling)
- Determinism enforcement (explicit RNG, no time-based calls)
"""

from __future__ import annotations

import random as pyrandom
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, Protocol

if TYPE_CHECKING:
    from core.entities import Fish

Observation = Dict[str, Any]


# =============================================================================
# Canonical Policy Protocol
# =============================================================================


class Policy(Protocol):
    """Base protocol for all genome-driven policies.

    This is a structural type (Protocol) that defines the interface all
    policies must satisfy. Policies don't need to inherit from this class,
    they just need to be callable with the right signature.
    """

    def __call__(self, observation: dict[str, Any], rng: pyrandom.Random) -> Any:
        """Execute the policy.

        Args:
            observation: Observation dict with sensory inputs and metadata.
                Always includes 'dt' (float) and optionally 'params' (dict).
            rng: Seeded random number generator for deterministic behavior.

        Returns:
            Policy-kind specific output (see MovementPolicy, SoccerPolicy, etc).
        """
        ...


class MovementPolicy(Protocol):
    """Protocol for movement policies (Tank, Petri worlds).

    Movement policies observe the local environment and decide on a
    desired velocity vector.
    """

    def __call__(
        self, observation: dict[str, Any], rng: pyrandom.Random
    ) -> tuple[float, float] | MovementAction | dict[str, float]:
        """Decide on desired movement.

        Args:
            observation: Contains position, velocity, nearest_food_vector,
                nearest_threat_vector, energy, age, can_play_poker, dt, params.
            rng: Seeded RNG for determinism.

        Returns:
            Desired velocity as:
            - tuple: (vx, vy)
            - dict: {"vx": x, "vy": y} or {"x": x, "y": y}
            - MovementAction: MovementAction(vx, vy)

            Values should be normalized to roughly [-1, 1] (enforced by SafeExecutor).
        """
        ...


class SoccerPolicy(Protocol):
    """Protocol for soccer policies (Soccer training and rcssserver).

    Soccer policies observe the full game state and decide on multi-faceted
    actions (movement, turning, kicking).
    """

    def __call__(self, observation: dict[str, Any], rng: pyrandom.Random) -> dict[str, Any]:
        """Decide on soccer action.

        Args:
            observation: Contains position, velocity, stamina, facing_angle,
                ball_position, ball_velocity, teammates, opponents, game_time,
                play_mode, field dimensions, dt, params.
            rng: Seeded RNG for determinism.

        Returns:
            Dict representing SoccerAction with keys:
            - move_target: {"x": float, "y": float} or None
            - face_angle: float (radians) or None
            - kick_power: float [0.0, 1.0]
            - kick_angle: float (radians relative to facing)
        """
        ...


class PokerPolicy(Protocol):
    """Protocol for poker policies (Tank world poker mini-game).

    Poker policies observe hand state and game context to make
    betting decisions.
    """

    def __call__(self, observation: dict[str, Any], rng: pyrandom.Random) -> dict[str, Any]:
        """Decide on poker action.

        Args:
            observation: Contains hand, pot, opponents, betting_round, etc.
            rng: Seeded RNG for determinism.

        Returns:
            Dict representing poker decision with action type and amount.
        """
        ...


# =============================================================================
# Action Types
# =============================================================================


@dataclass(frozen=True)
class MovementAction:
    """Normalized movement action returned by code policies."""

    vx: float
    vy: float


def build_movement_observation(fish: Fish) -> Observation:
    """Build a minimal observation payload for movement policies."""
    from core.config.food import BASE_FOOD_DETECTION_RANGE
    from core.entities import Crab, Food

    environment = fish.environment
    detection_modifier = getattr(environment, "get_detection_modifier", lambda: 1.0)()
    max_food_distance = BASE_FOOD_DETECTION_RANGE * detection_modifier

    nearest_food_vector = _nearest_vector(
        fish, Food, max_distance=max_food_distance, use_resources=True
    )
    nearest_threat_vector = _nearest_vector(fish, Crab, max_distance=200.0, use_resources=False)

    return {
        "position": {"x": fish.pos.x, "y": fish.pos.y},
        "velocity": {"x": fish.vel.x, "y": fish.vel.y},
        "nearest_food_vector": nearest_food_vector,
        "nearest_threat_vector": nearest_threat_vector,
        "energy": fish.energy,
        "age": getattr(getattr(fish, "_lifecycle_component", None), "age", 0),
        "can_play_poker": getattr(fish, "can_play_skill_games", False),
    }


def _nearest_vector(
    fish: Fish,
    agent_type: type,
    *,
    max_distance: float | None,
    use_resources: bool,
) -> dict[str, float]:
    environment = fish.environment
    fish_x = fish.pos.x
    fish_y = fish.pos.y

    if max_distance is not None:
        radius = int(max_distance) + 1
        if use_resources and hasattr(environment, "nearby_resources"):
            agents = environment.nearby_resources(fish, radius)
        else:
            agents = environment.nearby_agents_by_type(fish, radius, agent_type)
    else:
        agents = environment.get_agents_of_type(agent_type)

    if not agents:
        return {"x": 0.0, "y": 0.0}

    max_distance_sq = max_distance * max_distance if max_distance is not None else None
    nearest_dx = 0.0
    nearest_dy = 0.0
    nearest_dist_sq = float("inf")

    for agent in agents:
        dx = agent.pos.x - fish_x
        dy = agent.pos.y - fish_y
        dist_sq = dx * dx + dy * dy
        if max_distance_sq is not None and dist_sq > max_distance_sq:
            continue
        if dist_sq < nearest_dist_sq:
            nearest_dist_sq = dist_sq
            nearest_dx = dx
            nearest_dy = dy

    if nearest_dist_sq == float("inf"):
        return {"x": 0.0, "y": 0.0}

    return {"x": nearest_dx, "y": nearest_dy}
