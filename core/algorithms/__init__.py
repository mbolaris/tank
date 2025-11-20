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
    AggressiveHunter,
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
    SpiralForager,
    SurfaceSkimmer,
    ZigZagForager,
)

# Import all poker interaction algorithms
from core.algorithms.poker import (
    PokerBluffer,
    PokerChallenger,
    PokerConservative,
    PokerDodger,
    PokerGambler,
    PokerOpportunist,
    PokerStrategist,
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
    AggressiveHunter,  # NEW: High-speed food pursuit
    SpiralForager,  # NEW: Systematic spiral search pattern
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
    PokerStrategist,
    PokerBluffer,
    PokerConservative,
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


def get_random_algorithm(rng: Optional[random.Random] = None) -> BehaviorAlgorithm:
    """Get a random behavior algorithm instance."""
    rng = rng or random
    algorithm_class = rng.choice(ALL_ALGORITHMS)
    return algorithm_class.random_instance()


def get_algorithm_by_id(algorithm_id: str) -> Optional[BehaviorAlgorithm]:
    """Get algorithm instance by ID."""
    for algo_class in ALL_ALGORITHMS:
        instance = algo_class.random_instance()
        if instance.algorithm_id == algorithm_id:
            return instance
    return None


def calculate_adaptive_mutation_factor(
    parent_fitness: Optional[float] = None, generation: Optional[int] = None
) -> float:
    """Calculate adaptive mutation factor based on fitness and generation.

    Successful lineages (high fitness) get reduced mutation.
    Struggling lineages (low fitness) get increased mutation.

    Args:
        parent_fitness: Fitness score (0.0-1.0, higher is better)
        generation: Generation number (for time-based adaptation)

    Returns:
        Adaptive factor (0.5-2.0, where 1.0 is baseline)
    """
    factor = 1.0

    # Fitness-based adaptation
    if parent_fitness is not None:
        if parent_fitness >= 0.7:
            # High fitness: reduce mutation (fine-tuning)
            factor *= 0.6
        elif parent_fitness >= 0.5:
            # Medium fitness: normal mutation
            factor *= 1.0
        elif parent_fitness >= 0.3:
            # Low fitness: increase mutation (exploration)
            factor *= 1.4
        else:
            # Very low fitness: high mutation (radical exploration)
            factor *= 2.0

    # Generation-based adaptation (optional cooling schedule)
    if generation is not None and generation > 50:
        # Gradually reduce mutation over time
        cooling = max(0.7, 1.0 - (generation - 50) / 1000.0)
        factor *= cooling

    return max(0.5, min(2.0, factor))


def inherit_algorithm_with_mutation(
    parent_algorithm: BehaviorAlgorithm,
    mutation_rate: float = 0.15,
    mutation_strength: float = 0.2,
    parent_fitness: Optional[float] = None,
    use_adaptive_mutation: bool = True,
) -> BehaviorAlgorithm:
    """Create offspring algorithm by copying parent and mutating parameters.

    Args:
        parent_algorithm: Parent's behavior algorithm
        mutation_rate: Probability of each parameter mutating
        mutation_strength: Magnitude of mutations
        parent_fitness: Parent's fitness score (0.0-1.0) for adaptive mutation
        use_adaptive_mutation: Whether to use adaptive mutation rates

    Returns:
        New algorithm instance with mutated parameters
    """
    # Create new instance of same algorithm type
    offspring = parent_algorithm.__class__()

    # Copy parent parameters
    offspring.parameters = parent_algorithm.parameters.copy()

    # Calculate adaptive mutation factor
    adaptive_factor = 1.0
    if use_adaptive_mutation and parent_fitness is not None:
        adaptive_factor = calculate_adaptive_mutation_factor(parent_fitness)

    # Mutate with adaptive factor
    offspring.mutate_parameters(
        mutation_rate,
        mutation_strength,
        use_parameter_specific=True,
        adaptive_factor=adaptive_factor,
    )

    return offspring


def _crossover_algorithms_base(
    parent1_algorithm: BehaviorAlgorithm,
    parent2_algorithm: BehaviorAlgorithm,
    parent1_weight: float,
    parent2_weight: float,
    mutation_rate: float,
    mutation_strength: float,
    algorithm_switch_rate: float,
    blend_strategy: str = "weighted",
    mutation_kwargs: Optional[dict] = None,
) -> BehaviorAlgorithm:
    """Base crossover function with common logic extracted.

    Args:
        parent1_algorithm: First parent's behavior algorithm
        parent2_algorithm: Second parent's behavior algorithm
        parent1_weight: Weight for parent1's contribution (0.0-1.0)
        parent2_weight: Weight for parent2's contribution (0.0-1.0)
        mutation_rate: Probability of each parameter mutating
        mutation_strength: Magnitude of mutations
        algorithm_switch_rate: Probability of switching to random algorithm
        blend_strategy: How to blend parameters ("weighted", "average_or_select")
        mutation_kwargs: Additional kwargs for mutate_parameters()

    Returns:
        New algorithm instance with blended parameters
    """
    # Handle edge cases
    if parent1_algorithm is None and parent2_algorithm is None:
        return get_random_algorithm()
    elif parent1_algorithm is None:
        return inherit_algorithm_with_mutation(parent2_algorithm, mutation_rate, mutation_strength)
    elif parent2_algorithm is None:
        return inherit_algorithm_with_mutation(parent1_algorithm, mutation_rate, mutation_strength)

    # Both parents have algorithms
    same_type = type(parent1_algorithm) == type(parent2_algorithm)

    # Decide whether to switch to random algorithm
    if random.random() < algorithm_switch_rate:
        return get_random_algorithm()

    if same_type:
        # CASE 1: Both parents have same algorithm type - blend parameters
        offspring = parent1_algorithm.__class__()

        for param_key in parent1_algorithm.parameters:
            if param_key in parent2_algorithm.parameters:
                val1 = parent1_algorithm.parameters[param_key]
                val2 = parent2_algorithm.parameters[param_key]

                # Handle non-numeric parameters
                if not isinstance(val1, (int, float)) or not isinstance(val2, (int, float)):
                    offspring.parameters[param_key] = (
                        val1 if random.random() < parent1_weight else val2
                    )
                    continue

                # Blend numeric parameters based on strategy
                if blend_strategy == "weighted":
                    # Weighted average
                    offspring_value = val1 * parent1_weight + val2 * parent2_weight
                elif blend_strategy == "average_or_select":
                    # 50% average, 50% random selection
                    if random.random() < 0.5:
                        offspring_value = (val1 + val2) / 2.0
                    else:
                        offspring_value = val1 if random.random() < 0.5 else val2
                else:
                    # Default to weighted
                    offspring_value = val1 * parent1_weight + val2 * parent2_weight

                # Clamp offspring value to parent range to handle floating-point inaccuracies
                parent_min = min(val1, val2)
                parent_max = max(val1, val2)
                offspring.parameters[param_key] = max(min(offspring_value, parent_max), parent_min)

            elif param_key in parent1_algorithm.parameters:
                # Only parent1 has this parameter
                offspring.parameters[param_key] = parent1_algorithm.parameters[param_key]

        # Add any parameters from parent2 that parent1 doesn't have
        for param_key in parent2_algorithm.parameters:
            if param_key not in offspring.parameters:
                offspring.parameters[param_key] = parent2_algorithm.parameters[param_key]

    else:
        # CASE 2: Different algorithm types - choose one parent
        chosen_parent = parent1_algorithm if random.random() < parent1_weight else parent2_algorithm
        offspring = chosen_parent.__class__()
        offspring.parameters = chosen_parent.parameters.copy()

    # Apply mutations to offspring parameters
    if mutation_kwargs:
        offspring.mutate_parameters(mutation_rate, mutation_strength, **mutation_kwargs)
    else:
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
    return _crossover_algorithms_base(
        parent1_algorithm=parent1_algorithm,
        parent2_algorithm=parent2_algorithm,
        parent1_weight=0.5,
        parent2_weight=0.5,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        algorithm_switch_rate=algorithm_switch_rate,
        blend_strategy="average_or_select",
    )


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

    return _crossover_algorithms_base(
        parent1_algorithm=parent1_algorithm,
        parent2_algorithm=parent2_algorithm,
        parent1_weight=parent1_weight,
        parent2_weight=parent2_weight,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        algorithm_switch_rate=algorithm_switch_rate,
        blend_strategy="weighted",
    )


def crossover_poker_algorithms(
    parent1_algorithm: BehaviorAlgorithm,
    parent2_algorithm: BehaviorAlgorithm,
    parent1_poker_wins: int = 0,
    parent2_poker_wins: int = 0,
    mutation_rate: float = 0.12,
    mutation_strength: float = 0.18,
) -> BehaviorAlgorithm:
    """Specialized crossover for poker algorithms with performance-based weighting.

    This function is optimized for poker behavior evolution:
    1. Weights contributions based on poker performance
    2. Uses intelligent parameter blending for synergistic combinations
    3. Lower mutation rates to preserve successful strategies
    4. Special handling for poker-specific parameter types

    Args:
        parent1_algorithm: First parent's behavior algorithm
        parent2_algorithm: Second parent's behavior algorithm
        parent1_poker_wins: Number of poker games parent1 has won
        parent2_poker_wins: Number of poker games parent2 has won
        mutation_rate: Probability of mutation (lower than standard for poker)
        mutation_strength: Magnitude of mutations

    Returns:
        New poker algorithm with intelligently blended parameters
    """
    # Handle edge cases
    if parent1_algorithm is None and parent2_algorithm is None:
        return get_random_algorithm()
    elif parent1_algorithm is None:
        return inherit_algorithm_with_mutation(parent2_algorithm, mutation_rate, mutation_strength)
    elif parent2_algorithm is None:
        return inherit_algorithm_with_mutation(parent1_algorithm, mutation_rate, mutation_strength)

    # Check if these are poker algorithms
    is_poker1 = "poker" in parent1_algorithm.algorithm_id.lower()
    is_poker2 = "poker" in parent2_algorithm.algorithm_id.lower()

    # Calculate performance-based weights
    total_wins = parent1_poker_wins + parent2_poker_wins
    if total_wins > 0:
        parent1_weight = (parent1_poker_wins + 1) / (total_wins + 2)  # Add pseudocounts
    else:
        parent1_weight = 0.5

    parent2_weight = 1.0 - parent1_weight

    # For poker algorithms, use special selection logic
    if is_poker1 and not is_poker2:
        # Only parent1 is poker - strongly prefer it (80%)
        parent1_weight = 0.8
    elif is_poker2 and not is_poker1:
        # Only parent2 is poker - strongly prefer it (80%)
        parent1_weight = 0.2

    # Determine mutation kwargs for poker algorithms
    mutation_kwargs = None
    if is_poker1 or is_poker2:
        # Adaptive mutation based on success rate
        success_rate = max(parent1_poker_wins, parent2_poker_wins) / max(total_wins, 1)
        if success_rate > 0.6:
            adaptive_factor = 0.7  # Successful - fine-tune
        else:
            adaptive_factor = 1.2  # Less successful - explore more

        mutation_kwargs = {"use_parameter_specific": True, "adaptive_factor": adaptive_factor}

    return _crossover_algorithms_base(
        parent1_algorithm=parent1_algorithm,
        parent2_algorithm=parent2_algorithm,
        parent1_weight=parent1_weight,
        parent2_weight=parent2_weight,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        algorithm_switch_rate=0.0,  # Poker algorithms don't randomly switch
        blend_strategy="weighted",
        mutation_kwargs=mutation_kwargs,
    )


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
    "AggressiveHunter",
    "SpiralForager",
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
    "PokerStrategist",
    "PokerBluffer",
    "PokerConservative",
    # Utilities
    "ALL_ALGORITHMS",
    "get_algorithm_index",
    "get_algorithm_name",
    "get_random_algorithm",
    "get_algorithm_by_id",
    "inherit_algorithm_with_mutation",
    "crossover_algorithms",
    "crossover_algorithms_weighted",
    "crossover_poker_algorithms",
    "calculate_adaptive_mutation_factor",
]
