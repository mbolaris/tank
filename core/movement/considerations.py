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

if TYPE_CHECKING:
    from core.entities import Fish
    from core.movement_strategy import AlgorithmicMovement

Velocity = tuple[float, float]


class MovementConsideration(Protocol):
    """One competing movement drive.

    Implementations are stateless and delegate to the owning strategy, so the
    priority *order* lives in exactly one place (the arbiter's list).
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


class BallPursuitConsideration:
    """Soccer-ball pursuit for fish with surplus energy."""

    name = "ball_pursuit"

    def desired_velocity(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        return strategy._get_ball_pursuit_velocity(fish)


class CodePolicyConsideration:
    """Genome-encoded movement code policy (GenomeCodePool)."""

    name = "code_policy"

    def desired_velocity(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
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

    NOTE: this order is the byte-identical extraction of the historical
    if-chain (ADR-010 step 1). ``ball_pursuit`` sitting above the composable
    behavior's threat/food drives is the documented mis-ordering that step 2
    corrects.
    """
    return [
        PolicyOverrideConsideration(),
        BallPursuitConsideration(),
        CodePolicyConsideration(),
        ComposableBehaviorConsideration(),
    ]
