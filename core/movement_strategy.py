"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Tuple

from core.collision_system import default_collision_detector
from core.config.fish import RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
from core.entities import Food
from core.math_utils import Vector2
from core.policies.interfaces import build_movement_observation

if TYPE_CHECKING:
    from core.entities import Fish

from core.actions.action_registry import translate_action

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

VelocityComponents = Tuple[float, float]


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

        for food in nearby_food:
            # Get the food entity (unwrap if it's a sprite wrapper)
            food_entity: Food = food._entity if hasattr(food, "_entity") else food

            # Use the collision detector for consistent collision detection
            if default_collision_detector.collides(sprite_entity, food_entity):
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

    def move(self, sprite: Fish) -> None:
        """Move using the fish's composable behavior.

        The composable behavior handles all sub-behaviors internally:
        threat response, food seeking, social behavior, and poker engagement.
        """
        sprite_entity: Fish = sprite._entity if hasattr(sprite, "_entity") else sprite
        genome = sprite_entity.genome

        # Priority 1: Check for explicit movement policy override
        if sprite_entity.movement_policy is not None:
            observation = build_movement_observation(sprite_entity)
            try:
                desired_velocity = sprite_entity.movement_policy(
                    observation, sprite_entity.environment.rng
                )
            except Exception:
                desired_velocity = None

            # If policy returned valid velocity, we use it directly
            # If it failed/returned None, we fall back to genome behavior below
        else:
            desired_velocity = None

        # Priority 2: Check for code policy in genome (if no override or override failed)
        if desired_velocity is None:
            desired_velocity = self._execute_policy_if_present(sprite_entity)

        # Priority 3: Check for standard behavior in genome
        if desired_velocity is None:
            composable_behavior = (
                genome.behavioral.behavior.value if genome.behavioral.behavior else None
            )

            if composable_behavior is None:
                # Fallback to simple random movement
                sprite_entity.add_random_velocity_change(
                    RANDOM_MOVE_PROBABILITIES, RANDOM_VELOCITY_DIVISOR
                )
                super().move(sprite_entity)
                return

            # Execute composable behavior - it handles all sub-behaviors internally
            desired_velocity = composable_behavior.execute(sprite_entity)

        # =========================================================================
        # CONTRACT ENFORCEMENT
        # =========================================================================
        # Convert raw decision (velocity) to canonical Action via Registry
        # This ensures all behaviors go through the standard translation layer.

        world_type = getattr(sprite_entity.environment, "world_type", "tank")

        # Translate to standardized Action
        # Note: desired_velocity is a tuple (vx, vy), which calls DefaultActionTranslator
        # to handle it correctly if no specific translator, or TankActionTranslator checks types.
        try:
            action = translate_action(
                world_type, str(getattr(sprite_entity, "fish_id", "unknown")), desired_velocity
            )
            # Use the translated velocity from the Action object
            desired_vx, desired_vy = action.target_velocity
        except Exception:
            # Fallback if translation fails (should not happen with defaults)
            desired_vx, desired_vy = desired_velocity

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

        # Execute via runner
        # run_movement_policy handles extracting the component_id from the genome
        return run_movement_policy(
            genome=fish.genome,
            code_pool=genome_code_pool,
            observation=observation,
            rng=fish.environment.rng,
            fish_id=getattr(fish, "fish_id", None),
        )
