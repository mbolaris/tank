"""World-specific feature hooks for the simulation runner.

This module defines how the universal SimulationRunner can be extended
with world-specific features like poker, benchmarking, and custom commands,
without embedding tank-specific assumptions into the core runner.

Each world type can provide hooks that the runner will call at appropriate
times to build state payloads, handle commands, and perform warmup/cleanup.
"""

from typing import Any, List, Optional, Protocol

from backend.state_payloads import (
    AutoEvaluateStatsPayload,
    PokerEventPayload,
    PokerLeaderboardEntryPayload,
)


class WorldHooks(Protocol):
    """Protocol for world-specific feature extensions.

    A world can optionally implement these hooks to add custom features
    to the runner without modifying the core runner logic.
    """

    def supports_command(self, command: str) -> bool:
        """Check if this world supports a specific command.

        Args:
            command: The command name to check

        Returns:
            True if the world can handle this command, False otherwise
        """
        ...

    def handle_command(self, runner: Any, command: str, data: dict) -> Optional[dict]:
        """Handle a world-specific command.

        Args:
            runner: The SimulationRunner instance
            command: The command name
            data: Command data/payload

        Returns:
            Response dict if handled, None to let runner handle it, or error dict
        """
        ...

    def build_world_extras(self, runner: Any) -> dict:
        """Build world-specific state extras (poker, leaderboards, etc).

        Args:
            runner: The SimulationRunner instance

        Returns:
            Dictionary of world-specific fields to merge into state payload
        """
        ...

    def warmup(self, runner: Any) -> None:
        """Optional warmup called once when runner starts.

        Args:
            runner: The SimulationRunner instance
        """
        ...

    def cleanup(self, runner: Any) -> None:
        """Optional cleanup called when runner stops.

        Args:
            runner: The SimulationRunner instance
        """
        ...


class NoOpWorldHooks:
    """Default no-op hooks for worlds that don't need special features."""

    def supports_command(self, command: str) -> bool:
        """No world-specific commands supported."""
        return False

    def handle_command(self, runner: Any, command: str, data: dict) -> Optional[dict]:
        """No command handling."""
        return None

    def build_world_extras(self, runner: Any) -> dict:
        """No extra state to add."""
        return {}

    def warmup(self, runner: Any) -> None:
        """No warmup needed."""
        pass

    def cleanup(self, runner: Any) -> None:
        """No cleanup needed."""
        pass


