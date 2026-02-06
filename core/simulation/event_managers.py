"""Event managers for simulation subsystem events.

These classes encapsulate event storage and retrieval for specific subsystems,
following the same pattern used by PokerSystem for poker events. By extracting
event management from the engine, we:

1. Reduce the engine's responsibility surface (it was a God Object)
2. Make event schemas explicit and type-safe
3. Allow subsystems to evolve their event formats independently
"""

from __future__ import annotations

from collections import deque
from typing import Any


class SoccerEventManager:
    """Manages soccer minigame event storage and retrieval.

    Stores recent soccer outcomes in a bounded deque and tracks the latest
    live league match state for real-time rendering.
    """

    def __init__(self, max_events: int = 100) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._league_live_state: dict[str, Any] | None = None

    def add_event(self, event: dict[str, Any]) -> None:
        """Record a soccer match outcome event."""
        self._events.append(event)

    def get_recent(self, current_frame: int, max_age_frames: int = 1800) -> list[dict[str, Any]]:
        """Get events within max_age_frames of current_frame."""
        return [e for e in self._events if current_frame - e["frame"] < max_age_frames]

    @property
    def league_live_state(self) -> dict[str, Any] | None:
        """The latest live league match state for rendering."""
        return self._league_live_state

    @league_live_state.setter
    def league_live_state(self, state: dict[str, Any] | None) -> None:
        self._league_live_state = state
