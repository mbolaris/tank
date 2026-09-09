"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.collision_system import default_collision_detector
from core.config.fish import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
from core.entities import Food
from core.math_utils import Vector2
from core.movement.kinematics import (
    ALGORITHMIC_MAX_SPEED_MULTIPLIER,
    ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ,
    ALGORITHMIC_MOVEMENT_SMOOTHING,
    MAX_ACTION_VELOCITY,
    apply_movement_kinematics,
)
from core.policies.interfaces import build_movement_observation

if TYPE_CHECKING:
    from core.behavior.tank_adapter import ForagingIntentKind
    from core.entities import Fish

from core.movement.considerations import MovementArbiter, default_considerations
from core.movement.intents import MovementArbitration

logger = logging.getLogger(__name__)

# The kinematics constants above are re-exported: they were part of this
# module's public surface long before core.movement.kinematics existed, and
# backend/tool code still imports them from here.
__all__ = [
    "ALGORITHMIC_MAX_SPEED_MULTIPLIER",
    "ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ",
    "ALGORITHMIC_MOVEMENT_SMOOTHING",
    "MAX_ACTION_VELOCITY",
    "AlgorithmicMovement",
    "MovementStrategy",
    "VelocityComponents",
    "apply_movement_kinematics",
]


VelocityComponents = tuple[float, float]


class MovementStrategy:
    """Base class for movement strategies."""

    def move(self, fish: Fish) -> None:
        """Move a fish according to the strategy."""
        self.check_collision_with_food(fish)

    def check_collision_with_food(self, fish: Fish) -> None:
        """Check if the fish collides with food and stop it if so.

        Args:
            fish: The fish entity to check for collisions
        """
        # Optimize: Use spatial query to only check nearby food
        # Radius of 50 is sufficient for collision detection (fish size + food size)
        nearby_food = fish.environment.nearby_resources(fish, 50)

        for candidate in nearby_food:
            if not isinstance(candidate, Food):
                continue

            # Use the collision detector for consistent collision detection
            if default_collision_detector.collides(fish, candidate):
                # Only stop if the fish can actually consume food
                if not fish.can_eat():
                    continue
                fish.vel = Vector2(0, 0)  # Set velocity to 0


