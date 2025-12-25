"""Benchmark suite definitions for poker evolution measurement.

This module defines the structured sub-tournament system that isolates
different skill signals for measuring pure poker playing strength.

Sub-tournament categories:
- FISH_VS_BASELINES: Measures ability to exploit weak/moderate opponents
- FISH_VS_FISH: Measures intra-population relative skill
- FISH_VS_PLANTS: Ecosystem-specific metric
- POPULATION_SKILL: Overall population fitness tracking
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class BenchmarkCategory(Enum):
    """Different benchmark tournament categories."""

    FISH_VS_BASELINES = "fish_vs_baselines"  # Ability to exploit weak play
    FISH_VS_FISH = "fish_vs_fish"  # Intra-population skill
    FISH_VS_PLANTS = "fish_vs_plants"  # Ecosystem-specific
    POPULATION_SKILL = "population_skill"  # Overall population fitness


class BaselineDifficulty(Enum):
    """Difficulty tiers for baseline opponents."""

    TRIVIAL = 1  # Should crush these (always_fold, random)
    WEAK = 2  # Should beat consistently (calling station, rock)
    MODERATE = 3  # Competitive games (TAG, LAG)
    STRONG = 4  # Challenging opponents (balanced, maniac)
    EXPERT = 5  # Optimal opponents (GTO expert)


@dataclass
class BaselineOpponent:
    """Definition of a fixed baseline opponent for benchmarking."""

    name: str
    strategy_id: str
    description: str
    difficulty: BaselineDifficulty
    weight: float = 1.0  # Weight in aggregate scoring

    def __post_init__(self):
        """Validate baseline opponent definition."""
        if self.weight <= 0:
            raise ValueError(f"Weight must be positive, got {self.weight}")


# Comprehensive baseline opponent suite
BASELINE_OPPONENTS: List[BaselineOpponent] = [
    # Trivial baselines (difficulty 1) - sanity checks
    BaselineOpponent(
        name="Always Fold",
        strategy_id="always_fold",
        description="Folds everything except AA/KK. Any strategy should crush this.",
        difficulty=BaselineDifficulty.TRIVIAL,
        weight=0.5,  # Lower weight - easy to beat
    ),
    BaselineOpponent(
        name="Random",
        strategy_id="random",
        description="Random actions with equal probability. Pure noise baseline.",
        difficulty=BaselineDifficulty.TRIVIAL,
        weight=0.5,
    ),
    # Weak baselines (difficulty 2) - exploitable patterns
    BaselineOpponent(
        name="Calling Station",
        strategy_id="loose_passive",
        description="Calls everything, rarely raises. Classic exploitable pattern.",
        difficulty=BaselineDifficulty.WEAK,
        weight=1.0,
    ),
    BaselineOpponent(
        name="Rock",
        strategy_id="tight_passive",
        description="Only plays premium hands, rarely aggressive. Easy to steal from.",
        difficulty=BaselineDifficulty.WEAK,
        weight=1.0,
    ),
    # Moderate baselines (difficulty 3) - standard strategies
    BaselineOpponent(
        name="TAG Bot",
        strategy_id="tight_aggressive",
        description="Tight-aggressive standard strategy. Solid fundamentals.",
        difficulty=BaselineDifficulty.MODERATE,
        weight=1.5,  # Higher weight - important benchmark
    ),
    BaselineOpponent(
        name="LAG Bot",
        strategy_id="loose_aggressive",
        description="Loose-aggressive pressure player. Tests defensive play.",
        difficulty=BaselineDifficulty.MODERATE,
        weight=1.5,
    ),
    # Strong baselines (difficulty 4) - challenging opponents
    BaselineOpponent(
        name="Balanced",
        strategy_id="balanced",
        description="GTO-inspired balanced play. Hard to exploit.",
        difficulty=BaselineDifficulty.STRONG,
        weight=2.0,  # Highest weight - gold standard
    ),
    BaselineOpponent(
        name="Maniac",
        strategy_id="maniac",
        description="Hyper-aggressive, unpredictable. Tests patience and reads.",
        difficulty=BaselineDifficulty.STRONG,
        weight=1.0,
    ),
    # Expert baselines (difficulty 5) - near optimal
    BaselineOpponent(
        name="GTO Expert",
        strategy_id="gto_expert",
        description="Uses optimal frequencies, polarized ranges, and equity-based sizing.",
        difficulty=BaselineDifficulty.EXPERT,
        weight=2.5,  # Highest difficulty ceiling
    ),
]


def get_baselines_by_difficulty(
    difficulty: BaselineDifficulty,
) -> List[BaselineOpponent]:
    """Get all baselines at a specific difficulty level."""
    return [b for b in BASELINE_OPPONENTS if b.difficulty == difficulty]


def get_baseline_ids_by_tier(tier: str) -> List[str]:
    """Get baseline strategy IDs by tier name.

    Args:
        tier: One of "weak", "moderate", "strong", or "all"

    Returns:
        List of strategy IDs
    """
    if tier == "weak":
        difficulties = [BaselineDifficulty.TRIVIAL, BaselineDifficulty.WEAK]
    elif tier == "moderate":
        difficulties = [BaselineDifficulty.MODERATE]
    elif tier == "strong":
        difficulties = [BaselineDifficulty.STRONG]
    elif tier == "expert":
        difficulties = [BaselineDifficulty.EXPERT]
    elif tier == "all":
        return [b.strategy_id for b in BASELINE_OPPONENTS]
    else:
        raise ValueError(f"Unknown tier: {tier}. Use weak, moderate, strong, expert, or all")

    return [b.strategy_id for b in BASELINE_OPPONENTS if b.difficulty in difficulties]


@dataclass
class SubTournamentConfig:
    """Configuration for a single sub-tournament."""

    category: BenchmarkCategory
    hands_per_match: int = 500  # Hands per duplicate set per seat
    num_duplicate_sets: int = 20  # Number of seeds for variance reduction
    replicates: int = 1  # Number of times to run for confidence intervals
    baseline_opponents: List[str] = field(default_factory=list)

    def total_hands_per_opponent(self) -> int:
        """Total hands played against each opponent."""
        # Each duplicate set plays 2 matches (one per seat)
        return self.hands_per_match * self.num_duplicate_sets * 2 * self.replicates


@dataclass
class ComprehensiveBenchmarkConfig:
    """Full benchmark suite configuration."""

    # Sub-tournament configurations
    fish_vs_baselines: SubTournamentConfig = field(
        default_factory=lambda: SubTournamentConfig(
            category=BenchmarkCategory.FISH_VS_BASELINES,
            hands_per_match=300,
            num_duplicate_sets=15,
            replicates=1,
            baseline_opponents=[
                "always_fold",
                "random",
                "loose_passive",
                "tight_passive",
                "tight_aggressive",
                "loose_aggressive",
                "balanced",
            ],
        )
    )

    fish_vs_fish: SubTournamentConfig = field(
        default_factory=lambda: SubTournamentConfig(
            category=BenchmarkCategory.FISH_VS_FISH,
            hands_per_match=200,
            num_duplicate_sets=10,
            replicates=1,
        )
    )

    fish_vs_plants: SubTournamentConfig = field(
        default_factory=lambda: SubTournamentConfig(
            category=BenchmarkCategory.FISH_VS_PLANTS,
            hands_per_match=150,
            num_duplicate_sets=8,
            replicates=1,
        )
    )

    # Stake structure (determines bb/100 calculation)
    small_blind: int = 50
    big_blind: int = 100
    starting_stack: int = 10_000  # 100 big blinds

    # Sampling configuration
    top_n_fish: int = 10  # Evaluate top N fish by poker winnings
    random_sample_fish: int = 5  # Also sample random fish for diversity

    # Performance settings
    parallel_evaluation: bool = True
    max_workers: int = 4

    def get_baseline_weights(self) -> Dict[str, float]:
        """Get weight for each baseline opponent."""
        return {b.strategy_id: b.weight for b in BASELINE_OPPONENTS}


# Quick benchmark config for frequent evaluation
# Increased sample size for better statistical accuracy:
# - 100 hands × 10 duplicate sets = 2000 hands per baseline (was 500)
# - Added missing weak baselines for balanced coverage
# - Increased fish sample from 5 to 8
QUICK_BENCHMARK_CONFIG = ComprehensiveBenchmarkConfig(
    fish_vs_baselines=SubTournamentConfig(
        category=BenchmarkCategory.FISH_VS_BASELINES,
        hands_per_match=100,
        num_duplicate_sets=10,
        replicates=1,
        baseline_opponents=[
            "always_fold",
            "random",
            "loose_passive",
            "tight_passive",
            "tight_aggressive",
            "loose_aggressive",
            "balanced",
            "gto_expert",
        ],
    ),
    top_n_fish=5,
    random_sample_fish=3,
)

# Full benchmark config for detailed analysis (higher sample size)
FULL_BENCHMARK_CONFIG = ComprehensiveBenchmarkConfig(
    fish_vs_baselines=SubTournamentConfig(
        category=BenchmarkCategory.FISH_VS_BASELINES,
        hands_per_match=500,
        num_duplicate_sets=25,
        replicates=2,
        baseline_opponents=[
            "always_fold",
            "random",
            "loose_passive",
            "tight_passive",
            "tight_aggressive",
            "loose_aggressive",
            "balanced",
            "maniac",
            "gto_expert",
        ],
    ),
    top_n_fish=15,
    random_sample_fish=10,
)
