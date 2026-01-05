"""Statistics calculation package for the simulation.

This package provides modular statistics calculation, splitting the original
1,277-line StatsCalculator into focused sub-calculators.

Architecture Notes:
- StatsCalculator is the main aggregator
- Sub-calculators handle specific stat domains
- Each sub-calculator can be tested independently
"""

from core.services.stats.calculator import StatsCalculator

__all__ = ["StatsCalculator"]
