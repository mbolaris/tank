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
from core.movement.intents import MovementArbitration, MovementIntent, Velocity

if TYPE_CHECKING:
    from core.entities import Fish
    from core.movement_strategy import AlgorithmicMovement

__all__ = [
    "MovementArbitration",
    "MovementConsideration",
    "MovementIntent",
    "PolicyOverrideConsideration",
    "BallPursuitConsideration",
    "CodePolicyConsideration",
    "GraphBehaviorConsideration",
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

    def intent(self, strategy: AlgorithmicMovement, fish: Fish) -> MovementIntent | None:
        """Return this drive's meaningful intent, or None if inactive."""
        ...


class PolicyOverrideConsideration:
    """Explicit movement-policy override (experiments / tests / external control)."""

    name = "policy_override"

    def intent(self, strategy: AlgorithmicMovement, fish: Fish) -> MovementIntent | None:
        return MovementIntent.from_velocity(
            strategy._get_policy_override_velocity(fish),
            kind="policy_override",
            source=self.name,
        )


class CodePolicyConsideration:
    """Genome-encoded movement code policy (GenomeCodePool)."""

    name = "code_policy"

    def intent(self, strategy: AlgorithmicMovement, fish: Fish) -> MovementIntent | None:
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
                return MovementIntent.from_velocity(
                    strategy._execute_policy_if_present(fish),
                    kind="code_policy",
                    source=self.name,
                )

        has_survival_priority = getattr(behavior, "has_survival_priority", None)
        if callable(has_survival_priority) and has_survival_priority(fish):
            return None
        return MovementIntent.from_velocity(
            strategy._execute_policy_if_present(fish),
            kind="code_policy",
            source=self.name,
        )


class ComposableBehaviorConsideration:
    """The evolvable composable behavior (threat / food / poker / social)."""

    name = "composable_behavior"

    def intent(self, strategy: AlgorithmicMovement, fish: Fish) -> MovementIntent | None:
        return MovementIntent.from_velocity(
            strategy._get_composable_velocity(fish),
            kind="composable_behavior",
            source=self.name,
        )


class GraphBehaviorConsideration:
    """Experimental fixed-topology graph controller for graph-carrying fish.

    Yields (returns None) on a leisure-tier classification - social cohesion
    with no live threat or hunger - so a lower-priority drive such as
    soccer-ball pursuit gets evaluated instead of being unconditionally
    preempted by a graph that merely wants to keep station with the school.
    Threat and food classifications are survival-relevant and still preempt
    everything below, matching how ``ball_pursuit``/``code_policy`` already
    yield to survival via ``has_survival_priority`` despite their own list
    position.
    """

    name = "behavior_graph"

    def intent(self, strategy: AlgorithmicMovement, fish: Fish) -> MovementIntent | None:
        from core.behavior.tank_adapter import ForagingIntentKind

        decision = strategy._get_graph_decision(fish)
        if decision is None:
            return None
        velocity, kind = decision
        if kind is ForagingIntentKind.COHESION:
            return None
        return MovementIntent.from_velocity(
            velocity,
            kind=f"graph_{kind.value}",
            source=self.name,
            allow_zero=False,
        )


class MovementArbiter:
    """Selects a desired velocity from an ordered list of considerations."""

    def __init__(self, considerations: list[MovementConsideration]) -> None:
        self._considerations = considerations

    @property
    def considerations(self) -> list[MovementConsideration]:
        """The ordered considerations (highest priority first)."""
        return self._considerations

    def arbitrate(self, strategy: AlgorithmicMovement, fish: Fish) -> MovementArbitration:
        """Select an intent without evaluating lower-priority drives unnecessarily."""
        engine = getattr(fish.environment, "engine", None)
        from core.simulation.profiler import is_profiling

        if is_profiling(engine) and engine is not None:
            import time

            start = time.perf_counter()
            with engine.profiler.context("decision"):
                result = MovementArbitration(None)
                for index, consideration in enumerate(self._considerations):
                    intent = consideration.intent(strategy, fish)
                    if intent is not None:
                        result = MovementArbitration(
                            selected=intent,
                            suppressed_sources=tuple(
                                candidate.name for candidate in self._considerations[index + 1 :]
                            ),
                        )
                        break
            engine.profiler.record_decide(time.perf_counter() - start)
            return result

        for index, consideration in enumerate(self._considerations):
            intent = consideration.intent(strategy, fish)
            if intent is not None:
                return MovementArbitration(
                    selected=intent,
                    suppressed_sources=tuple(
                        candidate.name for candidate in self._considerations[index + 1 :]
                    ),
                )
        return MovementArbitration(None)

    def decide(self, strategy: AlgorithmicMovement, fish: Fish) -> Velocity | None:
        """Return the selected velocity for compatibility with tuple callers."""
        selected = self.arbitrate(strategy, fish).selected
        return selected.velocity if selected is not None else None


def default_considerations() -> list[MovementConsideration]:
    """The canonical movement priority order (highest priority first).

    ``ball_pursuit`` and ``code_policy`` are listed above the composable
    behavior, but neither pre-empts survival: each drive yields to threat/food
    via ``ComposableBehavior.has_survival_priority`` (ADR-010 step 2), so list
    position here is leisure-vs-leisure only. ``behavior_graph`` is listed
    above ``ball_pursuit`` for the same reason: it yields on a leisure-tier
    (social cohesion) classification rather than unconditionally winning on
    any nonzero output, so soccer gets a turn instead of being structurally
    outranked by a graph that just wants to keep station with the school.
    """
    return [
        PolicyOverrideConsideration(),
        GraphBehaviorConsideration(),
        BallPursuitConsideration(),
        CodePolicyConsideration(),
        ComposableBehaviorConsideration(),
    ]