class TankWorldHooks:
    """Hooks for Tank world mode - provides poker, benchmarking, and tank-specific features.

    This encapsulates all tank-specific logic that was previously embedded
    in SimulationRunner, making it optional for other world types.
    """

    def __init__(self):
        """Initialize tank hooks."""
        self.human_poker_game: Optional[Any] = None
        self.standard_poker_series: Optional[Any] = None
        self.evolution_benchmark_tracker: Optional[Any] = None
        self._evolution_benchmark_guard: Optional[Any] = None
        self._evolution_benchmark_last_completed_time = 0.0

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

        # Collect poker events
        poker_events = self._collect_poker_events(runner)
        if poker_events is not None:
            extras["poker_events"] = poker_events

        # Collect poker leaderboard
        poker_leaderboard = self._collect_poker_leaderboard(runner)
        if poker_leaderboard is not None:
            extras["poker_leaderboard"] = poker_leaderboard

        # Collect auto-eval stats
        auto_eval = self._collect_auto_eval(runner)
        if auto_eval is not None:
            extras["auto_evaluation"] = auto_eval

        return extras

    def warmup(self, runner: Any) -> None:
        """Initialize tank-specific features."""
        import logging
        import os
        import threading
        from pathlib import Path

        logger = logging.getLogger(__name__)

        # Setup evolution benchmark tracker if enabled
        if os.getenv("TANK_EVOLUTION_BENCHMARK_ENABLED", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        ):
            try:
                from core.poker.evaluation.evolution_benchmark_tracker import (
                    EvolutionBenchmarkTracker,
                )

                # Write to shared benchmarks directory to avoid creating orphan tank directories
                export_path = (
                    Path("data") / "benchmarks" / f"poker_evolution_{runner.tank_id[:8]}.json"
                )
                self.evolution_benchmark_tracker = EvolutionBenchmarkTracker(
                    eval_interval_frames=int(
                        os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_FRAMES", "27000")
                    ),
                    export_path=export_path,
                    use_quick_benchmark=True,
                )
                self._evolution_benchmark_guard = threading.Lock()
                import time

                initial_delay = 60.0
                interval = float(os.getenv("TANK_EVOLUTION_BENCHMARK_INTERVAL_SECONDS", "900"))
                self._evolution_benchmark_last_completed_time = (
                    time.time() - interval + initial_delay
                )
                logger.info(
                    f"Evolution benchmark tracker initialized for tank {runner.tank_id[:8]}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize evolution benchmark tracker: {e}")
                self.evolution_benchmark_tracker = None
                self._evolution_benchmark_guard = None

    def cleanup(self, runner: Any) -> None:
        """Clean up tank-specific resources."""
        if self.human_poker_game is not None:
            self.human_poker_game = None
        if self.standard_poker_series is not None:
            self.standard_poker_series = None

    def update_benchmark_tracker_path(self, runner: Any) -> None:
        """Update benchmark tracker export path when tank identity changes."""
        if self.evolution_benchmark_tracker is not None:
            from pathlib import Path

            # Write to shared benchmarks directory to avoid creating orphan tank directories
            export_path = Path("data") / "benchmarks" / f"poker_evolution_{runner.tank_id[:8]}.json"
            self.evolution_benchmark_tracker.export_path = export_path

    # =========================================================================
    # Private methods
    # =========================================================================

    def _collect_poker_events(self, runner: Any) -> Optional[List[PokerEventPayload]]:
        """Collect poker events from the world engine."""
        if not hasattr(runner.world, "engine"):
            return None

        poker_events: List[PokerEventPayload] = []
        recent_events = runner.world.engine.poker_events
        for event in recent_events:
            if "Standard Algorithm" in event["message"] or "Auto-eval" in event["message"]:
                continue

            poker_events.append(
                PokerEventPayload(
                    frame=event["frame"],
                    winner_id=event["winner_id"],
                    loser_id=event["loser_id"],
                    winner_hand=event["winner_hand"],
                    loser_hand=event["loser_hand"],
                    energy_transferred=event["energy_transferred"],
                    message=event["message"],
                    is_plant=event.get("is_plant", False),
                    plant_id=event.get("plant_id", None),
                )
            )

        return poker_events

    def _collect_poker_leaderboard(
        self, runner: Any
    ) -> Optional[List[PokerLeaderboardEntryPayload]]:
        """Collect poker leaderboard from world ecosystem."""
        from core.entities import Fish

        if not hasattr(runner.world, "ecosystem"):
            return None

        if not hasattr(runner.world.ecosystem, "get_poker_leaderboard"):
            return None

        fish_list = [e for e in runner.world.entities_list if isinstance(e, Fish)]
        try:
            leaderboard_data = runner.world.ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=10, sort_by="net_energy"
            )
            return [PokerLeaderboardEntryPayload(**entry) for entry in leaderboard_data]
        except Exception:
            return []

    def _collect_auto_eval(self, runner: Any) -> Optional[AutoEvaluateStatsPayload]:
        """Collect auto-evaluation stats (placeholder for now)."""
        return None

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


def get_hooks_for_world(world_type: str) -> WorldHooks:
    """Factory function to get the appropriate hooks for a world type.

    Args:
        world_type: The type of world (tank, soccer_training, petri, etc)

    Returns:
        WorldHooks instance for the world type
    """
    if world_type == "tank":
        return TankWorldHooks()
    else:
        # All other worlds use no-op hooks
        return NoOpWorldHooks()
