"""Genetics system for fractal plants.

BACKWARD COMPATIBILITY MODULE
=============================
This module re-exports from core.genetics.plant for backward compatibility.
New code should import directly from core.genetics instead.

Example:
    # Old way (still works)
    from core.plant_genetics import PlantGenome

    # New way (preferred)
    from core.genetics import PlantGenome
"""

# Re-export PlantGenome from new location
from core.genetics.plant import PlantGenome

__all__ = ["PlantGenome"]
