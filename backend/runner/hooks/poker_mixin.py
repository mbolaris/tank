"""Poker functionality mixin for world hooks.

This module provides a mixin class that adds poker event collection
and leaderboard functionality to world hooks that support poker gameplay.
"""

from typing import Any, List, Optional

from backend.state_payloads import (
    AutoEvaluateStatsPayload,
    PokerEventPayload,
    PokerLeaderboardEntryPayload,
)


class PokerMixin:
    """Mixin that provides poker event and leaderboard collection functionality.

    Add this mixin to any hooks class that needs to support poker
    game events and leaderboards.
    """

    def collect_poker_events(self, runner: Any) -> Optional[List[PokerEventPayload]]:
        """Collect poker events from the world engine.

        Args:
            runner: The SimulationRunner instance

        Returns:
            List of poker event payloads, or None if not available
        """
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

    def collect_poker_leaderboard(
        self, runner: Any
    ) -> Optional[List[PokerLeaderboardEntryPayload]]:
        """Collect poker leaderboard from world ecosystem.

        Args:
            runner: The SimulationRunner instance

        Returns:
            List of leaderboard entry payloads, or None if not available
        """
        if not hasattr(runner.world, "ecosystem"):
            return None

        if not hasattr(runner.world.ecosystem, "get_poker_leaderboard"):
            return None

        # Intentional: poker leaderboard only applies to fish agents in TankWorld v1
        fish_list = [
            e for e in runner.world.entities_list
            if getattr(e, 'snapshot_type', None) == "fish"
        ]
        try:
            leaderboard_data = runner.world.ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=10, sort_by="net_energy"
            )
            return [PokerLeaderboardEntryPayload(**entry) for entry in leaderboard_data]
        except Exception:
            return []

    def collect_auto_eval(self, runner: Any) -> Optional[AutoEvaluateStatsPayload]:
        """Collect auto-evaluation stats (placeholder for now).

        Args:
            runner: The SimulationRunner instance

        Returns:
            Auto-evaluation stats payload, or None if not available
        """
        return None
