"""Energy state value object.

This module defines the EnergyState class, which provides an immutable
snapshot of a fish's energy status. It centralizes logic for determined
critical energy thresholds, saturation, and other energy-derived states.
"""

from dataclasses import dataclass
from typing import Optional

from core.config.fish import (
    CRITICAL_ENERGY_THRESHOLD_RATIO,
    LOW_ENERGY_THRESHOLD_RATIO,
    REPRODUCTION_MIN_ENERGY,
)


@dataclass(frozen=True)
class EnergyState:
    """Immutable snapshot of energy state.
    
    This class encapsulates all logic related to energy thresholds and states,
    providing a single source of truth for energy checking patterns.
    """
    
    current_energy: float
    max_energy: float
    
    @property
    def percentage(self) -> float:
        """Get energy as a percentage (0.0 - 1.0)."""
        if self.max_energy <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current_energy / self.max_energy))
        
    @property
    def is_critical(self) -> bool:
        """Check if energy is critically low."""
        return self.percentage < CRITICAL_ENERGY_THRESHOLD_RATIO
        
    @property
    def is_hungry(self) -> bool:
        """Check if fish is hungry (below low energy threshold).
        
        Uses the configured ratio.
        """
        return self.percentage < LOW_ENERGY_THRESHOLD_RATIO
        
    @property
    def can_reproduce(self) -> bool:
        """Check if energy is sufficient for reproduction attempt."""
        # Using the absolute minimum value from config
        return self.current_energy >= REPRODUCTION_MIN_ENERGY
        
    @property
    def is_saturated(self) -> bool:
        """Check if energy is full (>= 100%)."""
        return self.current_energy >= self.max_energy
    
    @property
    def saturation_overflow(self) -> float:
        """Get amount of energy exceeding max capacity."""
        return max(0.0, self.current_energy - self.max_energy)
