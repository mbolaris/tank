"""Poker participant management system.

This module manages poker-specific state for fish without storing it directly
on the fish entities. This separation allows for cleaner code organization
and easier testing.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List

from core.poker.strategy.base import PokerStrategyEngine

if TYPE_CHECKING:
    from core.entities import Fish
    from core.fish.poker_stats_component import FishPokerStats


@dataclass
class PokerParticipant:
    """Tracks poker-specific state for a fish without storing it on the fish.

    This allows poker-specific data to be managed separately from the fish
    entity itself, following the separation of concerns principle.

    Attributes:
        fish: The fish entity this participant tracks
        strategy: The poker strategy engine for decision making
        stats: Poker statistics for this fish
        cooldown: Frames until fish can play poker again
        last_button_position: Last position at the table
        last_cooldown_age: Fish age when cooldown was last updated
    """

    fish: "Fish"
    strategy: PokerStrategyEngine
    stats: "FishPokerStats"
    cooldown: int = 0
    last_button_position: int = 0
    last_cooldown_age: int = 0

    def sync_with_age(self) -> None:
        """Reduce cooldown based on the fish's current age.

        This ensures cooldowns are reduced even if the fish isn't actively
        playing poker, by tracking how many frames have passed since the
        cooldown was last set.
        """
        age = getattr(self.fish, "age", 0)
        if age > self.last_cooldown_age:
            self.cooldown = max(0, self.cooldown - (age - self.last_cooldown_age))
            self.last_cooldown_age = age

    def start_cooldown(self, frames: int) -> None:
        """Start or extend the cooldown period.

        Args:
            frames: Number of frames to wait before playing again
        """
        self.sync_with_age()
        self.cooldown = max(self.cooldown, frames)
        self.last_cooldown_age = getattr(self.fish, "age", self.last_cooldown_age)

    def is_ready(self) -> bool:
        """Check if this participant is ready to play poker.

        Returns:
            True if off cooldown and ready to play
        """
        self.sync_with_age()
        return self.cooldown <= 0


class PokerParticipantManager:
    """Manages poker participants across the simulation.

    This class provides a centralized registry for poker participant state,
    handling creation, caching, and cleanup of participant data.

    The manager uses weak references conceptually - when a fish is removed
    from the simulation, its participant data can be garbage collected.
    """

    def __init__(self) -> None:
        """Initialize the participant manager."""
        self._participants: Dict[tuple[int | None, int], PokerParticipant] = {}

    @staticmethod
    def _participant_key(fish: "Fish") -> tuple[int | None, int]:
        """Build a stable participant key scoped to the fish's environment."""
        environment = getattr(fish, "environment", None)
        env_key = id(environment) if environment is not None else None
        fish_id = getattr(fish, "fish_id", None)
        if fish_id is None:
            fish_id = id(fish)
        return (env_key, int(fish_id))

    def get_participant(self, fish: "Fish") -> PokerParticipant:
        """Get or create the poker participant for a fish.

        Args:
            fish: The fish to get participant data for

        Returns:
            PokerParticipant with current state
        """
        from core.fish.poker_stats_component import FishPokerStats

        # Ensure fish has poker_stats
        if not hasattr(fish, "poker_stats") or fish.poker_stats is None:
            fish.poker_stats = FishPokerStats()

        # Use Python id() as key to ensure uniqueness across engines
        # (fish_id can collide between different simulation engines)
        fish_key = self._participant_key(fish)
        participant = self._participants.get(fish_key)
        if participant is None:
            participant = PokerParticipant(
                fish=fish,
                strategy=PokerStrategyEngine(fish),
                stats=fish.poker_stats,
                last_cooldown_age=getattr(fish, "age", 0),
            )
            self._participants[fish_key] = participant

        # Always update the stats reference in case the fish object was recreated/reloaded
        participant.stats = fish.poker_stats
        participant.fish = fish
        participant.sync_with_age()
        return participant

    def get_ready_participants(self, fish_list: List["Fish"]) -> List["Fish"]:
        """Get fish that are ready to play poker.

        Args:
            fish_list: List of fish to check

        Returns:
            List of fish that are off cooldown and ready to play
        """
        ready = []
        for fish in fish_list:
            participant = self.get_participant(fish)
            if participant.is_ready():
                ready.append(fish)
        return ready

    def set_cooldown(self, fish: "Fish", frames: int) -> None:
        """Set cooldown for a fish.

        Args:
            fish: The fish to set cooldown for
            frames: Number of frames to wait
        """
        participant = self.get_participant(fish)
        participant.start_cooldown(frames)

    def clear_participant(self, fish: "Fish") -> None:
        """Remove participant data for a fish.

        Args:
            fish: The fish to clear participant data for
        """
        self._participants.pop(self._participant_key(fish), None)

    def clear_all(self) -> None:
        """Clear all participant data."""
        self._participants.clear()

    @property
    def participant_count(self) -> int:
        """Get the number of tracked participants."""
        return len(self._participants)


# Global instance for backwards compatibility
# New code should consider using dependency injection instead
_global_manager = PokerParticipantManager()


def get_participant(fish: "Fish") -> PokerParticipant:
    """Get poker participant for a fish (convenience function).

    This function provides backwards compatibility with the original
    module-level function. New code should consider using a
    PokerParticipantManager instance directly.

    Args:
        fish: The fish to get participant data for

    Returns:
        PokerParticipant with current state
    """
    return _global_manager.get_participant(fish)


def get_ready_players(fish_list: List["Fish"], min_energy: float = 10.0) -> List["Fish"]:
    """Get fish that are ready to play poker (convenience function).

    Args:
        fish_list: List of fish to check
        min_energy: Minimum energy required to play

    Returns:
        List of fish ready to play poker
    """
    ready = []
    for fish in fish_list:
        participant = _global_manager.get_participant(fish)
        participant.sync_with_age()

        if fish.energy < min_energy:
            continue

        if participant.cooldown > 0:
            continue

        ready.append(fish)

    return ready
