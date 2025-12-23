"""Debug tracing utilities wired through the EventBus."""

import time
from collections import defaultdict
from typing import Any, Callable, Dict, List

from core.events import (
    EntityBornEvent,
    EntityDiedEvent,
    EventBus,
    PhaseTransitionEvent,
    PokerGameEvent,
)


class DebugTraceSink:
    """Collects lightweight trace data from simulation events.

    Records:
        - Phase timings (start/end)
        - Birth/death counters
        - Poker outcomes (winner/loser summaries)
    """

    def __init__(self, event_bus: EventBus) -> None:
        self.phase_timings: Dict[str, List[float]] = defaultdict(list)
        self.lifecycle_counts: Dict[str, int] = defaultdict(int)
        self.poker_outcomes: List[Dict[str, Any]] = []
        self._start_times: Dict[str, float] = {}
        self._unsubscribes: List[Callable[[], None]] = []
        self._attach(event_bus)

    def _attach(self, event_bus: EventBus) -> None:
        self._unsubscribes.append(event_bus.subscribe(PhaseTransitionEvent, self._on_phase_event))
        self._unsubscribes.append(event_bus.subscribe(EntityBornEvent, self._on_entity_born))
        self._unsubscribes.append(event_bus.subscribe(EntityDiedEvent, self._on_entity_died))
        self._unsubscribes.append(event_bus.subscribe(PokerGameEvent, self._on_poker_event))

    def close(self) -> None:
        """Unsubscribe from all events."""
        for unsubscribe in self._unsubscribes:
            unsubscribe()
        self._unsubscribes.clear()

    def _on_phase_event(self, event: PhaseTransitionEvent) -> None:
        if event.status == "start":
            self._start_times[event.phase] = time.perf_counter()
        elif event.status == "end":
            start = self._start_times.pop(event.phase, None)
            if start is not None:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                self.phase_timings[event.phase].append(elapsed_ms)

    def _on_entity_born(self, event: EntityBornEvent) -> None:
        key = f"{event.entity_type}_born"
        self.lifecycle_counts[key] += 1

    def _on_entity_died(self, event: EntityDiedEvent) -> None:
        key = f"{event.entity_type}_died"
        self.lifecycle_counts[key] += 1

    def _on_poker_event(self, event: PokerGameEvent) -> None:
        self.poker_outcomes.append(
            {
                "frame": event.frame,
                "winner_id": event.winner_id,
                "winner_type": event.winner_type,
                "loser_ids": event.loser_ids,
                "loser_types": event.loser_types,
                "energy_transferred": event.energy_transferred,
                "is_tie": event.is_tie,
                "house_cut": event.house_cut,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize collected trace data."""
        return {
            "phase_timings_ms": {
                phase: {
                    "count": len(samples),
                    "avg_ms": sum(samples) / len(samples) if samples else 0.0,
                    "samples": samples,
                }
                for phase, samples in self.phase_timings.items()
            },
            "lifecycle_counts": dict(self.lifecycle_counts),
            "poker_outcomes": self.poker_outcomes,
        }
