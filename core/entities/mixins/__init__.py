"""Fish-only policy mixins layered over the pure-state agent components.

These are **not** reusable mixins: each hardwires Fish/world specifics
(``fish_id``, ``environment``, ``ReproductionService``, food spawning) and is
mixed into ``Fish`` and only ``Fish``. They hold *policy* plus the
protocol-facing API, and delegate state and pure math/rules to the components
they wrap:

- EnergyManagementMixin -> EnergyComponent       (energy value, metabolism math)
- ReproductionMixin     -> ReproductionComponent (credits/cooldown, eligibility)
- MortalityMixin        -> (no component; death/migration is pure Fish/world policy)

This policy-vs-state split is intentional (see ADR-013): the components stay
free of world coupling so they remain unit-testable, while the Fish-specific
wiring lives here. They are kept out of ``fish.py`` only to keep that module a
manageable size - conceptually they are part of ``Fish``.
"""

from core.entities.mixins.energy_mixin import EnergyManagementMixin
from core.entities.mixins.mortality_mixin import MortalityMixin
from core.entities.mixins.reproduction_mixin import ReproductionMixin

__all__ = ["EnergyManagementMixin", "MortalityMixin", "ReproductionMixin"]
