"""Poker event management for simulation engines."""

from collections import deque
from typing import Any, Dict, List

from core.fish_poker import PokerInteraction


class PokerSystem:
    """Handle poker interactions and event history."""

    def __init__(self, engine, max_events: int) -> None:
        self.engine = engine
        self.poker_events: deque = deque(maxlen=max_events)

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle poker outcomes, including reproduction and event logging."""
        self.add_poker_event(poker)

        if (
            poker.result is not None
            and poker.result.reproduction_occurred
            and poker.result.offspring is not None
        ):
            self.engine.add_entity(poker.result.offspring)

    def _add_poker_event_to_history(
        self,
        winner_id: int,
        loser_id: int,
        winner_hand: str,
        loser_hand: str,
        energy_transferred: float,
        message: str,
    ) -> None:
        event = {
            "frame": self.engine.frame_count,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "winner_hand": winner_hand,
            "loser_hand": loser_hand,
            "energy_transferred": energy_transferred,
            "message": message,
        }
        self.poker_events.append(event)

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Add a poker event to the recent events list."""
        if poker.result is None:
            return

        result = poker.result
        num_players = len(result.player_ids)

        if result.winner_id == -1:
            hand1_desc = result.hand1.description if result.hand1 is not None else "Unknown"
            if num_players == 2:
                message = f"Fish #{poker.fish1.fish_id} vs Fish #{poker.fish2.fish_id} - TIE! ({hand1_desc})"
            else:
                player_list = ", ".join(f"#{pid}" for pid in result.player_ids)
                message = f"Fish {player_list} - TIE! ({hand1_desc})"
        else:
            winner_hand_obj = None
            for i, pid in enumerate(result.player_ids):
                if pid == result.winner_id:
                    winner_hand_obj = result.player_hands[i]
                    break
            winner_desc = winner_hand_obj.description if winner_hand_obj is not None else "Unknown"

            if num_players == 2:
                message = (
                    f"Fish #{result.winner_id} beats Fish #{result.loser_id} "
                    f"with {winner_desc}! (+{result.winner_actual_gain:.1f} energy)"
                )
            else:
                loser_list = ", ".join(f"#{lid}" for lid in result.loser_ids)
                message = (
                    f"Fish #{result.winner_id} beats Fish {loser_list} "
                    f"with {winner_desc}! (+{result.winner_actual_gain:.1f} energy)"
                )

        winner_hand_obj = result.hand1 if result.winner_id == poker.fish1.fish_id else result.hand2
        loser_hand_obj = result.hand2 if result.winner_id == poker.fish1.fish_id else result.hand1
        winner_hand_desc = winner_hand_obj.description if winner_hand_obj is not None else "Unknown"
        loser_hand_desc = loser_hand_obj.description if loser_hand_obj is not None else "Unknown"

        self._add_poker_event_to_history(
            result.winner_id,
            result.loser_id,
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
        """Record a poker event between a fish and a plant."""
        if fish_won:
            winner_id = fish_id
            loser_id = -3
            winner_hand = fish_hand
            loser_hand = plant_hand
            message = f"Fish #{fish_id} beats Plant #{plant_id} with {fish_hand}! (+{energy_transferred:.1f}⚡)"
        else:
            winner_id = -3
            loser_id = fish_id
            winner_hand = plant_hand
            loser_hand = fish_hand
            message = f"Plant #{plant_id} beats Fish #{fish_id} with {plant_hand}! (+{energy_transferred:.1f}⚡)"

        event = {
            "frame": self.engine.frame_count,
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

    def get_recent_poker_events(self, max_age_frames: int) -> List[Dict[str, Any]]:
        """Get recent poker events within a frame window."""
        return [
            event
            for event in self.poker_events
            if self.engine.frame_count - event["frame"] < max_age_frames
        ]
