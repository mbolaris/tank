"""Shared agent components for multi-mode simulation.

This package contains reusable components that can be composed to create
different agent types (Fish, PetriMicrobe, SoccerPlayer, etc.).

Components:
- PerceptionComponent: Sensory data and memory queries
- LocomotionComponent: Movement, navigation, and boundary handling
- FeedingComponent: Food consumption and nutrition tracking
"""

from core.agents.components.feeding_component import FeedingComponent
from core.agents.components.locomotion_component import LocomotionComponent
from core.agents.components.perception_component import PerceptionComponent

__all__ = [
    "PerceptionComponent",
    "LocomotionComponent",
    "FeedingComponent",
]
