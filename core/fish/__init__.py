"""Fish-related components and utilities.

This package contains modular components for fish functionality,
organized for better code clarity and testability.
"""

# EnergyComponent moved to core.energy for cross-world sharing
# Re-export from core.energy (use core.energy directly for new code)
from core.energy.energy_component import EnergyComponent

__all__ = ["EnergyComponent"]
