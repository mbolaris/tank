"""Entity package exposing simulation agents."""

from core.entities.base import Agent, Castle, LifeStage, Rect
from core.entities.fish import Fish
from core.entities.fractal_plant import FractalPlant, PlantNectar
from core.entities.predators import Crab, Jellyfish
from core.entities.resources import Food, LiveFood, Plant

__all__ = [
    "Agent",
    "Castle",
    "LifeStage",
    "Rect",
    "Fish",
    "Crab",
    "Jellyfish",
    "Food",
    "LiveFood",
    "Plant",
    "FractalPlant",
    "PlantNectar",
]
