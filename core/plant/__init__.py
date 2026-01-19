"""Plant-related components and utilities.

This package contains modular components for plant functionality,
organized for better code clarity and testability.
"""

from core.plant.energy_component import PlantEnergyComponent
from core.plant.migration_component import PlantMigrationComponent
from core.plant.nectar_component import PlantNectarComponent
from core.plant.poker_component import PlantPokerComponent
from core.plant.visual_component import PlantVisualComponent

__all__ = [
    "PlantEnergyComponent",
    "PlantMigrationComponent",
    "PlantNectarComponent",
    "PlantPokerComponent",
    "PlantVisualComponent",
]
