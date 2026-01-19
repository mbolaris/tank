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
            logger.info(
                "Petri physics applied: dish(cx=%.0f, cy=%.0f, r=%.0f)",
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
        """Remove circular dish physics."""
        env = runner.engine.environment
        if env is not None:
            env.dish = None
            logger.info("Petri physics removed: rectangular bounds restored")

    def on_world_type_switch(self, runner: Any, old_type: str, new_type: str) -> None:
        """Handle transition into Petri mode."""
        if new_type == "petri":
            self.apply_physics_constraints(runner)

    def _clamp_entities_to_dish(self, runner: Any, dish: Any) -> None:
        """Reposition all agents to be inside the circular dish."""
        clamped_count = 0
        for entity in runner.engine.entities_list:
            if not hasattr(entity, "pos") or not hasattr(entity, "vel"):
                continue

            # Calculate agent center and radius
            agent_r = max(entity.width, getattr(entity, "height", entity.width)) / 2
            agent_cx = entity.pos.x + entity.width / 2
            agent_cy = entity.pos.y + getattr(entity, "height", entity.width) / 2

            # Clamp inside dish
            new_cx, new_cy, new_vx, new_vy, collided = dish.clamp_and_reflect(
                agent_cx,
                agent_cy,
                entity.vel.x,
                entity.vel.y,
                agent_r,
            )

            if collided:
                entity.pos.x = new_cx - entity.width / 2
                entity.pos.y = new_cy - getattr(entity, "height", entity.width) / 2
                entity.vel.x = new_vx
                entity.vel.y = new_vy
                if hasattr(entity, "rect"):
                    entity.rect.x = entity.pos.x
                    entity.rect.y = entity.pos.y
                clamped_count += 1

        if clamped_count > 0:
            logger.info("Clamped %d entities inside petri dish boundary", clamped_count)
