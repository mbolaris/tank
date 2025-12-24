"""Statistics calculator backward compatibility shim.

This module re-exports StatsCalculator from the new stats package
for backward compatibility with existing imports.

Note: New code should import from core.services.stats directly.
"""

from core.services.stats.calculator import StatsCalculator

__all__ = ["StatsCalculator"]
