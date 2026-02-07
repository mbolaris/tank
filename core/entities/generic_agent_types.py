"""Shared datatypes for GenericAgent.

This module intentionally contains the lightweight dataclasses / protocols used
by `core.entities.generic_agent.GenericAgent`, split out to keep file sizes
manageable and reduce coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.agents.components import (FeedingComponent, LocomotionComponent,
                                        PerceptionComponent)
    from core.agents.components.lifecycle_component import LifecycleComponent
    from core.agents.components.reproduction_component import \
        ReproductionComponent
    from core.energy.energy_component import EnergyComponent
    from core.entities.generic_agent import GenericAgent


@dataclass
class Percept:
    """Sensory data collected during the perceive phase."""

    position: Vector2
    velocity: Vector2
    energy: float = 0.0
    max_energy: float = 100.0
    age: int = 0
    size: float = 1.0
    nearby_food: list[Vector2] = field(default_factory=list)
    nearby_danger: list[Vector2] = field(default_factory=list)
    nearby_agents: list[Any] = field(default_factory=list)
    time_of_day: float | None = None
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """Action to be executed during the act phase."""

    movement: Vector2 | None = None
    eat_target: Any | None = None
    reproduce: bool = False
    interact_target: Any | None = None
    custom: dict[str, Any] = field(default_factory=dict)


class DecisionPolicy(Protocol):
    """Interface for decision-making policies (brains)."""

    def decide(self, percept: Percept, agent: GenericAgent) -> Action: ...


@dataclass
class AgentComponents:
    """Configuration of components for a GenericAgent."""

    energy: EnergyComponent | None = None
    lifecycle: LifecycleComponent | None = None
    perception: PerceptionComponent | None = None
    locomotion: LocomotionComponent | None = None
    feeding: FeedingComponent | None = None
    reproduction: ReproductionComponent | None = None
