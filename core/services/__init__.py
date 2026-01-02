"""Core services package.

Services are cross-cutting concerns that don't fit neatly into the
entity or system categories. They typically:
- Aggregate data from multiple sources
- Provide computed views of simulation state
- Handle operations that span multiple systems
"""

from core.services.energy_tracker import EnergyTracker
from core.services.stats.calculator import StatsCalculator

__all__ = ["EnergyTracker", "StatsCalculator"]
