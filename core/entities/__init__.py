"""Entity package exposing simulation agents."""

from core.entities.base import Agent, Castle, Entity, LifeStage, Rect
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
