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

from core.entities.ball import Ball
from core.movement.intents import MovementIntent

if TYPE_CHECKING:
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
    """
    # The ball is genuinely optional on the environment, so getattr-with-default
    # is the right tool here (unlike energy/max_energy, which every fish has).
    ball = getattr(fish.environment, "ball", None)
    if ball is None:
        agents = getattr(fish.environment, "agents", None)
        if agents:
            for entity in agents:
                if isinstance(entity, Ball):
                    ball = entity
                    break

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

    # Calculate direction to ball
    dx = ball.pos.x - fish.pos.x
    dy = ball.pos.y - fish.pos.y
    dist = math.sqrt(dx * dx + dy * dy)

    if dist < 10:  # Already at ball
        return None

    module_vector = _pursuit_module_vector(fish, ball)
    if module_vector is not None:
        return (
            module_vector[0] * BALL_PURSUIT_TARGET_SPEED,
            module_vector[1] * BALL_PURSUIT_TARGET_SPEED,
        )

    # Normalize and scale to the pursuit target magnitude (re-scaled downstream).
    vx = (dx / dist) * BALL_PURSUIT_TARGET_SPEED
    vy = (dy / dist) * BALL_PURSUIT_TARGET_SPEED

    return (vx, vy)


def _pursuit_module_vector(fish: Fish, ball: Ball) -> Velocity | None:
    """Evaluate the shared Target Pursuit Module for the ball, if active.

    None when the module isn't active for this fish (flags off or no trait),
    signaling the caller to fall back to the naive direct-line pursuit above,
    unchanged. Reachable only after the energy gate, RNG roll, and survival
    yield above have already run, so RNG draw order/outcome is identical
    regardless of whether the module path is taken.
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
        ball_position=(ball.pos.x, ball.pos.y),
        ball_velocity=(ball.vel.x, ball.vel.y),
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
