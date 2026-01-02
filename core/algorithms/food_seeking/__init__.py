"""Food-seeking behavior algorithms."""

from core.algorithms.food_seeking.aggressive import AggressiveHunter
from core.algorithms.food_seeking.ambush import AmbushFeeder
from core.algorithms.food_seeking.bottom import BottomFeeder
from core.algorithms.food_seeking.circular import CircularHunter
from core.algorithms.food_seeking.cooperative import CooperativeForager
from core.algorithms.food_seeking.energy_aware import EnergyAwareFoodSeeker
from core.algorithms.food_seeking.greedy import GreedyFoodSeeker
from core.algorithms.food_seeking.memory import FoodMemorySeeker
from core.algorithms.food_seeking.opportunistic import OpportunisticFeeder
from core.algorithms.food_seeking.patrol import PatrolFeeder
from core.algorithms.food_seeking.quality import FoodQualityOptimizer
from core.algorithms.food_seeking.spiral import SpiralForager
from core.algorithms.food_seeking.surface import SurfaceSkimmer
from core.algorithms.food_seeking.zigzag import ZigZagForager

__all__ = [
    "GreedyFoodSeeker",
    "EnergyAwareFoodSeeker",
    "OpportunisticFeeder",
    "FoodQualityOptimizer",
    "AmbushFeeder",
    "PatrolFeeder",
    "SurfaceSkimmer",
    "BottomFeeder",
    "ZigZagForager",
    "CircularHunter",
    "FoodMemorySeeker",
    "AggressiveHunter",
    "SpiralForager",
    "CooperativeForager",
]
