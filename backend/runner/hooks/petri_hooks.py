"""Petri world hooks implementation.

This module provides the PetriWorldHooks class which handles petri dish-specific
features like circular physics constraints.
"""

import logging
from typing import Any

from backend.runner.hooks.tank_hooks import TankWorldHooks

logger = logging.getLogger(__name__)


class PetriWorldHooks(TankWorldHooks):
    """Hooks for Petri world mode.

    Inherits from TankWorldHooks because Petri is just a physics mod for Tank world,
    so it still needs all the fish/poker features. The main differences are:
    - Circular dish physics instead of rectangular bounds
    - Circular root spot manager instead of grid-based
    """

    def apply_physics_constraints(self, runner: Any) -> None:
        """Apply circular dish physics and clamp all entities inside."""
        from core.config.display import SCREEN_HEIGHT, SCREEN_WIDTH
        from core.worlds.petri.dish import PetriDish
        from core.worlds.petri.root_spots import CircularRootSpotManager

        # Create dish geometry matching PetriPack defaults
        rim_margin = 2.0
        radius = (min(SCREEN_WIDTH, SCREEN_HEIGHT) / 2) - rim_margin
        dish = PetriDish(
            cx=SCREEN_WIDTH / 2,
            cy=SCREEN_HEIGHT / 2,
            r=radius,
        )

        # Inject dish into environment for circular physics
        env = runner.engine.environment
        if env is not None:
            env.dish = dish

            # Install the circular boundary collision resolver
            # This is what Agent.handle_screen_edges() checks for
            def resolve_boundary_collision(agent: Any) -> bool:
                """Resolve collision with the circular dish boundary."""
                if dish is None:
                    return False
                if not hasattr(agent, "vel"):
                    return False

                # Calculate agent center and radius
                agent_r = max(agent.width, getattr(agent, "height", agent.width)) / 2
                agent_cx = agent.pos.x + agent.width / 2
                agent_cy = agent.pos.y + getattr(agent, "height", agent.width) / 2

                # Use dish to clamp and reflect
                new_cx, new_cy, new_vx, new_vy, collided = dish.clamp_and_reflect(
                    agent_cx,
                    agent_cy,
                    agent.vel.x,
                    agent.vel.y,
                    agent_r,
                )

                if collided:
                    # Update agent position (convert center back to top-left)
                    agent.pos.x = new_cx - agent.width / 2
                    agent.pos.y = new_cy - getattr(agent, "height", agent.width) / 2
                    if hasattr(agent, "rect"):
                        agent.rect.x = agent.pos.x
                        agent.rect.y = agent.pos.y

                    # Update velocity
                    agent.vel.x = new_vx
                    agent.vel.y = new_vy

                return True  # Always handled (circular boundary is authoritative)

            env.resolve_boundary_collision = resolve_boundary_collision

            logger.info(
                "Petri physics applied: dish(cx=%.0f, cy=%.0f, r=%.0f) + boundary resolver",
                dish.cx,
                dish.cy,
                dish.r,
            )

        # Clamp all entities inside the dish
        self._clamp_entities_to_dish(runner, dish)

        # Swap RootSpotManager to CircularRootSpotManager
        if runner.engine.plant_manager:
            # Create new manager
            new_manager = CircularRootSpotManager(dish, rng=runner.engine.rng)
            runner.engine.plant_manager.root_spot_manager = new_manager
            logger.info("Swapped to CircularRootSpotManager")

            # Relocate existing plants to new perimeter spots
            self._relocate_plants_to_spots(runner, new_manager)

    def cleanup_physics(self, runner: Any) -> None:
        """Remove circular dish physics and boundary resolver."""
        env = runner.engine.environment
        if env is not None:
            env.dish = None
            # Remove the boundary collision resolver so Agent.handle_screen_edges()
            # falls back to rectangular bounds
            if hasattr(env, "resolve_boundary_collision"):
                env.resolve_boundary_collision = None
            logger.info("Petri physics removed: rectangular bounds restored")

    def on_world_type_switch(self, runner: Any, old_type: str, new_type: str) -> None:
        """Handle transition into Petri mode.

        Note: apply_physics_constraints is called by switch_world_type before
        this method, so we don't need to call it again here.
        """
        # Physics are already applied by switch_world_type; this hook is for
        # any additional post-switch cleanup or notifications.
        pass

    def _clamp_entities_to_dish(self, runner: Any, dish: Any) -> None:
        """Reposition all agents to be inside the circular dish."""
        clamped_count = 0
        for entity in runner.engine.entities_list:
            if not hasattr(entity, "pos"):
                continue

            # Calculate agent center and radius
            agent_r = max(entity.width, getattr(entity, "height", entity.width)) / 2
            agent_cx = entity.pos.x + entity.width / 2
            agent_cy = entity.pos.y + getattr(entity, "height", entity.width) / 2

            # Get velocity (use 0,0 for static entities like GoalZone)
            vel_x = getattr(entity.vel, "x", 0.0) if hasattr(entity, "vel") else 0.0
            vel_y = getattr(entity.vel, "y", 0.0) if hasattr(entity, "vel") else 0.0

            # Clamp inside dish
            new_cx, new_cy, new_vx, new_vy, collided = dish.clamp_and_reflect(
                agent_cx,
                agent_cy,
                vel_x,
                vel_y,
                agent_r,
            )

            if collided:
                entity.pos.x = new_cx - entity.width / 2
                entity.pos.y = new_cy - getattr(entity, "height", entity.width) / 2
                # Only update velocity if entity has it
                if hasattr(entity, "vel"):
                    entity.vel.x = new_vx
                    entity.vel.y = new_vy
                if hasattr(entity, "rect"):
                    entity.rect.x = entity.pos.x
                    entity.rect.y = entity.pos.y
                clamped_count += 1

        if clamped_count > 0:
            logger.info("Clamped %d entities inside petri dish boundary", clamped_count)
