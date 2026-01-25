"""Energy management components for entities.

This module provides energy-related functionality that can be shared across
different entity types and worlds (tank fish, soccer players, etc.).
"""

from core.energy.energy_component import EnergyComponent
from core.energy.energy_utils import apply_energy_delta

__all__ = ["EnergyComponent", "apply_energy_delta"]
