"""Day/night cycle system for the simulation.

This module provides time-of-day tracking and related effects.
"""

import math
from typing import Tuple


class TimeSystem:
    """Manages the day/night cycle and time-related effects.

    Attributes:
        time: Current time in the cycle (0.0 to cycle_length)
        cycle_length: Length of one full day/night cycle in frames
    """

    def __init__(self, cycle_length: int = 1800):
        """Initialize the time system.

        Args:
            cycle_length: Number of frames for a full day/night cycle (default: 1800 = 1 min at 30fps)
        """
        self.time: float = 0.0
        self.cycle_length: int = cycle_length

    def update(self) -> None:
        """Advance time by one frame."""
        self.time = (self.time + 1) % self.cycle_length

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
            # Dark blue tint
            r = int(20 * brightness)
            g = int(20 * brightness)
            b = int(40 * brightness)
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
