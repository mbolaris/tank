"""Shared agent components for multi-mode simulation.

This package contains reusable components composed by ``GenericAgent``
subclasses (currently ``Fish``) to own discrete concerns.

Components:
- LifecycleComponent: Aging and life stage transitions
- ReproductionComponent: Reproduction mechanics and cooldowns
"""

from core.agents.components.lifecycle_component import LifecycleComponent
from core.agents.components.reproduction_component import ReproductionComponent

__all__ = [
    "LifecycleComponent",
    "ReproductionComponent",
]