class AlgorithmicMovement(MovementStrategy):
    """Movement strategy controlled by composable behaviors.

    Fish use a ComposableBehavior that combines multiple sub-behaviors:
    - ThreatResponse: How to react to predators
    - FoodApproach: How to approach and capture food
    - SocialMode: How to interact with other fish
    - PokerEngagement: How to engage with poker opportunities

    This provides 384+ behavior combinations with tunable parameters,
    enabling much richer evolutionary exploration than the previous
    48 monolithic algorithms.

    Performance optimizations:
    - Pre-computed squared constant for speed comparison
    - Avoid sqrt when not needed
    - Inline velocity calculations
    """

    _policy_error_log_interval = 60
    _policy_error_last_log: dict[int, int] = {}

    def __init__(self) -> None:
        # Competing movement drives, resolved in priority order. The order is
        # DATA (the arbiter's list), not statement order spread through move().
        # See ADR-010 and core.movement.considerations.
        self._arbiter = MovementArbiter(default_considerations())
        self._last_arbitration = MovementArbitration(None)

    @property
    def last_arbitration(self) -> MovementArbitration:
        """Most recent decision, retained for the selected-fish inspector."""
        return self._last_arbitration

    def move(self, fish: Fish) -> None:
        """Move the fish by resolving its competing drives.

        Drives (explicit policy override, ball pursuit, genome code policy, and
        the composable behavior) are arbitrated by ``self._arbiter`` in priority
        order; the first active drive's desired velocity is used. If no drive
        fires (the genome has no composable behavior), fall back to random
        movement.
        """
        self._last_arbitration = self._arbiter.arbitrate(self, fish)
        selected_intent = self._last_arbitration.selected
        desired_velocity = selected_intent.velocity if selected_intent is not None else None

        if desired_velocity is None:
            # No drive produced a velocity (genome has no composable behavior):
            # fall back to simple random movement.
            fish.add_random_velocity_change(RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR)
            super().move(fish)
            return

        # Turn the winning drive's desired velocity into actual motion. This is
        # the internal fast path: on the composable-behavior path the
        # external-brain action-translation registry only re-applied the same
        # kinematic clamp (allocating an Action per fish per frame), so it is
        # bypassed here. External brains still translate through core.actions.
        apply_movement_kinematics(fish.vel, desired_velocity, fish.speed, fish.environment.rng)

        super().move(fish)

    def _get_policy_override_velocity(self, fish: Fish) -> VelocityComponents | None:
        """Explicit movement-policy override, if one is set on the fish.

        Returns the policy's velocity directly. Returns None when no policy is
        set or the policy raises (caller falls through to the next drive).
        """
        if fish.movement_policy is None:
            return None
        observation = build_movement_observation(fish)
        try:
            # movement_policy is typed Any; pin the declared return type so mypy
            # (3.10 CI) doesn't flag no-any-return.
            velocity: VelocityComponents | None = fish.movement_policy(
                observation, fish.environment.rng
            )
            return velocity
        except Exception:
            logger.debug(
                "Movement policy failed for fish %s, falling back to genome behavior",
                fish.fish_id,
                exc_info=True,
            )
            return None

    def _get_composable_velocity(self, fish: Fish) -> VelocityComponents | None:
        """Desired velocity from the genome's composable behavior.

        Returns None when the genome has no composable behavior, signaling the
        caller to fall back to random movement.
        """
        genome = fish.genome
        composable_behavior = (
            genome.behavioral.behavior.value if genome.behavioral.behavior else None
        )
        if composable_behavior is None:
            return None
        return composable_behavior.execute(fish)

    def _get_graph_decision(
        self, fish: Fish
    ) -> tuple[VelocityComponents, ForagingIntentKind] | None:
        """Evaluate a graph-backed controller when the experimental flag is on.

        Returns the desired velocity plus a classification of what the
        graph's fixed topology actually selected (threat / food / cohesion),
        so ``GraphBehaviorConsideration`` can decide whether this is
        survival-relevant (preempts soccer) or leisure-tier (yields to it).
        """
        config = fish.environment.simulation_config
        if config is None or not config.tank.graph_behavior_enabled:
            return None
        graph_trait = fish.genome.behavioral.behavior_graph
        graph = graph_trait.value if graph_trait is not None else None
        if graph is None:
            return None
        from core.behavior.tank_adapter import (
            build_tank_behavior_observation,
            classify_foraging_intent,
        )

        observation = build_tank_behavior_observation(fish)
        output = graph.compile_cached().evaluate(observation.values)
        if not isinstance(output, tuple) or len(output) != 2:
            logger.warning("Graph behavior for fish %s returned a non-vector", fish.fish_id)
            return None
        velocity = (float(output[0]), float(output[1]))
        return velocity, classify_foraging_intent(observation, graph)

    def _execute_policy_if_present(self, fish: Fish) -> VelocityComponents | None:
        """Execute movement policy from genome if configured.

        Delegates to the movement_policy_runner to handle:
        - Extraction of policy ID from genome
        - Safety checks and validation
        - Execution via GenomeCodePool
        """
        from core.policies.movement_policy_runner import run_movement_policy

        # OPTIMIZATION: Check if policy is configured before doing expensive setup
        # This avoids building observations (which runs spatial queries) for fish without policies
        trait = fish.genome.behavioral.movement_policy_id
        policy_id = trait.value if trait is not None else None
        if not policy_id:
            return None

        # We need a reference to a code pool
        genome_code_pool = fish.environment.genome_code_pool
        if genome_code_pool is None:
            return None

        # Build observation
        observation = build_movement_observation(fish)

        # Environments have no dt attribute: the simulation is fixed-timestep.
        env_dt = 1.0
        fish_frame = fish.age

        # Execute via runner
        # run_movement_policy handles extracting the component_id from the genome
        return run_movement_policy(
            genome=fish.genome,
            code_pool=genome_code_pool,
            observation=observation,
            rng=fish.environment.rng,
            fish_id=fish.fish_id,
            dt=env_dt,
            frame=fish_frame,
        )
