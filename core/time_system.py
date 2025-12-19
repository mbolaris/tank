"""Day/night cycle system for the simulation.

This module provides time-of-day tracking and related effects.
The system extends BaseSystem for consistent interface and lifecycle management.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.TIME_UPDATE
- Can operate independently (engine reference optional for backward compatibility)
- Provides time-based modifiers for fish behavior and visibility
"""

import math
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.simulation_engine import SimulationEngine


@runs_in_phase(UpdatePhase.TIME_UPDATE)
class TimeSystem(BaseSystem):
    """Manages the day/night cycle and time-related effects.

    This system runs in the TIME_UPDATE phase and tracks the simulation's
    day/night cycle, providing modifiers for fish behavior, visibility,
    and screen rendering.

    Attributes:
        time: Current time in the cycle (0.0 to cycle_length)
        cycle_length: Length of one full day/night cycle in frames
    """

    def __init__(
        self,
        engine: Optional["SimulationEngine"] = None,
        cycle_length: int = 1800,
    ) -> None:
        """Initialize the time system.

        Args:
            engine: The simulation engine (optional for backward compatibility)
            cycle_length: Number of frames for a full day/night cycle
                         (default: 1800 = 1 min at 30fps)
        """
        # Handle case where engine is not provided (backward compatibility)
        # We'll use a sentinel object that satisfies BaseSystem's needs
        if engine is None:
            # Create minimal engine-like object for BaseSystem
            class _DummyEngine:
                pass
            super().__init__(_DummyEngine(), "Time")  # type: ignore
            self._engine = None  # type: ignore  # Override to None for safety
        else:
            super().__init__(engine, "Time")

        self.time: float = 0.0
        self.cycle_length: int = cycle_length
        self._days_elapsed: int = 0

    def _do_update(self, frame: int) -> SystemResult:
        """Advance time by one frame.

        Args:
            frame: Current simulation frame number (unused, time tracked internally)

        Returns:
            SystemResult with day transition details
        """
        old_time = self.time
        self.time = (self.time + 1) % self.cycle_length

        # Track day transitions
        day_transitioned = self.time < old_time
        if day_transitioned:
            self._days_elapsed += 1

        return SystemResult(
            details={
                "time_of_day": self.get_time_of_day(),
                "day_transitioned": day_transitioned,
            },
        )

    def update(self, frame: int = 0) -> SystemResult:
        """Advance time by one frame.

        Overrides BaseSystem.update() to support being called without frame arg
        for backward compatibility.

        Args:
            frame: Current simulation frame number (optional)

        Returns:
            SystemResult with time update details
        """
        if not self._enabled:
            return SystemResult.skipped_result()
        result = self._do_update(frame)
        self._update_count += 1
        return result

    def get_time_of_day(self) -> float:
        """Get normalized time of day.

        Returns:
            Float from 0.0 (midnight) to 1.0 (next midnight)
            0.25 = dawn, 0.5 = noon, 0.75 = dusk
        """
        return self.time / self.cycle_length

    def is_day(self) -> bool:
        """Check if it's currently daytime.

        Returns:
            True if between dawn (0.25) and dusk (0.75)
        """
        time_of_day = self.get_time_of_day()
        return 0.25 <= time_of_day <= 0.75

    def is_night(self) -> bool:
        """Check if it's currently nighttime."""
        return not self.is_day()

    def get_brightness(self) -> float:
        """Get current brightness level.

        Returns:
            Float from 0.4 (darkest night) to 1.0 (brightest day)
        """
        time_of_day = self.get_time_of_day()

        # Use sine wave for smooth transitions
        # Peak at noon (0.5), trough at midnight (0.0/1.0)
        brightness = 0.7 + 0.3 * math.sin(2 * math.pi * (time_of_day - 0.25))

        return max(0.4, min(1.0, brightness))

    def get_activity_modifier(self) -> float:
        """Get activity level modifier based on time of day.

        Returns:
            Float from 0.5 (night, less active) to 1.0 (day, fully active)
        """
        time_of_day = self.get_time_of_day()

        # Fish are less active at night
        activity = 0.75 + 0.25 * math.sin(2 * math.pi * (time_of_day - 0.25))

        return max(0.5, min(1.0, activity))

    def get_screen_tint(self) -> Tuple[int, int, int]:
        """Get RGB tint for the screen based on time of day.

        Returns:
            RGB tuple to overlay on the screen
        """
        time_of_day = self.get_time_of_day()
        brightness = self.get_brightness()

        if time_of_day < 0.25:  # Night to dawn
            # Interpolate from midnight dark blue to dawn start
            # Midnight (0.0): (20, 20, 40)
            # Dawn Start (0.25): (100, 100, 120) - matches start of next block
            progress = time_of_day / 0.25
            r = int((20 + 80 * progress) * brightness)
            g = int((20 + 80 * progress) * brightness)
            b = int((40 + 80 * progress) * brightness)
        elif time_of_day < 0.5:  # Dawn to noon
            # Warm morning light
            progress = (time_of_day - 0.25) / 0.25
            r = int((100 + 155 * progress) * brightness)
            g = int((100 + 155 * progress) * brightness)
            b = int((120 + 135 * progress) * brightness)
        elif time_of_day < 0.75:  # Noon to dusk
            # Warm afternoon/evening light
            progress = (time_of_day - 0.5) / 0.25
            r = int((255 - 55 * progress) * brightness)
            g = int((255 - 100 * progress) * brightness)
            b = int((255 - 155 * progress) * brightness)
        else:  # Dusk to night
            # Darkening to night
            progress = (time_of_day - 0.75) / 0.25
            r = int((200 - 180 * progress) * brightness)
            g = int((155 - 135 * progress) * brightness)
            b = int((100 - 60 * progress) * brightness)

        return (r, g, b)

    def get_detection_range_modifier(self) -> float:
        """Get detection range modifier based on time of day.

        Fish have reduced ability to detect food at night due to lower visibility.

        Returns:
            Float multiplier for detection range:
            - Night (0.0-0.25, 0.75-1.0): 0.25 (25% range)
            - Dawn (0.25-0.35): 0.75 (75% range)
            - Dusk (0.65-0.75): 0.75 (75% range)
            - Day (0.35-0.65): 1.0 (100% range)
        """
        time_of_day = self.get_time_of_day()

        # Night: very limited detection
        if time_of_day < 0.25 or time_of_day > 0.75:
            return 0.25
        # Dawn: transitioning to full visibility
        elif time_of_day < 0.35:
            return 0.75
        # Day: full detection range
        elif time_of_day < 0.65:
            return 1.0
        # Dusk: transitioning to limited visibility
        else:
            return 0.75

    def get_time_string(self) -> str:
        """Get a human-readable time string.

        Returns:
            String like "Dawn", "Day", "Dusk", "Night"
        """
        time_of_day = self.get_time_of_day()

        if time_of_day < 0.15 or time_of_day > 0.85:
            return "Night"
        elif time_of_day < 0.35:
            return "Dawn"
        elif time_of_day < 0.65:
            return "Day"
        else:
            return "Dusk"

    def get_debug_info(self) -> Dict[str, Any]:
        """Return time system statistics for debugging.

        Returns:
            Dictionary containing system state and statistics
        """
        return {
            **super().get_debug_info(),
            "time": self.time,
            "cycle_length": self.cycle_length,
            "time_of_day": self.get_time_of_day(),
            "time_string": self.get_time_string(),
            "is_day": self.is_day(),
            "brightness": self.get_brightness(),
            "activity_modifier": self.get_activity_modifier(),
            "detection_modifier": self.get_detection_range_modifier(),
            "days_elapsed": self._days_elapsed,
        }
