"""Movement drive arbitration for tank-like agents.

A fish resolves competing *drives* - an explicit policy override, soccer-ball
pursuit, a genome code policy, and the composable behavior - into a single
desired velocity. This module makes that priority order **data**: an ordered
list of :class:`MovementConsideration` objects evaluated by
:class:`MovementArbiter`, rather than a hand-rolled if-chain split across the
movement strategy. See ADR-010.

Each consideration reports the velocity its drive wants this frame, or ``None``
if the drive is inactive. The arbiter returns the first active consideration's
velocity (priority = list order) and short-circuits, so an inactive downstream
drive is never evaluated and never consumes RNG - preserving the simulation's
determinism contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from core.code_pool import BUILTIN_FLEE_FROM_THREAT_ID
from core.movement.ball_pursuit import BallPursuitConsideration

if TYPE_CHECKING:
    from core.entities import Fish
    from core.movement_strategy import AlgorithmicMovement

Velocity = tuple[float, float]

__all__ = [
    "MovementConsideration",
    "PolicyOverrideConsideration",
    "BallPursuitConsideration",
    "CodePolicyConsideration",
    "ComposableBehaviorConsideration",
    "MovementArbiter",
    "default_considerations",
]


class MovementConsideration(Protocol):
    """One competing movement drive.

    Implementations are stateless; some delegate to the owning strategy (e.g.
    the policy/code/composable drives below) while others are self-contained
    (e.g. ``BallPursuitConsideration``). Either way the priority *order* lives in
    exactly one place — the arbiter's list — not in control flow.
    """

    name: str

    def desired_velocity(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        """Return this drive's desired velocity, or None if inactive."""
        ...


class PolicyOverrideConsideration:
    """Explicit movement-policy override (experiments / tests / external control)."""

    name = "policy_override"

    def desired_velocity(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        return strategy._get_policy_override_velocity(fish)


class CodePolicyConsideration:
    """Genome-encoded movement code policy (GenomeCodePool)."""

    name = "code_policy"

    def desired_velocity(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        behavior = (
            fish.genome.behavioral.behavior.value if fish.genome.behavioral.behavior else None
        )
        movement_policy_id = fish.genome.behavioral.movement_policy_id
        if (
            movement_policy_id is not None
            and movement_policy_id.value == BUILTIN_FLEE_FROM_THREAT_ID
        ):
            has_threat_priority = getattr(behavior, "has_threat_priority", None)
            has_food_priority = getattr(behavior, "has_food_priority", None)
            if (
                callable(has_threat_priority)
                and has_threat_priority(fish)
                and (not callable(has_food_priority) or not has_food_priority(fish))
            ):
                return strategy._execute_policy_if_present(fish)

        has_survival_priority = getattr(behavior, "has_survival_priority", None)
        if callable(has_survival_priority) and has_survival_priority(fish):
            return None
        return strategy._execute_policy_if_present(fish)


class ComposableBehaviorConsideration:
    """The evolvable composable behavior (threat / food / poker / social)."""

    name = "composable_behavior"

    def desired_velocity(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        return strategy._get_composable_velocity(fish)


class MovementArbiter:
    """Selects a desired velocity from an ordered list of considerations."""

    def __init__(self, considerations: list[MovementConsideration]) -> None:
        self._considerations = considerations

    @property
    def considerations(self) -> list[MovementConsideration]:
        """The ordered considerations (highest priority first)."""
        return self._considerations

    def decide(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        """Return the first active consideration's velocity, or None if none fire."""
        for consideration in self._considerations:
            velocity = consideration.desired_velocity(strategy, fish)
            if velocity is not None:
                return velocity
        return None


def default_considerations() -> list[MovementConsideration]:
    """The canonical movement priority order (highest priority first).

    ``ball_pursuit`` and ``code_policy`` are listed above the composable
    behavior, but neither pre-empts survival: each drive yields to threat/food
    via ``ComposableBehavior.has_survival_priority`` (ADR-010 step 2), so list
    position here is leisure-vs-leisure only.
    """
    return [
        PolicyOverrideConsideration(),
        BallPursuitConsideration(),
        CodePolicyConsideration(),
        ComposableBehaviorConsideration(),
    ]
