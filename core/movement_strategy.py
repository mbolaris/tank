"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from core.collision_system import default_collision_detector
from core.config.fish import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
from core.entities import Food
from core.math_utils import Vector2
from core.policies.interfaces import build_movement_observation

if TYPE_CHECKING:
    from core.entities import Fish

from core.movement.considerations import MovementArbiter, default_considerations

logger = logging.getLogger(__name__)

# Movement smoothing constants (lower = smoother, higher = more responsive)
# INCREASED from 0.02 to 0.10 - fish were too sluggish to catch food
# At 2% per frame, it took ~150 frames (5s) to reach target velocity
# At 10% per frame, it takes ~30 frames (1s) - much better for food pursuit
ALGORITHMIC_MOVEMENT_SMOOTHING = 0.10
ALGORITHMIC_MAX_SPEED_MULTIPLIER = 1.0  # Cap at base speed (was 0.6)
ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ = (
    ALGORITHMIC_MAX_SPEED_MULTIPLIER * ALGORITHMIC_MAX_SPEED_MULTIPLIER
)

# Kinematic action bound for tank-like worlds, mirroring
# TankLikeActionTranslator(max_velocity=5.0). The internal movement path clamps
# inline rather than round-tripping every fish every frame through the
# external-brain action-translation registry, which only re-applied this same
# clamp while allocating an Action object. The translation layer is still the
# correct seam for *external* brains; it is just not needed on the internal
# composable-behavior path. See ADR-007 (silent-fallback removal).
MAX_ACTION_VELOCITY = 5.0


def _clamp_action_velocity(value: float) -> float:
    """Clamp one velocity component to the kinematic action bound."""
    return max(-MAX_ACTION_VELOCITY, min(MAX_ACTION_VELOCITY, value))


VelocityComponents = tuple[float, float]


class MovementStrategy:
    """Base class for movement strategies."""

    def move(self, sprite: Fish) -> None:
        """Move a sprite according to the strategy."""
        self.check_collision_with_food(sprite)

    def check_collision_with_food(self, sprite: Fish) -> None:
        """Check if sprite collides with food and stop it if so.

        Args:
            sprite: The fish sprite to check for collisions
        """
        # Get the sprite entity (unwrap if it's a sprite wrapper)
        sprite_entity: Fish = sprite._entity if hasattr(sprite, "_entity") else sprite

        # Optimize: Use spatial query to only check nearby food
        # Radius of 50 is sufficient for collision detection (fish size + food size)
        # Use optimized nearby_resources query if available
        if hasattr(sprite.environment, "nearby_resources"):
            nearby_food = sprite.environment.nearby_resources(sprite_entity, 50)
        else:
            nearby_food = sprite.environment.nearby_agents_by_type(sprite_entity, 50, Food)

        for candidate in nearby_food:
            # Get the food entity (unwrap if it's a sprite wrapper)
            candidate_entity = candidate._entity if hasattr(candidate, "_entity") else candidate
            if not isinstance(candidate_entity, Food):
                continue
            food_entity = candidate_entity

            # Use the collision detector for consistent collision detection
            if default_collision_detector.collides(sprite_entity, food_entity):
                # Only stop if the fish can actually consume food
                if hasattr(sprite_entity, "can_eat") and not sprite_entity.can_eat():
                    continue
                sprite.vel = Vector2(0, 0)  # Set velocity to 0


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

    def move(self, sprite: Fish) -> None:
        """Move the fish by resolving its competing drives.

        Drives (explicit policy override, ball pursuit, genome code policy, and
        the composable behavior) are arbitrated by ``self._arbiter`` in priority
        order; the first active drive's desired velocity is used. If no drive
        fires (the genome has no composable behavior), fall back to random
        movement.
        """
        sprite_entity: Fish = sprite._entity if hasattr(sprite, "_entity") else sprite

        desired_velocity = self._arbiter.decide(self, sprite_entity)

        if desired_velocity is None:
            # No drive produced a velocity (genome has no composable behavior):
            # fall back to simple random movement.
            sprite_entity.add_random_velocity_change(
                RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
            )
            super().move(sprite_entity)
            return

        # Clamp the desired velocity to the kinematic action bound, then scale by
        # speed below. This is the internal fast path: on the composable-behavior
        # path the external-brain action-translation registry only re-applied this
        # same clamp (allocating an Action per fish per frame), so it is bypassed
        # here. External brains still translate through core.actions.
        desired_vx = _clamp_action_velocity(float(desired_velocity[0]))
        desired_vy = _clamp_action_velocity(float(desired_velocity[1]))

        # Apply algorithm decision - scale by speed to get actual velocity
        speed = sprite_entity.speed
        target_vx = desired_vx * speed
        target_vy = desired_vy * speed

        # Smoothly interpolate toward desired velocity - inline for performance
        vel = sprite_entity.vel
        vel.x += (target_vx - vel.x) * ALGORITHMIC_MOVEMENT_SMOOTHING
        vel.y += (target_vy - vel.y) * ALGORITHMIC_MOVEMENT_SMOOTHING

        # Normalize velocity to maintain consistent speed
        # Performance: Use squared comparison to avoid sqrt when not needed
        vel_x = vel.x
        vel_y = vel.y
        vel_length_sq = vel_x * vel_x + vel_y * vel_y

        # Anti-stuck mechanism: if velocity is very low, add small random nudge
        # This prevents fish from getting permanently stuck at (0,0)
        if vel_length_sq < 0.01:
            rng = sprite_entity.environment.rng
            angle = rng.random() * 6.283185307
            nudge_speed = speed * 0.3  # Small nudge to get unstuck
            vel.x = nudge_speed * math.cos(angle)
            vel.y = nudge_speed * math.sin(angle)
            vel_length_sq = vel.x * vel.x + vel.y * vel.y

        if vel_length_sq > 0:
            # Only normalize if speed exceeds max allowed
            max_speed_sq = speed * speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER_SQ
            if vel_length_sq > max_speed_sq:
                # Normalize and scale in one step
                max_speed = speed * ALGORITHMIC_MAX_SPEED_MULTIPLIER
                scale = max_speed / math.sqrt(vel_length_sq)
                vel.x = vel_x * scale
                vel.y = vel_y * scale

        super().move(sprite_entity)

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
                getattr(fish, "fish_id", "?"),
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
        behavioral = fish.genome.behavioral

        # Quick check: extract value and see if it's set
        trait = getattr(behavioral, "movement_policy_id", None)
        if trait is not None and hasattr(trait, "value"):
            trait = trait.value

        if not trait:
            return None

        # We need a reference to a code pool
        genome_code_pool = getattr(fish.environment, "genome_code_pool", None)

        if genome_code_pool is None:
            # Fallback to legacy behavior or just return None
            # If we really want to support raw CodePool without GenomeCodePool wrapper,
            # we'd need to adapt the runner or keep legacy logic.
            # Given the goal is "Use GenomeCodePool", we focus on that path.
            return None

        # Build observation
        observation = build_movement_observation(fish)

        # Extract explicit dt and frame for deterministic execution
        env_dt = getattr(fish.environment, "dt", 1.0)
        fish_frame = fish.age

        # Execute via runner
        # run_movement_policy handles extracting the component_id from the genome
        return run_movement_policy(
            genome=fish.genome,
            code_pool=genome_code_pool,
            observation=observation,
            rng=fish.environment.rng,
            fish_id=getattr(fish, "fish_id", None),
            dt=env_dt,
            frame=fish_frame,
        )
