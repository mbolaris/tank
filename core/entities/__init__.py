"""Entity package exposing simulation agents."""

from core.entities.base import Agent, Entity, LifeStage, Rect
from core.tank_objects import Castle, TankObject, TankObjectDefinition, TankObjectLayout
import core.entities.base as _base_entities

# Keep old ``core.entities.base.Castle`` imports source-compatible while the
# implementation is now the generic entity-backed TankObject.
setattr(_base_entities, "Castle", Castle)  # noqa: B010
from core.entities.fish import Fish
from core.entities.generic_agent import AgentComponents, GenericAgent
from core.entities.plant import Plant
from core.entities.plant_nectar import PlantNectar
from core.entities.predators import Crab
from core.entities.resources import Food, LiveFood

__all__ = [
    # Base classes
    "Agent",
    "Castle",
    "TankObject",
    "TankObjectDefinition",
    "TankObjectLayout",
    "Entity",
    "LifeStage",
    "Rect",
    # Generic agent abstraction
    "GenericAgent",
    "AgentComponents",
    # Concrete entity types
    "Fish",
    "Crab",
    "Food",
    "LiveFood",
    "Plant",
    "PlantNectar",
]
