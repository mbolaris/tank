"""Tank world hooks implementation.

This module provides the TankWorldHooks class which handles all tank-specific
features like poker, benchmarking, and tank-specific commands.
"""

import logging
from typing import Any, Optional

from backend.runner.hooks.benchmark_mixin import BenchmarkMixin
from backend.runner.hooks.poker_mixin import PokerMixin
from backend.runner.hooks.soccer_mixin import SoccerMixin

logger = logging.getLogger(__name__)


class TankWorldHooks(PokerMixin, SoccerMixin, BenchmarkMixin):
    """Hooks for Tank world mode - provides poker, benchmarking, and tank-specific features.

    This encapsulates all tank-specific logic that was previously embedded
    in SimulationRunner, making it optional for other world types.

    Inherits functionality from:
    - PokerMixin: Poker event and leaderboard collection
    - SoccerMixin: Soccer event and league state collection
    - BenchmarkMixin: Evolution benchmark tracking
    """

    def __init__(self):
        """Initialize tank hooks."""
        self.human_poker_game: Optional[Any] = None
        self.standard_poker_series: Optional[Any] = None
        # BenchmarkMixin attributes are initialized via its setup method

    def supports_command(self, command: str) -> bool:
        """Tank supports poker-related and benchmark commands."""
        tank_commands = {
            "start_human_poker",
            "stop_human_poker",
            "auto_evaluate_poker",
            "cancel_auto_evaluate",
        }
        return command in tank_commands

    def handle_command(self, runner: Any, command: str, data: dict) -> Optional[dict]:
        """Handle tank-specific commands.

        Args:
            runner: The SimulationRunner instance
            command: The command name
            data: Command data

        Returns:
            Response dict if handled, None otherwise
        """
        if command == "start_human_poker":
            return self._handle_start_human_poker(runner, data)
        elif command == "stop_human_poker":
            return self._handle_stop_human_poker(runner, data)
        elif command == "auto_evaluate_poker":
            return self._handle_auto_evaluate_poker(runner, data)
        elif command == "cancel_auto_evaluate":
            return self._handle_cancel_auto_evaluate(runner, data)
        return None

    def build_world_extras(self, runner: Any) -> dict:
        """Build tank-specific state extras (poker events, leaderboard, benchmarks)."""
        extras = {}

        # Collect poker events (from PokerMixin)
        poker_events = self.collect_poker_events(runner)
        if poker_events is not None:
            extras["poker_events"] = poker_events

        # Collect soccer events (from SoccerMixin)
        soccer_events = self.collect_soccer_events(runner)
        if soccer_events is not None:
            extras["soccer_events"] = soccer_events

        # Collect poker leaderboard (from PokerMixin)
        poker_leaderboard = self.collect_poker_leaderboard(runner)
        if poker_leaderboard is not None:
            extras["poker_leaderboard"] = poker_leaderboard

        # Collect auto-eval stats (from PokerMixin)
        auto_eval = self.collect_auto_eval(runner)
        if auto_eval is not None:
            extras["auto_evaluation"] = auto_eval

        # Collect soccer league live state (from SoccerMixin)
        soccer_league_live = self.collect_soccer_league_live(runner)
        if soccer_league_live is not None:
            extras["soccer_league_live"] = soccer_league_live

        return extras

    def warmup(self, runner: Any) -> None:
        """Initialize tank-specific features."""
        # Setup evolution benchmark tracker (from BenchmarkMixin)
        self.setup_benchmark_tracker(runner)

    def cleanup(self, runner: Any) -> None:
        """Clean up tank-specific resources."""
        if self.human_poker_game is not None:
            self.human_poker_game = None
        if self.standard_poker_series is not None:
            self.standard_poker_series = None
        self.cleanup_benchmark_tracker()

    def apply_physics_constraints(self, runner: Any) -> None:
        """Tank world uses standard rectangular bounds (handled by engine)."""
        pass

    def cleanup_physics(self, runner: Any) -> None:
        """Nothing to clean up for tank physics."""
        pass

    def on_world_type_switch(self, runner: Any, old_type: str, new_type: str) -> None:
        """Handle transition into Tank mode."""
        if new_type == "tank":
            self._restore_tank_manager(runner)
            self._restore_soccer_positions(runner)

    def _restore_soccer_positions(self, runner: Any) -> None:
        """Restore soccer goals and ball to their standard tank positions."""
        env = getattr(runner.engine, "environment", None)
        if not env:
            return

        # Restore Goal Positions
        if hasattr(env, "goal_manager") and env.goal_manager:
            width = env.width
            height = env.height
            mid_y = height / 2

            for zone in env.goal_manager.zones.values():
                if zone.goal_id == "goal_left":
                    zone.pos.x = 50.0
                    zone.pos.y = mid_y
                elif zone.goal_id == "goal_right":
                    zone.pos.x = width - 50.0
                    zone.pos.y = mid_y

                # Reset physics state (velocity/acceleration) to ensure it stays fixed
                if hasattr(zone, "vel"):
                    zone.vel.x = 0.0
                    zone.vel.y = 0.0
                if hasattr(zone, "acceleration"):
                    zone.acceleration.x = 0.0
                    zone.acceleration.y = 0.0

                # Reset stats too
                zone.reset_stats()

        # Restore Ball Position (center)
        if hasattr(env, "ball") and env.ball:
            cx = env.width / 2
            cy = env.height / 2
            env.ball.pos.x = cx
            env.ball.pos.y = cy
            env.ball.vel.x = 0
            env.ball.vel.y = 0
            env.ball.acceleration.x = 0
            env.ball.acceleration.y = 0
            env.ball.last_kicker = None

    def _restore_tank_manager(self, runner: Any) -> None:
        """Restore standard RootSpotManager."""
        from core.root_spots import RootSpotManager

        if not hasattr(runner.engine, "plant_manager") or not runner.engine.plant_manager:
            return

        # Create new manager
        width = 800
        height = 600
        if runner.engine.environment:
            width = runner.engine.environment.width
            height = runner.engine.environment.height

        new_manager = RootSpotManager(
            width,
            height,
            rng=runner.engine.rng,
        )
        runner.engine.plant_manager.root_spot_manager = new_manager
        logger.info("Swapped to standard RootSpotManager")

        # Relocate existing plants to new grid spots
        self._relocate_plants_to_spots(runner, new_manager)

    def _relocate_plants_to_spots(self, runner: Any, manager: Any) -> None:
        """Relocate all existing plants to valid spots in the new manager."""
        from core.entities import Plant
        from core.math_utils import Vector2

        # Get all plants
        if runner.engine.environment and runner.engine.environment.agents:
            plants = [e for e in runner.engine.environment.agents if isinstance(e, Plant)]
        else:
            plants = []
        if not plants:
            return

        # Clear old spots
        for plant in plants:
            if plant.root_spot:
                plant.root_spot.occupant = None
                plant.root_spot = None

        # Assign new spots
        count = 0
        for plant in plants:
            spot = manager.get_random_empty_spot()
            if spot:
                plant.root_spot = spot
                spot.claim(plant)
                # Physically move plant to the spot
                plant.pos = Vector2(spot.x, spot.y)
                plant.rect.x = spot.x
                plant.rect.y = spot.y
                count += 1

        logger.info("Relocated %d/%d plants to new root spots", count, len(plants))

    # =========================================================================
    # Command handlers
    # =========================================================================

    def _handle_start_human_poker(self, runner: Any, data: dict) -> dict:
        """Handle start_human_poker command."""
        return {"success": True, "message": "Human poker not yet implemented"}

    def _handle_stop_human_poker(self, runner: Any, data: dict) -> dict:
        """Handle stop_human_poker command."""
        return {"success": True, "message": "Human poker not yet implemented"}

    def _handle_auto_evaluate_poker(self, runner: Any, data: dict) -> dict:
        """Handle auto_evaluate_poker command."""
        return {"success": True, "message": "Auto-evaluate not yet implemented"}

    def _handle_cancel_auto_evaluate(self, runner: Any, data: dict) -> dict:
        """Handle cancel_auto_evaluate command."""
        return {"success": True, "message": "Cancel not yet implemented"}
