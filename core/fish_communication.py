"""Fish communication system.

This module enables fish to signal information to nearby fish, including:
- Danger warnings
- Food discovery
- Mating signals
- Distress calls
"""

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING
from enum import Enum

from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.entities import Fish


class SignalType(Enum):
    """Types of signals fish can send."""

    DANGER_WARNING = "danger_warning"  # Predator nearby
    FOOD_FOUND = "food_found"  # Found food source
    MATING_CALL = "mating_call"  # Looking for mate
    DISTRESS = "distress"  # Under attack or starving
    ALL_CLEAR = "all_clear"  # Danger has passed
    FOLLOW_ME = "follow_me"  # Follow to food/safety


@dataclass
class Signal:
    """A signal broadcast by a fish.

    Attributes:
        signal_type: Type of signal
        sender_pos: Position of fish sending signal
        target_location: Optional location being signaled (e.g., food location)
        strength: Signal strength (0.0-1.0), affects range
        urgency: How urgent the signal is (0.0-1.0)
        timestamp: When signal was created
        metadata: Additional information
    """

    signal_type: SignalType
    sender_pos: Vector2
    target_location: Optional[Vector2] = None
    strength: float = 1.0
    urgency: float = 0.5
    timestamp: int = 0
    metadata: dict = field(default_factory=dict)

    def get_range(self) -> float:
        """Calculate signal range based on strength and urgency.

        Returns:
            Effective range in pixels
        """
        base_range = 150.0  # Base communication range
        return base_range * self.strength * (1.0 + self.urgency * 0.5)

    def decay(self, decay_rate: float = 0.05):
        """Decay signal strength over time."""
        self.strength = max(0.0, self.strength - decay_rate)

    def is_expired(self, max_age: int = 90) -> bool:
        """Check if signal has expired (default 3 seconds at 30fps)."""
        return self.strength <= 0.0


class FishCommunicationSystem:
    """Manages communication between fish.

    Attributes:
        active_signals: List of currently active signals
        max_signals: Maximum number of signals to track
        decay_rate: How fast signals decay
    """

    def __init__(self, max_signals: int = 50, decay_rate: float = 0.05):
        """Initialize communication system.

        Args:
            max_signals: Maximum active signals
            decay_rate: Signal decay rate per frame
        """
        self.active_signals: List[Signal] = []
        self.max_signals = max_signals
        self.decay_rate = decay_rate
        self.current_frame = 0

    def broadcast_signal(
        self,
        signal_type: SignalType,
        sender_pos: Vector2,
        target_location: Optional[Vector2] = None,
        strength: float = 1.0,
        urgency: float = 0.5,
        metadata: Optional[dict] = None,
    ):
        """Broadcast a signal.

        Args:
            signal_type: Type of signal
            sender_pos: Position of sender
            target_location: Optional target location
            strength: Signal strength (0.0-1.0)
            urgency: Signal urgency (0.0-1.0)
            metadata: Additional data
        """
        signal = Signal(
            signal_type=signal_type,
            sender_pos=sender_pos.copy(),
            target_location=target_location.copy() if target_location else None,
            strength=strength,
            urgency=urgency,
            timestamp=self.current_frame,
            metadata=metadata or {},
        )

        self.active_signals.append(signal)

        # Limit signal count
        if len(self.active_signals) > self.max_signals:
            # Remove oldest/weakest signals
            self.active_signals.sort(key=lambda s: (s.strength, -s.timestamp))
            self.active_signals = self.active_signals[-self.max_signals :]

    def get_nearby_signals(
        self,
        position: Vector2,
        signal_type: Optional[SignalType] = None,
        max_distance: Optional[float] = None,
    ) -> List[Signal]:
        """Get signals near a position.

        Args:
            position: Position to search from
            signal_type: Optional filter by signal type
            max_distance: Optional maximum distance (uses signal range if None)

        Returns:
            List of nearby signals
        """
        nearby = []

        for signal in self.active_signals:
            # Filter by type if specified
            if signal_type and signal.signal_type != signal_type:
                continue

            # Check distance
            distance = (signal.sender_pos - position).length()
            signal_range = max_distance if max_distance else signal.get_range()

            if distance <= signal_range:
                nearby.append(signal)

        # Sort by distance (closest first)
        nearby.sort(key=lambda s: (s.sender_pos - position).length())
        return nearby

    def get_strongest_signal(
        self, position: Vector2, signal_type: Optional[SignalType] = None
    ) -> Optional[Signal]:
        """Get strongest signal near a position.

        Args:
            position: Position to search from
            signal_type: Optional filter by signal type

        Returns:
            Strongest nearby signal or None
        """
        nearby = self.get_nearby_signals(position, signal_type)
        if not nearby:
            return None

        # Return signal with highest combined score
        def score_signal(s: Signal) -> float:
            distance = (s.sender_pos - position).length()
            distance_factor = max(0.0, 1.0 - distance / s.get_range())
            return s.strength * s.urgency * distance_factor

        return max(nearby, key=score_signal)

    def update(self, current_frame: int):
        """Update communication system (decay and remove old signals).

        Args:
            current_frame: Current simulation frame
        """
        self.current_frame = current_frame

        # Decay all signals
        for signal in self.active_signals:
            signal.decay(self.decay_rate)

        # Remove expired signals
        self.active_signals = [s for s in self.active_signals if not s.is_expired()]

    def clear_signals(self, signal_type: Optional[SignalType] = None):
        """Clear signals.

        Args:
            signal_type: Type to clear, or None to clear all
        """
        if signal_type:
            self.active_signals = [s for s in self.active_signals if s.signal_type != signal_type]
        else:
            self.active_signals = []

    def get_signal_count(self, signal_type: Optional[SignalType] = None) -> int:
        """Get count of active signals.

        Args:
            signal_type: Optional filter by type

        Returns:
            Count of signals
        """
        if signal_type:
            return len([s for s in self.active_signals if s.signal_type == signal_type])
        return len(self.active_signals)


def fish_should_respond_to_signal(fish: "Fish", signal: Signal) -> bool:
    """Determine if a fish should respond to a signal.

    Args:
        fish: The fish receiving the signal
        signal: The signal to evaluate

    Returns:
        True if fish should respond
    """
    # Check social tendency - more social fish respond more
    social_response_threshold = 1.0 - fish.genome.social_tendency

    # Check signal relevance based on fish state
    if signal.signal_type == SignalType.DANGER_WARNING:
        # Always respond to danger if not already fleeing
        return True

    elif signal.signal_type == SignalType.FOOD_FOUND:
        # Respond if hungry
        if fish.is_low_energy() or fish.is_critical_energy():
            return True
        # Otherwise based on social tendency
        return fish.genome.social_tendency > social_response_threshold

    elif signal.signal_type == SignalType.MATING_CALL:
        # Respond if can reproduce
        return fish.can_reproduce()

    elif signal.signal_type == SignalType.DISTRESS:
        # Help if highly social
        return fish.genome.social_tendency > 0.7

    elif signal.signal_type == SignalType.FOLLOW_ME:
        # Follow if social
        return fish.genome.social_tendency > social_response_threshold

    # Default: respond based on social tendency
    return fish.genome.social_tendency > 0.5
