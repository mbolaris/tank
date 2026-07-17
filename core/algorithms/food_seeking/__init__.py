"""Food-seeking behavior algorithms.

ADR-006 stage 2: 11 deprecated monolithic food-seekers removed.
Only the 3 winners retained (beat the composable baseline on every seed).
See docs/adr/006-deprecate-monolithic-food-seekers.md.
"""

from core.algorithms.food_seeking.cooperative import CooperativeForager
from core.algorithms.food_seeking.opportunistic import OpportunisticFeeder
from core.algorithms.food_seeking.quality import FoodQualityOptimizer

__all__ = [
    "CooperativeForager",
    "FoodQualityOptimizer",
    "OpportunisticFeeder",
]
