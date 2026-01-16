"""Tank world mode pack implementation.

This pack encapsulates the specific systems, environment, and entity seeding
logic for the standard fish tank simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.config.simulation_config import SimulationConfig
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

    Also initializes soccer components (ball, goals) if configured.
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
        """Register Tank systems including soccer system.

        Extends parent implementation to add soccer system.
        """
        # Call parent to register all standard systems
        super().register_systems(engine)

        # Add soccer system (optional, for ball and goal management)
        try:
            from core.systems.soccer_system import SoccerSystem

            soccer_system = SoccerSystem(engine)
            engine.soccer_system = soccer_system
            engine._system_registry.register(soccer_system)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to register soccer system: {e}")

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

    def seed_entities(self, engine: SimulationEngine) -> None:
        """Create initial entities including ball and goals.

        Extends parent implementation to initialize soccer components.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Call parent to create fish and plants
        super().seed_entities(engine)

        # Initialize soccer components (ball and goals)
        self._initialize_soccer(engine, logger)

    def _initialize_soccer(self, engine: SimulationEngine, logger) -> None:
        """Initialize ball and goal zones if enabled in config.

        Args:
            engine: The simulation engine
            logger: Logger instance
        """
        try:
            from core.entities.ball import Ball
            from core.entities.goal_zone import GoalZone, GoalZoneManager

            if not engine.environment:
                return

            # Check if soccer is enabled (default: False to preserve existing behavior)
            soccer_enabled = False
            if hasattr(self.config, "tank") and hasattr(self.config.tank, "soccer_enabled"):
                soccer_enabled = self.config.tank.soccer_enabled

            if not soccer_enabled:
                logger.info("Soccer components disabled in config")
                return

            # Get field dimensions
            width = engine.environment.width
            height = engine.environment.height
            mid_y = height / 2

            # Create ball at center
            ball = Ball(
                environment=engine.environment,
                x=width / 2,
                y=mid_y,
                decay_rate=0.94,
                max_speed=3.0,
                size=0.085,
                kickable_margin=0.7,
                kick_power_rate=0.027,
            )
            engine.request_spawn(ball)

            # Create goal manager
            goal_manager = GoalZoneManager()

            # Create goals (one for each team)
            goal_left = GoalZone(
                environment=engine.environment,
                x=50,
                y=mid_y,
                team="A",
                goal_id="goal_left",
                radius=15.0,
                base_energy_reward=100.0,
            )
            engine.request_spawn(goal_left)
            goal_manager.register_zone(goal_left)

            goal_right = GoalZone(
                environment=engine.environment,
                x=width - 50,
                y=mid_y,
                team="B",
                goal_id="goal_right",
                radius=15.0,
                base_energy_reward=100.0,
            )
            engine.request_spawn(goal_right)
            goal_manager.register_zone(goal_right)

            # Store references on environment
            engine.environment.ball = ball
            engine.environment.goal_manager = goal_manager

            # Setup soccer system to use them
            if hasattr(engine, "soccer_system") and engine.soccer_system:
                engine.soccer_system.set_ball(ball)
                engine.soccer_system.set_goal_manager(goal_manager)

            logger.info("Soccer components initialized: ball and goal zones")

        except Exception as e:
            # Log error but don't crash - soccer is optional
            logger.warning(f"Failed to initialize soccer components: {e}")
