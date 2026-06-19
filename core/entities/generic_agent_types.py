"""Shared datatypes for GenericAgent.

This module contains the lightweight dataclass used by
`core.entities.generic_agent.GenericAgent`, split out to keep file sizes
manageable and reduce coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agents.components.lifecycle_component import LifecycleComponent
    from core.agents.components.reproduction_component import ReproductionComponent
    from core.energy.energy_component import EnergyComponent


@dataclass
class AgentComponents:
    """Components a GenericAgent delegates core state to.

    Each field is the single owner of one concern. Subclasses supply the
    components they need via ``GenericAgent._create_components`` (or by
    passing an instance to the constructor); unset concerns stay ``None``.
    """

    energy: EnergyComponent | None = None
    lifecycle: LifecycleComponent | None = None
    reproduction: ReproductionComponent | None = None
