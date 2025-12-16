"""Elo-style rating system for stable poker skill measurement.

This module provides an Elo-inspired rating system that:
1. Reduces variance through K-factor dampening
2. Accounts for opponent strength in calculations
3. Converges to true skill over time
4. Provides confidence intervals based on games played

The rating system assigns each baseline opponent a fixed Elo rating and
updates fish ratings based on their performance (bb/100) against each opponent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Fixed Elo ratings for baseline opponents based on difficulty tier
# These are calibrated so that a "break-even" player is around 1500
BASELINE_ELO_RATINGS: Dict[str, float] = {
    # Trivial opponents (very easy to beat)
    "always_fold": 800.0,
    "random": 900.0,
    # Weak opponents (should beat consistently)
    "loose_passive": 1100.0,  # Calling station
    "tight_passive": 1150.0,  # Rock
    # Moderate opponents (competitive)
    "tight_aggressive": 1400.0,  # TAG
    "loose_aggressive": 1350.0,  # LAG
    # Strong opponents (challenging)
    "balanced": 1600.0,  # GTO-inspired
    "maniac": 1450.0,  # Hyper-aggressive
}

# K-factor controls how much rating changes per game
# Higher K = faster convergence but more volatility
# Lower K = slower convergence but more stability
BASE_K_FACTOR = 32.0

# Rating floor and ceiling
MIN_RATING = 500.0
MAX_RATING = 2500.0

# Initial rating for new fish
INITIAL_RATING = 1200.0

# Games needed for "established" rating (lower K-factor after this)
ESTABLISHED_GAMES_THRESHOLD = 50


@dataclass
class EloRating:
    """Elo rating with confidence information."""

    rating: float = INITIAL_RATING
    games_played: int = 0
    rating_history: List[float] = field(default_factory=list)

    # Performance tracking for confidence
    wins: int = 0  # Games where bb/100 > 5 (clearly winning)
    losses: int = 0  # Games where bb/100 < -5 (clearly losing)
    draws: int = 0  # Games where -5 <= bb/100 <= 5

    def get_k_factor(self) -> float:
        """Get K-factor based on games played.

        New players have higher K for faster convergence.
        Established players have lower K for stability.
        """
        if self.games_played < 10:
            return BASE_K_FACTOR * 2.0  # Fast initial learning
        elif self.games_played < ESTABLISHED_GAMES_THRESHOLD:
            return BASE_K_FACTOR * 1.5  # Moderate learning
        else:
            return BASE_K_FACTOR  # Stable rating

    def get_confidence_interval(self) -> Tuple[float, float]:
        """Get 95% confidence interval for rating.

        Confidence narrows as more games are played.
        Based on approximation: CI_width = 400 / sqrt(games)
        """
        if self.games_played < 2:
            return (MIN_RATING, MAX_RATING)

        # Standard deviation decreases with sqrt(games)
        ci_half_width = 400.0 / math.sqrt(self.games_played)
        ci_half_width = min(ci_half_width, 500.0)  # Cap at reasonable max

        return (
            max(MIN_RATING, self.rating - ci_half_width),
            min(MAX_RATING, self.rating + ci_half_width),
        )

    def is_established(self) -> bool:
        """Check if rating is considered established (stable)."""
        return self.games_played >= ESTABLISHED_GAMES_THRESHOLD


def expected_score(player_rating: float, opponent_rating: float) -> float:
    """Calculate expected score (win probability) using Elo formula.

    Args:
        player_rating: Player's current Elo rating
        opponent_rating: Opponent's Elo rating

    Returns:
        Expected score (0.0 to 1.0)
    """
    return 1.0 / (1.0 + 10.0 ** ((opponent_rating - player_rating) / 400.0))


def bb_per_100_to_score(bb_per_100: float) -> float:
    """Convert bb/100 to a score for Elo calculation.

    Maps bb/100 to a 0-1 scale:
    - bb/100 >= 10: score = 1.0 (dominating)
    - bb/100 = 0: score = 0.5 (break-even)
    - bb/100 <= -10: score = 0.0 (getting crushed)

    Uses sigmoid-like mapping for smooth transitions.
    """
    # Sigmoid transformation centered at 0, scaled to ±10 bb/100
    # This gives 0.5 at 0, ~0.9 at +10, ~0.1 at -10
    clamped = max(-20.0, min(20.0, bb_per_100))
    return 1.0 / (1.0 + math.exp(-clamped / 5.0))


def update_elo_from_benchmark(
    current_rating: EloRating,
    benchmark_id: str,
    bb_per_100: float,
    hands_played: int = 100,
) -> EloRating:
    """Update Elo rating based on benchmark result.

    Args:
        current_rating: Current EloRating object
        benchmark_id: ID of benchmark opponent played
        bb_per_100: Performance in bb/100 against this opponent
        hands_played: Number of hands played (affects confidence)

    Returns:
        Updated EloRating object
    """
    opponent_elo = BASELINE_ELO_RATINGS.get(benchmark_id, 1300.0)

    # Calculate expected and actual scores
    expected = expected_score(current_rating.rating, opponent_elo)
    actual = bb_per_100_to_score(bb_per_100)

    # Get K-factor (adjusted by hands played for this benchmark)
    k = current_rating.get_k_factor()

    # Scale K by hands played (more hands = more reliable result)
    # Minimum 20 hands for any update, max effect at 200+ hands
    hands_factor = min(1.0, max(0.2, hands_played / 200.0))
    k *= hands_factor

    # Update rating
    new_rating = current_rating.rating + k * (actual - expected)
    new_rating = max(MIN_RATING, min(MAX_RATING, new_rating))

    # Update win/loss/draw tracking
    new_wins = current_rating.wins
    new_losses = current_rating.losses
    new_draws = current_rating.draws

    if bb_per_100 > 5:
        new_wins += 1
    elif bb_per_100 < -5:
        new_losses += 1
    else:
        new_draws += 1

    # Create updated rating
    updated = EloRating(
        rating=new_rating,
        games_played=current_rating.games_played + 1,
        rating_history=current_rating.rating_history + [new_rating],
        wins=new_wins,
        losses=new_losses,
        draws=new_draws,
    )

    return updated


def compute_elo_from_benchmarks(
    benchmark_results: Dict[str, float],
    hands_per_benchmark: Dict[str, int],
    initial_rating: Optional[EloRating] = None,
) -> EloRating:
    """Compute Elo rating from a full set of benchmark results.

    Args:
        benchmark_results: Dict mapping benchmark_id to bb/100
        hands_per_benchmark: Dict mapping benchmark_id to hands played
        initial_rating: Optional starting rating (uses default if None)

    Returns:
        Final EloRating after processing all benchmarks
    """
    rating = initial_rating or EloRating()

    # Process benchmarks in order of difficulty (easiest first)
    # This helps with initial rating calibration
    difficulty_order = [
        "always_fold",
        "random",
        "loose_passive",
        "tight_passive",
        "tight_aggressive",
        "loose_aggressive",
        "maniac",
        "balanced",
    ]

    for benchmark_id in difficulty_order:
        if benchmark_id in benchmark_results:
            bb_per_100 = benchmark_results[benchmark_id]
            hands = hands_per_benchmark.get(benchmark_id, 100)
            rating = update_elo_from_benchmark(rating, benchmark_id, bb_per_100, hands)

    return rating


def rating_to_skill_tier(rating: float) -> str:
    """Convert Elo rating to human-readable skill tier.

    Args:
        rating: Elo rating value

    Returns:
        Skill tier string
    """
    if rating < 900:
        return "failing"
    elif rating < 1100:
        return "novice"
    elif rating < 1300:
        return "beginner"
    elif rating < 1450:
        return "intermediate"
    elif rating < 1550:
        return "advanced"
    elif rating < 1700:
        return "expert"
    else:
        return "master"


def rating_to_percentile(rating: float) -> float:
    """Estimate skill percentile from rating.

    Assumes ratings follow approximately normal distribution.
    Returns percentile (0-100).
    """
    # Assume mean=1300, std=150 for typical population
    z = (rating - 1300.0) / 150.0
    # CDF approximation using sigmoid
    percentile = 100.0 / (1.0 + math.exp(-z * 1.5))
    return round(percentile, 1)


@dataclass
class PopulationEloStats:
    """Population-level Elo statistics."""

    mean_rating: float = INITIAL_RATING
    median_rating: float = INITIAL_RATING
    std_rating: float = 0.0
    min_rating: float = INITIAL_RATING
    max_rating: float = INITIAL_RATING

    # Distribution by tier
    tier_distribution: Dict[str, int] = field(default_factory=dict)

    # Best performer
    best_rating: float = INITIAL_RATING
    best_fish_id: Optional[int] = None

    # Confidence metrics
    avg_games_played: float = 0.0
    pct_established: float = 0.0  # % of fish with established ratings


def compute_population_elo_stats(
    fish_ratings: Dict[int, EloRating],
) -> PopulationEloStats:
    """Compute population-level Elo statistics.

    Args:
        fish_ratings: Dict mapping fish_id to EloRating

    Returns:
        PopulationEloStats object
    """
    if not fish_ratings:
        return PopulationEloStats()

    ratings = [r.rating for r in fish_ratings.values()]
    games = [r.games_played for r in fish_ratings.values()]

    # Basic stats
    mean_rating = sum(ratings) / len(ratings)
    sorted_ratings = sorted(ratings)
    median_rating = sorted_ratings[len(sorted_ratings) // 2]

    if len(ratings) > 1:
        variance = sum((r - mean_rating) ** 2 for r in ratings) / len(ratings)
        std_rating = variance ** 0.5
    else:
        std_rating = 0.0

    # Tier distribution
    tier_counts: Dict[str, int] = {}
    for rating in ratings:
        tier = rating_to_skill_tier(rating)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # Best performer
    best_fish_id = max(fish_ratings.items(), key=lambda x: x[1].rating)[0]
    best_rating = fish_ratings[best_fish_id].rating

    # Confidence metrics
    avg_games = sum(games) / len(games) if games else 0.0
    established_count = sum(1 for r in fish_ratings.values() if r.is_established())
    pct_established = (established_count / len(fish_ratings) * 100) if fish_ratings else 0.0

    return PopulationEloStats(
        mean_rating=round(mean_rating, 1),
        median_rating=round(median_rating, 1),
        std_rating=round(std_rating, 1),
        min_rating=round(min(ratings), 1),
        max_rating=round(max(ratings), 1),
        tier_distribution=tier_counts,
        best_rating=round(best_rating, 1),
        best_fish_id=best_fish_id,
        avg_games_played=round(avg_games, 1),
        pct_established=round(pct_established, 1),
    )
