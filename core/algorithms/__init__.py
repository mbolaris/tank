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
    ALGORITHM_PARAMETER_BOUNDS,
    BehaviorAlgorithm,
    Vector2,
)

# Import all energy management algorithms
from core.algorithms.energy_management import (
    AdaptivePacer,
    BurstSwimmer,
    EnergyBalancer,
    EnergyConserver,
    MetabolicOptimizer,
    OpportunisticRester,
    StarvationPreventer,
    SustainableCruiser,
)

# Import all food-seeking algorithms
from core.algorithms.food_seeking import (
    AmbushFeeder,
    BottomFeeder,
    CircularHunter,
    CooperativeForager,
    EnergyAwareFoodSeeker,
    FoodMemorySeeker,
    FoodQualityOptimizer,
    GreedyFoodSeeker,
    OpportunisticFeeder,
    PatrolFeeder,
    SurfaceSkimmer,
    ZigZagForager,
)

# Import all poker interaction algorithms
from core.algorithms.poker import (
    PokerChallenger,
    PokerDodger,
    PokerGambler,
    PokerOpportunist,
    SelectivePoker,
)

# Import all predator avoidance algorithms
from core.algorithms.predator_avoidance import (
    BorderHugger,
    DistanceKeeper,
    ErraticEvader,
    FreezeResponse,
    GroupDefender,
    PanicFlee,
    PerpendicularEscape,
    SpiralEscape,
    StealthyAvoider,
    VerticalEscaper,
)

# Import all schooling algorithms
from core.algorithms.schooling import (
    AlignmentMatcher,
    BoidsBehavior,
    DynamicSchooler,
    FrontRunner,
    LeaderFollower,
    LooseSchooler,
    MirrorMover,
    PerimeterGuard,
    SeparationSeeker,
    TightSchooler,
)

