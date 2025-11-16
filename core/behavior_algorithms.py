"""Behavior algorithms for fish - backward compatibility module.

This module has been refactored into the core.algorithms package.
All imports are re-exported from there for backward compatibility.

New structure:
- core/algorithms/base.py - Base class and utilities
- core/algorithms/food_seeking.py - Food-related behaviors (12 algorithms)
- core/algorithms/predator_avoidance.py - Escape strategies (10 algorithms)
- core/algorithms/schooling.py - Social behaviors (10 algorithms)
- core/algorithms/energy_management.py - Energy optimization (8 algorithms)
- core/algorithms/territory.py - Spatial behaviors (8 algorithms)
- core/algorithms/poker.py - Poker interaction behaviors (5 algorithms)
"""

# Re-export everything from the algorithms package for backward compatibility
from core.algorithms import *  # noqa: F401, F403

# Explicitly list what's exported to maintain compatibility
__all__ = [
    # Base
    'BehaviorAlgorithm',
    'ALGORITHM_PARAMETER_BOUNDS',
    'Vector2',

    # Food seeking (12)
    'GreedyFoodSeeker',
    'EnergyAwareFoodSeeker',
    'OpportunisticFeeder',
    'FoodQualityOptimizer',
    'AmbushFeeder',
    'PatrolFeeder',
    'SurfaceSkimmer',
    'BottomFeeder',
    'ZigZagForager',
    'CircularHunter',
    'FoodMemorySeeker',
    'CooperativeForager',

    # Predator avoidance (10)
    'PanicFlee',
    'StealthyAvoider',
    'FreezeResponse',
    'ErraticEvader',
    'VerticalEscaper',
    'GroupDefender',
    'SpiralEscape',
    'BorderHugger',
    'PerpendicularEscape',
    'DistanceKeeper',

    # Schooling (10)
    'TightScholer',
    'LooseScholer',
    'LeaderFollower',
    'AlignmentMatcher',
    'SeparationSeeker',
    'FrontRunner',
    'PerimeterGuard',
    'MirrorMover',
    'BoidsBehavior',
    'DynamicScholer',

    # Energy management (8)
    'EnergyConserver',
    'BurstSwimmer',
    'OpportunisticRester',
    'EnergyBalancer',
    'SustainableCruiser',
    'StarvationPreventer',
    'MetabolicOptimizer',
    'AdaptivePacer',

    # Territory/exploration (8)
    'TerritorialDefender',
    'RandomExplorer',
    'WallFollower',
    'CornerSeeker',
    'CenterHugger',
    'RoutePatroller',
    'BoundaryExplorer',
    'NomadicWanderer',

    # Poker interactions (5)
    'PokerChallenger',
    'PokerDodger',
    'PokerGambler',
    'SelectivePoker',
    'PokerOpportunist',

    # Utilities
    'ALL_ALGORITHMS',
    'get_algorithm_index',
    'get_random_algorithm',
    'get_algorithm_by_id',
    'inherit_algorithm_with_mutation',
]
