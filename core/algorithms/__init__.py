"""Behavior algorithms package.

This package organizes fish behavior algorithms into categories:
- base: Core BehaviorAlgorithm class and utilities
- food_seeking: Food-finding and hunting behaviors
- predator_avoidance: Escape and avoidance strategies
- schooling: Social and group behaviors
- energy_management: Energy conservation and optimization
- territory: Spatial behaviors and exploration

All algorithms are exported at the package level for backward compatibility.
"""

import random
from typing import Optional

# Import base class and utilities
from core.algorithms.base import (
    BehaviorAlgorithm,
    ALGORITHM_PARAMETER_BOUNDS,
    Vector2,
)

# Import all food-seeking algorithms
from core.algorithms.food_seeking import (
    GreedyFoodSeeker,
    EnergyAwareFoodSeeker,
    OpportunisticFeeder,
    FoodQualityOptimizer,
    AmbushFeeder,
    PatrolFeeder,
    SurfaceSkimmer,
    BottomFeeder,
    ZigZagForager,
    CircularHunter,
    FoodMemorySeeker,
    CooperativeForager,
)

# Import all predator avoidance algorithms
from core.algorithms.predator_avoidance import (
    PanicFlee,
    StealthyAvoider,
    FreezeResponse,
    ErraticEvader,
    VerticalEscaper,
    GroupDefender,
    SpiralEscape,
    BorderHugger,
    PerpendicularEscape,
    DistanceKeeper,
)

# Import all schooling algorithms
from core.algorithms.schooling import (
    TightScholer,
    LooseScholer,
    LeaderFollower,
    AlignmentMatcher,
    SeparationSeeker,
    FrontRunner,
    PerimeterGuard,
    MirrorMover,
    BoidsBehavior,
    DynamicScholer,
)

# Import all energy management algorithms
from core.algorithms.energy_management import (
    EnergyConserver,
    BurstSwimmer,
    OpportunisticRester,
    EnergyBalancer,
    SustainableCruiser,
    StarvationPreventer,
    MetabolicOptimizer,
    AdaptivePacer,
)

# Import all territory/exploration algorithms
from core.algorithms.territory import (
    TerritorialDefender,
    RandomExplorer,
    WallFollower,
    CornerSeeker,
    CenterHugger,
    RoutePatroller,
    BoundaryExplorer,
    NomadicWanderer,
)

# Import all poker interaction algorithms
from core.algorithms.poker import (
    PokerChallenger,
    PokerDodger,
    PokerGambler,
    SelectivePoker,
    PokerOpportunist,
)


# All available algorithms (in original order for compatibility)
ALL_ALGORITHMS = [
    # Food seeking
    GreedyFoodSeeker,
    EnergyAwareFoodSeeker,
    OpportunisticFeeder,
    FoodQualityOptimizer,
    AmbushFeeder,
    PatrolFeeder,
    SurfaceSkimmer,
    BottomFeeder,
    ZigZagForager,
    CircularHunter,
    FoodMemorySeeker,
    CooperativeForager,

    # Predator avoidance
    PanicFlee,
    StealthyAvoider,
    FreezeResponse,
    ErraticEvader,
    VerticalEscaper,
    GroupDefender,
    SpiralEscape,
    BorderHugger,
    PerpendicularEscape,
    DistanceKeeper,

    # Schooling/social
    TightScholer,
    LooseScholer,
    LeaderFollower,
    AlignmentMatcher,
    SeparationSeeker,
    FrontRunner,
    PerimeterGuard,
    MirrorMover,
    BoidsBehavior,
    DynamicScholer,

    # Energy management
    EnergyConserver,
    BurstSwimmer,
    OpportunisticRester,
    EnergyBalancer,
    SustainableCruiser,
    StarvationPreventer,
    MetabolicOptimizer,
    AdaptivePacer,

    # Territory/exploration
    TerritorialDefender,
    RandomExplorer,
    WallFollower,
    CornerSeeker,
    CenterHugger,
    RoutePatroller,
    BoundaryExplorer,
    NomadicWanderer,

    # Poker interactions
    PokerChallenger,
    PokerDodger,
    PokerGambler,
    SelectivePoker,
    PokerOpportunist,
]


def get_algorithm_index(algorithm: BehaviorAlgorithm) -> int:
    """Get the index of an algorithm in the ALL_ALGORITHMS list.

    Args:
        algorithm: The behavior algorithm instance

    Returns:
        Index (0-47) of the algorithm, or -1 if not found
    """
    algorithm_class = type(algorithm)
    try:
        return ALL_ALGORITHMS.index(algorithm_class)
    except ValueError:
        return -1


def get_random_algorithm() -> BehaviorAlgorithm:
    """Get a random behavior algorithm instance."""
    algorithm_class = random.choice(ALL_ALGORITHMS)
    return algorithm_class.random_instance()


def get_algorithm_by_id(algorithm_id: str) -> Optional[BehaviorAlgorithm]:
    """Get algorithm instance by ID."""
    for algo_class in ALL_ALGORITHMS:
        instance = algo_class.random_instance()
        if instance.algorithm_id == algorithm_id:
            return instance
    return None


def inherit_algorithm_with_mutation(parent_algorithm: BehaviorAlgorithm,
                                   mutation_rate: float = 0.15,
                                   mutation_strength: float = 0.2) -> BehaviorAlgorithm:
    """Create offspring algorithm by copying parent and mutating parameters.

    Args:
        parent_algorithm: Parent's behavior algorithm
        mutation_rate: Probability of each parameter mutating
        mutation_strength: Magnitude of mutations

    Returns:
        New algorithm instance with mutated parameters
    """
    # Create new instance of same algorithm type
    offspring = parent_algorithm.__class__()

    # Copy parent parameters
    offspring.parameters = parent_algorithm.parameters.copy()

    # Mutate
    offspring.mutate_parameters(mutation_rate, mutation_strength)

    return offspring


# Export all symbols
__all__ = [
    # Base
    'BehaviorAlgorithm',
    'ALGORITHM_PARAMETER_BOUNDS',
    'Vector2',

    # Food seeking
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

    # Predator avoidance
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

    # Schooling
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

    # Energy management
    'EnergyConserver',
    'BurstSwimmer',
    'OpportunisticRester',
    'EnergyBalancer',
    'SustainableCruiser',
    'StarvationPreventer',
    'MetabolicOptimizer',
    'AdaptivePacer',

    # Territory/exploration
    'TerritorialDefender',
    'RandomExplorer',
    'WallFollower',
    'CornerSeeker',
    'CenterHugger',
    'RoutePatroller',
    'BoundaryExplorer',
    'NomadicWanderer',

    # Poker interactions
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
