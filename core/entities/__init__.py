"""Entity package exposing simulation agents."""

from core.entities.base import Agent, Castle, Entity, LifeStage, Rect
from core.entities.fish import Fish
from core.entities.plant import Plant, PlantNectar
from core.entities.predators import Crab
from core.entities.resources import Food, LiveFood

__all__ = [
    "Agent",
    "Castle",
    "Entity",
    "LifeStage",
    "Rect",
    "Fish",
    "Crab",
    "Food",
    "LiveFood",
    "Plant",
    "PlantNectar",
]
