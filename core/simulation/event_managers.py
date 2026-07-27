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
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, cast

from core.minigames.soccer.fish_stats import SoccerFishStatsTracker

if TYPE_CHECKING:
    from core.minigames.soccer.evaluator import SoccerMinigameOutcome


class SoccerEventManager:
    """Manages soccer minigame event storage and retrieval.

    Stores recent soccer outcomes in a bounded deque and tracks the latest
    live league match state for real-time rendering.

    Owns its own event stream so the engine need not carry soccer-specific
    methods; callers reach it via ``engine.soccer_events`` (ADR-011). A
    ``frame_provider`` lets it self-source the current frame, so callers use
    ``record_outcome``/``recent`` without threading ``frame_count`` through.
    """

    def __init__(
        self,
        max_events: int = 100,
        frame_provider: Callable[[], int] | None = None,
    ) -> None:
        self._events: deque[dict[str, object]] = deque(maxlen=max_events)
        self._league_live_state: dict[str, object] | None = None
        self._frame_provider = frame_provider or (lambda: 0)
        self._fish_stats = SoccerFishStatsTracker()

    def record_outcome(self, outcome: SoccerMinigameOutcome) -> None:
        """Record an outcome, sourcing the current frame from the provider."""
        self.add_outcome(self._frame_provider(), outcome)

    def recent(self, max_age_frames: int = 1800) -> list[dict[str, object]]:
        """Recent events within max_age_frames of the current frame."""
        return self.get_recent(self._frame_provider(), max_age_frames)

    def add_event(self, event: dict[str, object]) -> None:
        """Record a soccer match outcome event."""
        self._events.append(event)

    def fish_leaders(self, top_n: int = 10) -> list[dict[str, object]]:
        """Top-N per-fish soccer standings aggregated across matches."""
        return cast(list[dict[str, object]], self._fish_stats.leaders(top_n))

    def add_outcome(self, frame: int, outcome: SoccerMinigameOutcome) -> None:
        """Build and record an event dict from a soccer minigame outcome."""
        self._fish_stats.record(outcome)

        def stringify_keys(values: Mapping[Any, Any]) -> dict[str, object]:
            return {str(key): value for key, value in values.items()}

        event: dict[str, object] = {
            "frame": frame,
            "match_id": outcome.match_id,
            "match_counter": outcome.match_counter,
            "winner_team": outcome.winner_team,
            "score_left": outcome.score_left,
            "score_right": outcome.score_right,
            "frames": outcome.frames,
            "seed": outcome.seed,
            "selection_seed": outcome.selection_seed,
            "message": outcome.message,
            "rewarded": stringify_keys(dict(outcome.rewarded)),
            "entry_fees": stringify_keys(dict(outcome.entry_fees)),
            "energy_deltas": stringify_keys(dict(outcome.energy_deltas)),
            "repro_credit_deltas": stringify_keys(dict(outcome.repro_credit_deltas)),
            "teams": {
                "left": list(outcome.teams.get("left", [])),
                "right": list(outcome.teams.get("right", [])),
            },
            "last_goal": outcome.last_goal,
            "skipped": outcome.skipped,
            "skip_reason": outcome.skip_reason,
        }
        self.add_event(event)

    def get_recent(self, current_frame: int, max_age_frames: int = 1800) -> list[dict[str, object]]:
        """Get events within max_age_frames of current_frame."""
        return [
            e for e in self._events if current_frame - int(cast(int, e["frame"])) < max_age_frames
        ]

    @property
    def league_live_state(self) -> dict[str, object] | None:
        """The latest live league match state for rendering."""
        return self._league_live_state

    @league_live_state.setter
    def league_live_state(self, state: dict[str, object] | None) -> None:
        self._league_live_state = state
