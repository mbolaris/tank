"""Tank world mode pack implementation.

This pack encapsulates the specific systems, environment, and entity seeding
logic for the standard fish tank simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.config.simulation_config import SimulationConfig
from core.entities.ball import Ball
from core.entities.goal_zone import GoalZone
from core.systems.soccer_system import SoccerSystem
from core.worlds.shared.identity import TankLikeEntityIdentityProvider
from core.worlds.shared.tank_like_pack_base import TankLikePackBase
from core.worlds.tank.movement_observations import register_tank_movement_observation_builder
from core.worlds.tank.tank_actions import register_tank_action_translator

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine
    from core.worlds.identity import EntityIdentityProvider


class TankPack(TankLikePackBase):
    """System pack for the standard Fish Tank simulation.

    Inherits shared Tank-like wiring from TankLikePackBase and provides
    Tank-specific mode_id, metadata, and identity provider.
    """

    def __init__(self, config: SimulationConfig):
        super().__init__(config)
        self._identity_provider = TankLikeEntityIdentityProvider()

    @property
    def mode_id(self) -> str:
        return "tank"

    def register_contracts(self, engine: SimulationEngine) -> None:
        """Register Tank-specific contracts."""
        register_tank_action_translator("tank")
        register_tank_movement_observation_builder("tank")

    def register_systems(self, engine: SimulationEngine) -> None:
        """Register Tank systems including soccer."""
        super().register_systems(engine)

        # Register Soccer System
        soccer = SoccerSystem(engine)
        engine.soccer_system = soccer  # Accessible reference
        engine._system_registry.register(soccer)

    def seed_entities(self, engine: SimulationEngine) -> None:
        """Seed initial entities including ball/goals."""
        super().seed_entities(engine)

        # Initialize Soccer Elements
        self._initialize_soccer(engine)

    def _initialize_soccer(self, engine: SimulationEngine) -> None:
        """Spawn ball and goals based on config settings."""
        # Check if tank practice mode is enabled
        soccer_cfg = self.config.soccer
        if not soccer_cfg.tank_practice_enabled:
            return  # Skip soccer initialization

        if not hasattr(engine, "soccer_system"):
            print("WARNING: No soccer system found in engine")
            return

        import logging

        logger = logging.getLogger(__name__)
        logger.info("SOCCER: Initializing soccer elements on fresh tank")

        env = engine.environment
        width = env.width
        height = env.height

        # 1. Spawn Ball (if visible)
        if soccer_cfg.tank_ball_visible:
            ball = Ball(env, width / 2, height / 2)
            engine.add_entity(ball)
            engine.soccer_system.register_ball(ball)
            logger.info(f"SOCCER: Ball spawned at ({width / 2}, {height / 2})")

        # 2. Spawn Goals (if visible)
        if soccer_cfg.tank_goals_visible:
            # Goal A (Left side)
            goal_a = GoalZone(env, 50.0, height / 2, "A")
            engine.add_entity(goal_a)
            engine.soccer_system.add_goal(goal_a)

            # Goal B (Right side)
            goal_b = GoalZone(env, width - 50.0, height / 2, "B")
            engine.add_entity(goal_b)
            engine.soccer_system.add_goal(goal_b)
            logger.info("SOCCER: Goals spawned (A and B)")

    def get_identity_provider(self) -> EntityIdentityProvider:
        """Return the Tank identity provider."""
        return self._identity_provider

    def get_metadata(self) -> dict[str, Any]:
        """Return Tank-specific metadata."""
        return {
            "world_type": "tank",
            "width": self.config.display.screen_width,
            "height": self.config.display.screen_height,
        }