# Import all territory/exploration algorithms
from core.algorithms.territory import (
    BoundaryExplorer,
    CenterHugger,
    CornerSeeker,
    NomadicWanderer,
    RandomExplorer,
    RoutePatroller,
    TerritorialDefender,
    WallFollower,
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
    TightSchooler,
    LooseSchooler,
    LeaderFollower,
    AlignmentMatcher,
    SeparationSeeker,
    FrontRunner,
    PerimeterGuard,
    MirrorMover,
    BoidsBehavior,
    DynamicSchooler,
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


def get_algorithm_name(algorithm_index: int) -> str:
    """Get the human-readable name of an algorithm from its index.

    Args:
        algorithm_index: Index (0-47) of the algorithm

    Returns:
        Algorithm name (e.g., "greedy_food_seeker") or "Unknown"
    """
    if 0 <= algorithm_index < len(ALL_ALGORITHMS):
        algorithm_class = ALL_ALGORITHMS[algorithm_index]
        # Create a temporary instance to get its algorithm_id
        instance = algorithm_class()
        return instance.algorithm_id
    return "Unknown"


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


def inherit_algorithm_with_mutation(
    parent_algorithm: BehaviorAlgorithm, mutation_rate: float = 0.15, mutation_strength: float = 0.2
) -> BehaviorAlgorithm:
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


def crossover_algorithms(
    parent1_algorithm: BehaviorAlgorithm,
    parent2_algorithm: BehaviorAlgorithm,
    mutation_rate: float = 0.15,
    mutation_strength: float = 0.2,
    algorithm_switch_rate: float = 0.1,
) -> BehaviorAlgorithm:
    """Create offspring algorithm by crossing over both parents' algorithms.

    This function allows for:
    1. Inheriting the algorithm TYPE from one parent
    2. Blending PARAMETERS from both parents (if they have the same algorithm)
    3. Randomly switching to the other parent's algorithm type
    4. Mutation of parameters

    Args:
        parent1_algorithm: First parent's behavior algorithm
        parent2_algorithm: Second parent's behavior algorithm
        mutation_rate: Probability of each parameter mutating
        mutation_strength: Magnitude of mutations
        algorithm_switch_rate: Probability of switching to other parent's algorithm type

    Returns:
        New algorithm instance with blended/crossed-over parameters
    """
    # Determine which algorithm type to inherit
    if parent1_algorithm is None and parent2_algorithm is None:
        # Both parents have no algorithm, create random
        return get_random_algorithm()
    elif parent1_algorithm is None:
        # Only parent2 has algorithm
        return inherit_algorithm_with_mutation(parent2_algorithm, mutation_rate, mutation_strength)
    elif parent2_algorithm is None:
        # Only parent1 has algorithm
        return inherit_algorithm_with_mutation(parent1_algorithm, mutation_rate, mutation_strength)

    # Both parents have algorithms
    same_type = type(parent1_algorithm) == type(parent2_algorithm)

    # Decide which parent's algorithm type to use (or switch with small probability)
    if random.random() < algorithm_switch_rate:
        # Rare mutation: switch to a completely different algorithm
        return get_random_algorithm()

    if same_type:
        # CASE 1: Both parents have same algorithm type
        # Blend parameters from both parents
        offspring = parent1_algorithm.__class__()

        # For each parameter, blend from both parents
        for param_key in parent1_algorithm.parameters:
            if param_key in parent2_algorithm.parameters:
                val1 = parent1_algorithm.parameters[param_key]
                val2 = parent2_algorithm.parameters[param_key]

                # Skip non-numeric parameters
                if not isinstance(val1, (int, float)) or not isinstance(val2, (int, float)):
                    offspring.parameters[param_key] = val1 if random.random() < 0.5 else val2
                    continue

                # Crossover: randomly blend from both parents
                if random.random() < 0.5:
                    # Averaging (Mendelian inheritance)
                    offspring.parameters[param_key] = (val1 + val2) / 2.0
                else:
                    # Random selection (dominant gene)
                    offspring.parameters[param_key] = val1 if random.random() < 0.5 else val2

            elif param_key in parent1_algorithm.parameters:
                # Only parent1 has this parameter
                offspring.parameters[param_key] = parent1_algorithm.parameters[param_key]

        # Add any parameters from parent2 that parent1 doesn't have
        for param_key in parent2_algorithm.parameters:
            if param_key not in offspring.parameters:
                offspring.parameters[param_key] = parent2_algorithm.parameters[param_key]

    else:
        # CASE 2: Different algorithm types
        # Choose one parent's algorithm type (50/50 chance)
        chosen_parent = parent1_algorithm if random.random() < 0.5 else parent2_algorithm
        offspring = chosen_parent.__class__()
        offspring.parameters = chosen_parent.parameters.copy()

    # Apply mutations to offspring parameters
    offspring.mutate_parameters(mutation_rate, mutation_strength)

    return offspring


def crossover_algorithms_weighted(
    parent1_algorithm: BehaviorAlgorithm,
    parent2_algorithm: BehaviorAlgorithm,
    parent1_weight: float = 0.5,
    mutation_rate: float = 0.15,
    mutation_strength: float = 0.2,
    algorithm_switch_rate: float = 0.1,
) -> BehaviorAlgorithm:
    """Create offspring algorithm with weighted contributions from parents.

    This allows for unequal genetic contributions, useful when one parent
    has proven superior fitness (e.g., poker winner).

    Args:
        parent1_algorithm: First parent's behavior algorithm
        parent2_algorithm: Second parent's behavior algorithm
        parent1_weight: How much parent1 contributes (0.0-1.0)
        mutation_rate: Probability of each parameter mutating
        mutation_strength: Magnitude of mutations
        algorithm_switch_rate: Probability of switching to random algorithm

    Returns:
        New algorithm instance with weighted blended parameters
    """
    # Clamp weight to valid range
    parent1_weight = max(0.0, min(1.0, parent1_weight))
    parent2_weight = 1.0 - parent1_weight

    # Determine which algorithm type to inherit
    if parent1_algorithm is None and parent2_algorithm is None:
        return get_random_algorithm()
    elif parent1_algorithm is None:
        return inherit_algorithm_with_mutation(parent2_algorithm, mutation_rate, mutation_strength)
    elif parent2_algorithm is None:
        return inherit_algorithm_with_mutation(parent1_algorithm, mutation_rate, mutation_strength)

    # Both parents have algorithms
    same_type = type(parent1_algorithm) == type(parent2_algorithm)

    # Weighted decision: switch to random algorithm with small probability
    if random.random() < algorithm_switch_rate:
        return get_random_algorithm()

    if same_type:
        # CASE 1: Both parents have same algorithm type
        # Blend parameters using weights
        offspring = parent1_algorithm.__class__()

        for param_key in parent1_algorithm.parameters:
            if param_key in parent2_algorithm.parameters:
                val1 = parent1_algorithm.parameters[param_key]
                val2 = parent2_algorithm.parameters[param_key]

                # Skip non-numeric parameters
                if not isinstance(val1, (int, float)) or not isinstance(val2, (int, float)):
                    offspring.parameters[param_key] = (
                        val1 if random.random() < parent1_weight else val2
                    )
                    continue

                # Weighted average based on parent contributions
                offspring.parameters[param_key] = val1 * parent1_weight + val2 * parent2_weight

            elif param_key in parent1_algorithm.parameters:
                offspring.parameters[param_key] = parent1_algorithm.parameters[param_key]

        # Add parameters from parent2 that parent1 doesn't have
        for param_key in parent2_algorithm.parameters:
            if param_key not in offspring.parameters:
                offspring.parameters[param_key] = parent2_algorithm.parameters[param_key]

    else:
        # CASE 2: Different algorithm types
        # Choose based on weight (parent1_weight probability of choosing parent1)
        chosen_parent = parent1_algorithm if random.random() < parent1_weight else parent2_algorithm
        offspring = chosen_parent.__class__()
        offspring.parameters = chosen_parent.parameters.copy()

    # Apply mutations to offspring parameters
    offspring.mutate_parameters(mutation_rate, mutation_strength)

    return offspring


# Export all symbols
__all__ = [
    # Base
    "BehaviorAlgorithm",
    "ALGORITHM_PARAMETER_BOUNDS",
    "Vector2",
    # Food seeking
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
    "CooperativeForager",
    # Predator avoidance
    "PanicFlee",
    "StealthyAvoider",
    "FreezeResponse",
    "ErraticEvader",
    "VerticalEscaper",
    "GroupDefender",
    "SpiralEscape",
    "BorderHugger",
    "PerpendicularEscape",
    "DistanceKeeper",
    # Schooling
    "TightSchooler",
    "LooseSchooler",
    "LeaderFollower",
    "AlignmentMatcher",
    "SeparationSeeker",
    "FrontRunner",
    "PerimeterGuard",
    "MirrorMover",
    "BoidsBehavior",
    "DynamicSchooler",
    # Energy management
    "EnergyConserver",
    "BurstSwimmer",
    "OpportunisticRester",
    "EnergyBalancer",
    "SustainableCruiser",
    "StarvationPreventer",
    "MetabolicOptimizer",
    "AdaptivePacer",
    # Territory/exploration
    "TerritorialDefender",
    "RandomExplorer",
    "WallFollower",
    "CornerSeeker",
    "CenterHugger",
    "RoutePatroller",
    "BoundaryExplorer",
    "NomadicWanderer",
    # Poker interactions
    "PokerChallenger",
    "PokerDodger",
    "PokerGambler",
    "SelectivePoker",
    "PokerOpportunist",
    # Utilities
    "ALL_ALGORITHMS",
    "get_algorithm_index",
    "get_algorithm_name",
    "get_random_algorithm",
    "get_algorithm_by_id",
    "inherit_algorithm_with_mutation",
    "crossover_algorithms",
    "crossover_algorithms_weighted",
]
