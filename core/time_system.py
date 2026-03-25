"""Day/night cycle system for the simulation.

This module provides time-of-day tracking and related effects.
The system extends BaseSystem for consistent interface and lifecycle management.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.TIME_UPDATE
- Provides time-based modifiers for fish behavior and visibility
"""

import math
from typing import TYPE_CHECKING, Any

from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.simulation import SimulationEngine


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
        engine: "SimulationEngine",
        cycle_length: int = 1800,
    ) -> None:
        """Initialize the time system.

        Args:
            engine: The simulation engine
            cycle_length: Number of frames for a full day/night cycle
                         (default: 1800 = 1 min at 30fps)
        """
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

    def get_screen_tint(self) -> tuple[int, int, int]:
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
        Uses smooth interpolation to avoid sudden behavioral shifts.

        Returns:
            Float multiplier for detection range:
            - Night core (0.0-0.20, 0.80-1.0): 0.55 (55% range)
            - Dawn/Dusk transitions: smooth linear ramp
            - Day core (0.35-0.65): 1.0 (100% range)
        """
        time_of_day = self.get_time_of_day()

        # Use smooth interpolation instead of hard steps.
        # Night floor raised from 0.40 -> 0.55 based on experiments showing
        # 98.5% starvation deaths. Night was too punishing given fish need
        # to find food ~50% of the simulation cycle.
        night_floor = 0.55
        day_ceiling = 1.0

        if time_of_day < 0.20 or time_of_day > 0.80:
            # Deep night: reduced but survivable detection
            return night_floor
        elif time_of_day < 0.35:
            # Dawn transition: smooth ramp from night_floor to day_ceiling
            progress = (time_of_day - 0.20) / 0.15
            return night_floor + (day_ceiling - night_floor) * progress
        elif time_of_day <= 0.65:
            # Full day: maximum detection
            return day_ceiling
        else:
            # Dusk transition: smooth ramp from day_ceiling to night_floor
            progress = (time_of_day - 0.65) / 0.15
            return day_ceiling - (day_ceiling - night_floor) * progress

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

    def get_debug_info(self) -> dict[str, Any]:
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
