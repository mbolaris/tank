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

if TYPE_CHECKING:
    from core.entities import Fish
    from core.movement_strategy import AlgorithmicMovement

Velocity = tuple[float, float]

# Ball play is only worthwhile once a fish is genuinely topped up. Reproduction
# is funded by energy banked *above* max_energy (overflow), so a fish anywhere
# below max is still climbing toward its next birth - diverting it to the ball
# burns the very energy that would fund offspring. Gate on near-max energy so
# only fish at the overflow boundary spend genuine surplus on play.
PLAY_ENERGY_THRESHOLD_RATIO = 0.90

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

    # Normalize and scale to the pursuit target magnitude (re-scaled downstream).
    vx = (dx / dist) * BALL_PURSUIT_TARGET_SPEED
    vy = (dy / dist) * BALL_PURSUIT_TARGET_SPEED

    return (vx, vy)


class BallPursuitConsideration:
    """Soccer-ball pursuit drive for fish with surplus energy.

    Implements the :class:`~core.movement.considerations.MovementConsideration`
    protocol structurally; the ``strategy`` argument is unused because this
    drive depends only on the fish and its environment.
    """

    name = "ball_pursuit"

    def desired_velocity(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        return ball_pursuit_velocity(fish)
