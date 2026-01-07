"""Fish-related components and utilities.

This package contains modular components for fish functionality,
organized for better code clarity and testability.
"""

# EnergyComponent moved to core.energy for cross-world sharing
# Re-export for backward compatibility (deprecated, use core.energy instead)
from core.energy.energy_component import EnergyComponent
from core.fish.reproduction_component import ReproductionComponent

__all__ = ["EnergyComponent", "ReproductionComponent"]
