"""Energy accounting utilities for ecosystem statistics."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Optional, Tuple

from core.config.ecosystem import ENERGY_STATS_WINDOW_FRAMES


class EnergyTracker:
    """Tracks energy flow and snapshots for the ecosystem."""

    def __init__(self, *, window_maxlen: int = 2000, snapshot_interval: int = 1) -> None:
        self.frame_count: int = 0

        # Cumulative energy gains by source.
        self.energy_sources: Dict[str, float] = defaultdict(float)

        # Rolling per-frame energy gains.
        self.recent_energy_gains: deque[Tuple[int, Dict[str, float]]] = deque(
            maxlen=window_maxlen
        )
        self._current_frame_gains: Dict[str, float] = defaultdict(float)

        # Rolling per-frame energy burns.
        self.energy_burn: Dict[str, float] = defaultdict(float)
        self.recent_energy_burns: deque[Tuple[int, Dict[str, float]]] = deque(
            maxlen=window_maxlen
        )
        self._current_frame_burns: Dict[str, float] = defaultdict(float)

        # Plant energy tracking (separate pool).
        self.plant_energy_sources: Dict[str, float] = defaultdict(float)
        self.recent_plant_energy_gains: deque[Tuple[int, Dict[str, float]]] = deque(
            maxlen=window_maxlen
        )
        self._current_frame_plant_gains: Dict[str, float] = defaultdict(float)

        self.plant_energy_burn: Dict[str, float] = defaultdict(float)
        self.recent_plant_energy_burns: deque[Tuple[int, Dict[str, float]]] = deque(
            maxlen=window_maxlen
        )
        self._current_frame_plant_burns: Dict[str, float] = defaultdict(float)

        # Historical energy snapshots for true delta calculations.
        self.energy_history: deque[Tuple[int, float, int]] = deque(maxlen=window_maxlen)
        self._last_snapshot_frame: int = 0
        self._snapshot_interval: int = snapshot_interval

    def advance_frame(self, frame: int) -> None:
        """Flush per-frame buffers if we have moved to a new frame."""
        if self.frame_count < frame:
            if self._current_frame_gains:
                self.recent_energy_gains.append((self.frame_count, dict(self._current_frame_gains)))
                self._current_frame_gains.clear()

            if self._current_frame_burns:
                self.recent_energy_burns.append((self.frame_count, dict(self._current_frame_burns)))
                self._current_frame_burns.clear()

            if self._current_frame_plant_gains:
                self.recent_plant_energy_gains.append(
                    (self.frame_count, dict(self._current_frame_plant_gains))
                )
                self._current_frame_plant_gains.clear()

            if self._current_frame_plant_burns:
                self.recent_plant_energy_burns.append(
                    (self.frame_count, dict(self._current_frame_plant_burns))
                )
                self._current_frame_plant_burns.clear()

        self.frame_count = frame

    def record_energy_gain(self, source: str, amount: float) -> None:
        """Accumulate energy gains by source for downstream stats."""
        if amount == 0:
            return
        self.energy_sources[source] += amount
        self._current_frame_gains[source] += amount

    def record_energy_burn(self, source: str, amount: float) -> None:
        """Accumulate energy spent so we can prove metabolism/movement costs are applied."""
        if amount <= 0:  # Only record positive burns
            return
        self.energy_burn[source] += amount
        self._current_frame_burns[source] += amount

    def record_energy_delta(
        self, source: str, delta: float, *, negative_source: Optional[str] = None
    ) -> None:
        """Record a signed energy delta as either a gain or a burn."""
        if delta > 0:
            self.record_energy_gain(source, delta)
        elif delta < 0:
            self.record_energy_burn(negative_source or source, -delta)

    def record_energy_transfer(self, source: str, amount: float) -> None:
        """Record an internal transfer as both a gain and a burn (net zero)."""
        if amount == 0:
            return
        self.record_energy_gain(source, amount)
        self.record_energy_burn(source, amount)

    def record_plant_energy_gain(self, source: str, amount: float) -> None:
        """Accumulate plant energy gains by source for downstream stats."""
        if amount == 0:
            return
        self.plant_energy_sources[source] += amount
        self._current_frame_plant_gains[source] += amount

    def record_plant_energy_burn(self, source: str, amount: float) -> None:
        """Accumulate plant energy spent for downstream stats."""
        if amount == 0:
            return
        self.plant_energy_burn[source] += amount
        self._current_frame_plant_burns[source] += amount

    def record_plant_energy_delta(
        self, source: str, delta: float, *, negative_source: Optional[str] = None
    ) -> None:
        """Record a signed plant energy delta as either a gain or a burn."""
        if delta > 0:
            self.record_plant_energy_gain(source, delta)
        elif delta < 0:
            self.record_plant_energy_burn(negative_source or source, -delta)

    def record_plant_energy_transfer(self, source: str, amount: float) -> None:
        """Record a plant internal transfer as both a gain and a burn (net zero)."""
        if amount == 0:
            return
        self.record_plant_energy_gain(source, amount)
        self.record_plant_energy_burn(source, amount)

    def get_energy_source_summary(self) -> Dict[str, float]:
        """Return a snapshot of accumulated energy gains."""
        return dict(self.energy_sources)

    def get_plant_energy_source_summary(self) -> Dict[str, float]:
        """Return a snapshot of accumulated plant energy gains."""
        return dict(self.plant_energy_sources)

    def get_recent_energy_breakdown(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get energy source breakdown over recent frames."""
        if window_frames <= 0:
            return {}

        cutoff_frame = self.frame_count - window_frames + 1
        recent_totals: Dict[str, float] = defaultdict(float)

        for frame, gains in self.recent_energy_gains:
            if frame >= cutoff_frame:
                for source, amount in gains.items():
                    recent_totals[source] += amount

        for source, amount in self._current_frame_gains.items():
            recent_totals[source] += amount

        return dict(recent_totals)

    def get_recent_plant_energy_breakdown(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get plant energy source breakdown over recent frames."""
        if window_frames <= 0:
            return {}

        cutoff_frame = self.frame_count - window_frames + 1
        recent_totals: Dict[str, float] = defaultdict(float)

        for frame, gains in self.recent_plant_energy_gains:
            if frame >= cutoff_frame:
                for source, amount in gains.items():
                    recent_totals[source] += amount

        for source, amount in self._current_frame_plant_gains.items():
            recent_totals[source] += amount

        return dict(recent_totals)

    def get_recent_energy_burn(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get energy consumption breakdown over recent frames."""
        if window_frames <= 0:
            return {}

        cutoff_frame = self.frame_count - window_frames + 1
        recent_totals: Dict[str, float] = defaultdict(float)

        for frame, burns in self.recent_energy_burns:
            if frame >= cutoff_frame:
                for source, amount in burns.items():
                    recent_totals[source] += amount

        for source, amount in self._current_frame_burns.items():
            recent_totals[source] += amount

        return dict(recent_totals)

    def get_recent_plant_energy_burn(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, float]:
        """Get plant energy consumption breakdown over recent frames."""
        if window_frames <= 0:
            return {}

        cutoff_frame = self.frame_count - window_frames + 1
        recent_totals: Dict[str, float] = defaultdict(float)

        for frame, burns in self.recent_plant_energy_burns:
            if frame >= cutoff_frame:
                for source, amount in burns.items():
                    recent_totals[source] += amount

        for source, amount in self._current_frame_plant_burns.items():
            recent_totals[source] += amount

        return dict(recent_totals)

    def record_energy_snapshot(self, total_fish_energy: float, fish_count: int) -> None:
        """Record a snapshot of total fish energy for delta calculations."""
        if not self.energy_history or (
            self.frame_count - self._last_snapshot_frame >= self._snapshot_interval
        ):
            self.energy_history.append((self.frame_count, total_fish_energy, fish_count))
            self._last_snapshot_frame = self.frame_count

    def get_energy_delta(
        self, window_frames: int = ENERGY_STATS_WINDOW_FRAMES
    ) -> Dict[str, Any]:
        """Calculate the true change in fish population energy over a time window."""
        if not self.energy_history:
            return {
                "energy_delta": 0.0,
                "energy_now": 0.0,
                "energy_then": 0.0,
                "fish_count_now": 0,
                "fish_count_then": 0,
                "avg_energy_delta": 0.0,
            }

        current_frame, current_energy, current_count = self.energy_history[-1]

        target_frame = current_frame - window_frames
        past_energy = current_energy
        past_count = current_count

        for frame, energy, count in self.energy_history:
            if frame <= target_frame:
                past_energy = energy
                past_count = count
            else:
                break

        energy_delta = current_energy - past_energy

        avg_now = current_energy / current_count if current_count > 0 else 0
        avg_then = past_energy / past_count if past_count > 0 else 0
        avg_delta = avg_now - avg_then

        return {
            "energy_delta": energy_delta,
            "energy_now": current_energy,
            "energy_then": past_energy,
            "fish_count_now": current_count,
            "fish_count_then": past_count,
            "avg_energy_delta": avg_delta,
        }
