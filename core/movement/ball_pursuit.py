"""Soccer-ball pursuit movement drive.

This is the one place that knows fish *want* the ball. It is a self-contained
:class:`MovementConsideration` (ADR-010): it owns its own activation condition
(energy gate + survival yield) and desired velocity, so the generic movement
strategy no longer carries any ball/soccer concept. The arbiter in
``core.movement.considerations`` lists it; it does not implement it.

Note on placement: ball pursuit is a *tank-world default* drive (the practice
ball exists whenever ``tank_practice_enabled`` is set, which is the default even
when ``soccer_enabled`` is False), not a soccer-only minigame plugin. It lives
in ``core.movement`` rather than ``core.minigames.soccer`` so a plain tank run
does not pull in the heavy soccer package ``__init__``. See ADR-010 / ADR-011.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from core.behavior.target_memory import (
    BALL_TARGET_ID,
    TargetCandidate,
    TargetMemoryState,
    decide_target,
)
from core.entities.ball import Ball
from core.movement.intents import MovementIntent

if TYPE_CHECKING:
    from core.behavior.target_memory import TargetMemoryDecision
    from core.entities import Fish
    from core.movement_strategy import AlgorithmicMovement

Velocity = tuple[float, float]

# Ball play is only worthwhile once a fish is genuinely topped up. Reproduction
# is funded by energy banked *above* max_energy (overflow), so a fish anywhere
# below max is still climbing toward its next birth - diverting it to the ball
# burns the very energy that would fund offspring. Gate on near-max energy so
# only fish at the overflow boundary spend genuine surplus on play.
PLAY_ENERGY_THRESHOLD_RATIO = 0.98

# Target magnitude for the pursuit velocity. The arbiter's velocity tail in
# AlgorithmicMovement.move() re-scales by the fish's speed and clamps the
# magnitude, so this is a "head straight at the ball at full tilt" signal, not a
# literal pixels/frame speed. (Historically this read a non-existent
# ``fish.max_speed`` attribute via getattr and silently fell back to 2.0; the
# constant makes the real, always-used value explicit.)
BALL_PURSUIT_TARGET_SPEED = 2.0


def ball_pursuit_velocity(fish: Fish) -> Velocity | None:
    """Desired velocity toward the soccer ball, or None if not pursuing.

    Only fish with an energy surplus play ball, and even a topped-up fish yields
    to a live survival drive (threat/food) so leisure never pre-empts survival.

    The survival yield is checked *after* the RNG draw so the random stream is
    identical to when ball pursuit had unconditional top priority - only the
    *outcome* changes, and only for the few fish that both rolled "play" and
    have a survival drive (ADR-010 step 2).

    Reads (never advances) this frame's ball target-memory decision -
    core.behavior.target_memory_controller.advance_target_memory is what
    advances it, called once per fish per frame from Fish.update() before
    movement arbitration. That makes this function side-effect-free, so it
    is safe to call it zero or more times per frame (e.g. from the
    inspector) without perturbing memory.
    """
    ball = _resolve_ball(fish)
    if ball is None:
        return None  # No ball = no soccer

    max_energy = fish.max_energy
    current_energy = fish.energy
    energy_ratio = current_energy / max_energy if max_energy > 0 else 1.0

    if energy_ratio <= PLAY_ENERGY_THRESHOLD_RATIO:
        return None  # Still building toward reproduction: forage, don't play

    # Cap kept low: surplus energy banked via overflow funds reproduction, so
    # heavy ball play by full-energy fish directly suppresses births.
    surplus = (energy_ratio - PLAY_ENERGY_THRESHOLD_RATIO) / (1.0 - PLAY_ENERGY_THRESHOLD_RATIO)
    pursuit_prob = 0.25 * surplus  # 0% at play threshold -> 25% at full energy

    rng = fish.environment.rng
    if rng.random() > pursuit_prob:
        return None

    # Survival outranks leisure (checked after the RNG draw above; see docstring).
    behavior = fish.genome.behavioral.behavior.value if fish.genome.behavioral.behavior else None
    if behavior is not None and behavior.has_survival_priority(fish):
        return None

    # Memory's target position/velocity mirror the ball's live values exactly
    # whenever it's continuously visible (always true today - see
    # compute_ball_target_memory_decision's docstring); this is what lets a
    # future occlusion mechanic plug in later without touching this call site.
    memory_decision = fish.last_target_memory_decisions.get("ball")
    if memory_decision is not None and memory_decision.selected_target_id is not None:
        target_position = memory_decision.target_position
        target_velocity = memory_decision.target_velocity
    else:
        target_position = (ball.pos.x, ball.pos.y)
        target_velocity = (ball.vel.x, ball.vel.y)

    dx = target_position[0] - fish.pos.x
    dy = target_position[1] - fish.pos.y
    dist = math.sqrt(dx * dx + dy * dy)

    if dist < 10:  # Already at ball
        return None

    module_vector = _pursuit_module_vector_for(fish, target_position, target_velocity)
    if module_vector is not None:
        return (
            module_vector[0] * BALL_PURSUIT_TARGET_SPEED,
            module_vector[1] * BALL_PURSUIT_TARGET_SPEED,
        )

    # Normalize and scale to the pursuit target magnitude (re-scaled downstream).
    vx = (dx / dist) * BALL_PURSUIT_TARGET_SPEED
    vy = (dy / dist) * BALL_PURSUIT_TARGET_SPEED

    return (vx, vy)


def compute_ball_target_memory_decision(fish: Fish) -> TargetMemoryDecision | None:
    """Advance and return the fish's ball-domain target-memory decision.

    Called exactly once per frame by
    ``core.behavior.target_memory_controller.advance_target_memory``, before
    movement arbitration runs - regardless of any of ball_pursuit_velocity's
    gates, so frames_since_seen reflects real elapsed frames even on frames a
    fish skips pursuit entirely (or never reaches BallPursuitConsideration
    because a higher-priority drive won). Do not call this from
    ball_pursuit_velocity or the inspector; read
    ``fish.last_target_memory_decisions["ball"]`` instead. Returns None when
    memory isn't active for this fish (flag off or no trait) - callers then
    fall back to the ball's live position, byte-identical to pre-memory
    behavior.

    The engine has no detection-range/occlusion concept for the ball today -
    "exists" and "perceived" are the same boolean (ball is not None) - so this
    candidate is either present every frame or never; SEARCH/DROP won't
    trigger for the ball until a real occlusion mechanic exists to feed a
    genuinely intermittent candidate here.
    """
    config = fish.environment.simulation_config
    if config is None or not config.tank.target_memory_enabled:
        return None
    params_trait = fish.genome.behavioral.target_memory
    params = params_trait.value if params_trait is not None else None
    if params is None:
        return None

    ball = _resolve_ball(fish)
    candidates = (
        [
            TargetCandidate(
                target_id=BALL_TARGET_ID,
                position=(ball.pos.x, ball.pos.y),
                velocity=(ball.vel.x, ball.vel.y),
                value=1.0,
            )
        ]
        if ball is not None
        else []
    )
    state = fish.target_memory_state.get("ball", TargetMemoryState.empty())
    next_state, decision = decide_target(state, candidates, (fish.pos.x, fish.pos.y), params)
    fish.target_memory_state["ball"] = next_state
    return decision


def _resolve_ball(fish: Fish) -> Ball | None:
    """Look up the environment's soccer ball, if any.

    The ball is genuinely optional on the environment, so getattr-with-default
    is the right tool here (unlike energy/max_energy, which every fish has).
    """
    ball = getattr(fish.environment, "ball", None)
    if ball is None:
        agents = getattr(fish.environment, "agents", None)
        if agents:
            for entity in agents:
                if isinstance(entity, Ball):
                    ball = entity
                    break
    return ball


def _pursuit_module_vector(fish: Fish, ball: Ball) -> Velocity | None:
    """Evaluate the shared Target Pursuit Module for the ball's live position.

    None when the module isn't active for this fish (flags off or no trait),
    signaling the caller to fall back to the naive direct-line pursuit above,
    unchanged. Reachable only after the energy gate, RNG roll, and survival
    yield above have already run, so RNG draw order/outcome is identical
    regardless of whether the module path is taken.
    """
    return _pursuit_module_vector_for(fish, (ball.pos.x, ball.pos.y), (ball.vel.x, ball.vel.y))


def _pursuit_module_vector_for(
    fish: Fish, target_position: Velocity, target_velocity: Velocity
) -> Velocity | None:
    """Evaluate the shared Target Pursuit Module for an arbitrary target.

    Same contract as ``_pursuit_module_vector`` but takes position/velocity
    directly so the caller can pass target-memory's (possibly dead-reckoned)
    values instead of the ball's live ones.
    """
    config = fish.environment.simulation_config
    if config is None or not config.tank.target_pursuit_module_enabled:
        return None
    module_trait = fish.genome.behavioral.target_pursuit_module
    module = module_trait.value if module_trait is not None else None
    if module is None:
        return None

    from core.behavior.soccer_adapter import build_soccer_target_observation

    observation = build_soccer_target_observation(
        self_position=(fish.pos.x, fish.pos.y),
        self_velocity=(fish.vel.x, fish.vel.y),
        self_speed=fish.speed,
        ball_position=target_position,
        ball_velocity=target_velocity,
    )
    output = module.compile_cached().evaluate(observation.to_values())
    if not isinstance(output, tuple) or len(output) != 2:
        return None
    return float(output[0]), float(output[1])


class BallPursuitConsideration:
    """Soccer-ball pursuit drive for fish with surplus energy.

    Implements the :class:`~core.movement.considerations.MovementConsideration`
    protocol structurally; the ``strategy`` argument is unused because this
    drive depends only on the fish and its environment.
    """

    name = "ball_pursuit"

    def intent(self, strategy: AlgorithmicMovement, fish: Fish) -> MovementIntent | None:
        return MovementIntent.from_velocity(
            ball_pursuit_velocity(fish),
            kind="soccer_pursuit",
            source=self.name,
            urgency=0.42,
        )
