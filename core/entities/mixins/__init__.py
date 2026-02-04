"""Fish entity mixins for cleaner separation of concerns.

Each mixin encapsulates a logical group of behavior:
- EnergyManagementMixin: Energy gain, loss, overflow routing, status checks
- ReproductionMixin: Reproduction eligibility, offspring creation, mating
- MortalityMixin: Death detection, cause attribution, predator encounters
"""

from core.entities.mixins.energy_mixin import EnergyManagementMixin
from core.entities.mixins.mortality_mixin import MortalityMixin
from core.entities.mixins.reproduction_mixin import ReproductionMixin

__all__ = ["EnergyManagementMixin", "MortalityMixin", "ReproductionMixin"]
