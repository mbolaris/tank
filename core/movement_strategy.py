"""Movement strategies for fish agents.

This module provides movement behaviors for fish:
- AlgorithmicMovement: Parametrizable behavior algorithms that evolve
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Tuple

from core.collision_system import default_collision_detector
from core.config.fish import (
    RANDOM_MOVE_PROBABILITIES,
    RANDOM_VELOCITY_DIVISOR,
)
from core.entities import Food
from core.math_utils import Vector2
from core.policies.interfaces import MovementAction, build_movement_observation

if TYPE_CHECKING:
    from core.code_pool import GenomeCodePool
    from core.entities import Fish

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
        policy_kind = getattr(fish.genome.behavioral, "code_policy_kind", None)
        component_id = getattr(fish.genome.behavioral, "code_policy_component_id", None)
        policy_params = getattr(fish.genome.behavioral, "code_policy_params", None)
        if hasattr(policy_kind, "value"):
            policy_kind = policy_kind.value
        if hasattr(component_id, "value"):
            component_id = component_id.value
        if hasattr(policy_params, "value"):
            policy_params = policy_params.value
        if policy_kind != "movement_policy" or not component_id:
            return None

        # Try GenomeCodePool first (preferred), then fall back to CodePool
        genome_code_pool = getattr(fish.environment, "genome_code_pool", None)
        if genome_code_pool is not None:
            return self._execute_via_genome_pool(
                fish, genome_code_pool, component_id, policy_params
            )

        # Fall back to basic CodePool
        code_pool = getattr(fish.environment, "code_pool", None)
        if code_pool is None:
            return None

        func = code_pool.get_callable(component_id)
        if func is None:
            return None

        observation = build_movement_observation(fish)
        try:
            output = func(observation, fish.environment.rng)
        except Exception as exc:  # pragma: no cover - defensive guard
            self._log_policy_error(fish, component_id, "exception in policy", exc)
            return None

        parsed = self._parse_policy_output(output)
        if parsed is None:
            self._log_policy_error(fish, component_id, "invalid movement output")
            return None

        return parsed

    def _execute_via_genome_pool(
        self,
        fish: Fish,
        genome_pool: GenomeCodePool,
        component_id: str,
        params: dict | None,
    ) -> VelocityComponents | None:
        """Execute policy via GenomeCodePool with safety and determinism.

        The GenomeCodePool provides:
        - Explicit dt (delta time) for determinism
        - Output clamping for safety
        - Error handling and logging
        """
        from core.code_pool import GenomePolicySet

        # Build policy set from genome
        policy_set = GenomePolicySet()
        policy_set.set_policy("movement_policy", component_id, params)

        # Build observation with dt for determinism
        observation = build_movement_observation(fish)

        # Get dt from environment if available (default to 1.0)
        dt = getattr(fish.environment, "dt", 1.0)

        # Execute with safety checks
        vx, vy = genome_pool.execute_movement_policy(
            policy_set=policy_set,
            observation=observation,
            rng=fish.environment.rng,
            dt=dt,
        )

        if vx == 0.0 and vy == 0.0:
            # Check if this was an error (policy returned nothing useful)
            return None

        return (vx, vy)

    def _parse_policy_output(self, output: object) -> VelocityComponents | None:
        if isinstance(output, MovementAction):
            vx, vy = output.vx, output.vy
        elif isinstance(output, Vector2):
            vx, vy = output.x, output.y
        elif isinstance(output, (tuple, list)) and len(output) == 2:
            vx, vy = output
        elif isinstance(output, dict) and "vx" in output and "vy" in output:
            vx, vy = output["vx"], output["vy"]
        else:
            return None

        try:
            vx = float(vx)
            vy = float(vy)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(vx) or not math.isfinite(vy):
            return None

        if abs(vx) > 1.0 or abs(vy) > 1.0:
            return None

        return vx, vy

    def _log_policy_error(
        self,
        fish: Fish,
        component_id: str,
        message: str,
        exc: Exception | None = None,
    ) -> None:
        fish_id = getattr(fish, "fish_id", id(fish))
        lifecycle = getattr(fish, "_lifecycle_component", None)
        age = getattr(lifecycle, "age", 0)
        last_logged = self._policy_error_last_log.get(fish_id, -self._policy_error_log_interval)
        if age - last_logged < self._policy_error_log_interval:
            return
        self._policy_error_last_log[fish_id] = age
        if exc is not None:
            logger.warning(
                "Movement policy %s failed for fish %s: %s",
                component_id,
                fish_id,
                message,
                exc_info=exc,
            )
        else:
            logger.warning(
                "Movement policy %s failed for fish %s: %s",
                component_id,
                fish_id,
                message,
            )
