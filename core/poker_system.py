"""Poker event management system for simulation engines.

This module handles poker interactions and event history tracking.
The system extends BaseSystem for consistent interface and lifecycle management.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.INTERACTION
- Manages poker event history with configurable max size
- Tracks poker statistics for debugging and analysis
"""

from collections import deque
from typing import TYPE_CHECKING, Any, Dict, List

from core.poker_interaction import FishPokerInteraction as PokerInteraction
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine


@runs_in_phase(UpdatePhase.INTERACTION)
class PokerSystem(BaseSystem):
    """Handle poker interactions and event history.

    This system runs in the INTERACTION phase and manages:
    - Poker event history for UI display
    - Poker result processing (energy transfer, reproduction)
    - Statistics tracking for debugging

    Attributes:
        poker_events: Deque of recent poker events (capped at max_events)
        _games_played: Total number of poker games played
        _total_energy_transferred: Total energy transferred via poker
    """

    def __init__(self, engine: "SimulationEngine", max_events: int = 100) -> None:
        """Initialize the poker system.

        Args:
            engine: The simulation engine
            max_events: Maximum number of poker events to keep in history
        """
        super().__init__(engine, "Poker")
        self.poker_events: deque = deque(maxlen=max_events)
        self._max_events = max_events
        self._games_played: int = 0
        self._total_energy_transferred: float = 0.0
        self._fish_wins: int = 0
        self._plant_wins: int = 0
        self._ties: int = 0

    def _do_update(self, frame: int) -> SystemResult:
        """Poker system doesn't have per-frame logic.

        Poker games are triggered by collision/proximity detection
        in the collision system. This method exists for interface
        consistency but performs no action.

        Args:
            frame: Current simulation frame number

        Returns:
            Empty SystemResult (poker is event-driven, not frame-driven)
        """
        return SystemResult.empty()

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle poker outcomes, including event logging.

        Args:
            poker: The completed poker interaction
        """
        self.add_poker_event(poker)
        # Note: Reproduction is now handled separately by the simulator,
        # not via poker result fields

    def _add_poker_event_to_history(
        self,
        winner_id: int,
        loser_id: int,
        winner_hand: str,
        loser_hand: str,
        energy_transferred: float,
        message: str,
    ) -> None:
        """Add a poker event to the history.

        Args:
            winner_id: ID of the winning entity
            loser_id: ID of the losing entity
            winner_hand: Description of winner's hand
            loser_hand: Description of loser's hand
            energy_transferred: Amount of energy transferred
            message: Human-readable message describing the outcome
        """
        event = {
            "frame": self._engine.frame_count,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "winner_hand": winner_hand,
            "loser_hand": loser_hand,
            "energy_transferred": energy_transferred,
            "message": message,
        }
        self.poker_events.append(event)
        self._games_played += 1
        self._total_energy_transferred += energy_transferred

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Add a poker event to the recent events list.

        Args:
            poker: The completed poker interaction
        """
        if poker.result is None:
            return

        result = poker.result
        # Get player count from poker.players (MixedPokerInteraction stores players list)
        num_players = len(poker.players) if hasattr(poker, 'players') else 2

        if result.winner_id == -1 or result.is_tie:
            # Tie - use winner_hand or first loser_hand for description
            hand_desc = result.winner_hand.description if result.winner_hand else "Unknown"
            if num_players == 2:
                p1_id = poker.players[0].get_poker_id() if hasattr(poker.players[0], 'get_poker_id') else 0
                p2_id = poker.players[1].get_poker_id() if hasattr(poker.players[1], 'get_poker_id') else 0
                message = f"Fish #{p1_id} vs Fish #{p2_id} - TIE! ({hand_desc})"
            else:
                player_list = ", ".join(f"#{p.get_poker_id()}" for p in poker.players)
                message = f"Fish {player_list} - TIE! ({hand_desc})"
            self._ties += 1
        else:
            # Use winner_hand from result
            winner_desc = result.winner_hand.description if result.winner_hand else "Unknown"

            if num_players == 2:
                message = (
                    f"Fish #{result.winner_id} beats Fish #{result.loser_ids[0] if result.loser_ids else 0} "
                    f"with {winner_desc}! (+{result.energy_transferred:.1f} energy)"
                )
            else:
                loser_list = ", ".join(f"#{lid}" for lid in result.loser_ids)
                message = (
                    f"Fish #{result.winner_id} beats Fish {loser_list} "
                    f"with {winner_desc}! (+{result.energy_transferred:.1f} energy)"
                )
            self._fish_wins += 1

        # Get winner and loser hand descriptions
        winner_hand_desc = result.winner_hand.description if result.winner_hand else "Unknown"
        loser_hand_desc = result.loser_hands[0].description if result.loser_hands and result.loser_hands[0] else "Unknown"

        self._add_poker_event_to_history(
            result.winner_id,
            result.loser_ids[0] if result.loser_ids else -1,
            winner_hand_desc,
            loser_hand_desc,
            result.energy_transferred,
            message,
        )

    def add_plant_poker_event(
        self,
        fish_id: int,
        plant_id: int,
        fish_won: bool,
        fish_hand: str,
        plant_hand: str,
        energy_transferred: float,
    ) -> None:
        """Record a poker event between a fish and a plant.

        Args:
            fish_id: ID of the fish player
            plant_id: ID of the plant player
            fish_won: True if fish won, False if plant won
            fish_hand: Description of fish's hand
            plant_hand: Description of plant's hand
            energy_transferred: Amount of energy transferred
        """
        if fish_won:
            winner_id = fish_id
            loser_id = -3  # Sentinel for plant
            winner_hand = fish_hand
            loser_hand = plant_hand
            message = f"Fish #{fish_id} beats Plant #{plant_id} with {fish_hand}! (+{energy_transferred:.1f}⚡)"
            self._fish_wins += 1
        else:
            winner_id = -3
            loser_id = fish_id
            winner_hand = plant_hand
            loser_hand = fish_hand
            message = f"Plant #{plant_id} beats Fish #{fish_id} with {plant_hand}! (+{energy_transferred:.1f}⚡)"
            self._plant_wins += 1

        event = {
            "frame": self._engine.frame_count,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "winner_hand": winner_hand,
            "loser_hand": loser_hand,
            "energy_transferred": energy_transferred,
            "message": message,
            "is_plant": True,
            "plant_id": plant_id,
        }

        self.poker_events.append(event)
        self._games_played += 1
        self._total_energy_transferred += energy_transferred

    def get_recent_poker_events(self, max_age_frames: int) -> List[Dict[str, Any]]:
        """Get recent poker events within a frame window.

        Args:
            max_age_frames: Maximum age of events to include (in frames)

        Returns:
            List of poker events within the specified time window
        """
        return [
            event
            for event in self.poker_events
            if self._engine.frame_count - event["frame"] < max_age_frames
        ]

    def get_debug_info(self) -> Dict[str, Any]:
        """Return poker statistics for debugging.

        Returns:
            Dictionary containing system state and statistics
        """
        return {
            **super().get_debug_info(),
            "games_played": self._games_played,
            "total_energy_transferred": self._total_energy_transferred,
            "fish_wins": self._fish_wins,
            "plant_wins": self._plant_wins,
            "ties": self._ties,
            "events_in_history": len(self.poker_events),
            "max_events": self._max_events,
            "avg_energy_per_game": (
                self._total_energy_transferred / self._games_played
                if self._games_played > 0
                else 0.0
            ),
        }
