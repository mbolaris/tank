"""Genetic diversity metrics and speciation support.

This module provides tools for measuring and maintaining genetic diversity
in the population. Key capabilities:

- Genetic distance: Euclidean distance between two genomes in trait space
- Population diversity: Shannon entropy and pairwise distance metrics
- Niche detection: Identify genetic clusters (species/niches) in the population
- Fitness sharing: Reduce effective fitness for genetically similar individuals
  to prevent monocultures and maintain exploration of the solution space

These tools support both in-simulation diversity tracking (Layer 0) and
external analysis by contributing agents (Layer 1/2).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.genetics.genome import Genome


# =============================================================================
# Genetic Distance
# =============================================================================

# Trait weights for distance calculation. Physical traits that directly affect
# survival get higher weight; purely cosmetic traits get lower weight.
_PHYSICAL_TRAIT_WEIGHTS: dict[str, float] = {
    "size_modifier": 1.0,
    "fin_size": 0.8,
    "tail_size": 0.8,
    "body_aspect": 0.6,
    "eye_size": 0.7,
    "color_hue": 0.3,  # Cosmetic, low weight
    "pattern_intensity": 0.2,  # Cosmetic, low weight
    "template_id": 0.4,
    "lifespan_modifier": 0.5,
    "pattern_type": 0.1,
}

_BEHAVIORAL_TRAIT_WEIGHTS: dict[str, float] = {
    "aggression": 1.0,
    "social_tendency": 1.0,
    "pursuit_aggression": 1.0,
    "prediction_skill": 0.8,
    "hunting_stamina": 0.8,
    "asexual_reproduction_chance": 0.6,
}

# Weights for composable behavior sub-behaviors (discrete)
_BEHAVIOR_MISMATCH_WEIGHT: float = 0.5  # Per sub-behavior mismatch


def _normalize_trait(value: float, min_val: float, max_val: float) -> float:
    """Normalize a trait value to [0, 1] range."""
    span = max_val - min_val
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / span))


def _circular_distance(a: float, b: float) -> float:
    """Distance on a circular [0, 1] scale (for hue)."""
    diff = abs(a - b) % 1.0
    return min(diff, 1.0 - diff)


# Trait comparison kinds for the precomputed distance table.
_KIND_CONTINUOUS = 0
_KIND_DISCRETE = 1
_KIND_HUE = 2

# Lazily built once from the trait specs (deferred to avoid circular imports):
# - rows: (is_physical, trait_name, kind, weight, min_val, max_val)
# - kind_weight_rows: (kind, weight) per row, for the distance inner loop
# - base_total_weight: sum of all row weights, accumulated in row order so the
#   floating-point result matches an incremental per-row summation exactly
_trait_table: (
    tuple[
        list[tuple[bool, str, int, float, float, float]],
        list[tuple[int, float]],
        float,
    ]
    | None
) = None

# OPTIMIZATION: Precomputed per-kind index+weight lists for branch-free inner loops.
# Built alongside _trait_table; each entry is a tuple of (index, weight) for that kind.
_continuous_iw: list[tuple[int, float]] = []
_discrete_iw: list[tuple[int, float]] = []
_hue_iw: list[tuple[int, float]] = []


def _get_trait_table() -> tuple[
    list[tuple[bool, str, int, float, float, float]],
    list[tuple[int, float]],
    float,
]:
    global _trait_table, _continuous_iw, _discrete_iw, _hue_iw
    if _trait_table is None:
        from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
        from core.genetics.physical import PHYSICAL_TRAIT_SPECS

        rows: list[tuple[bool, str, int, float, float, float]] = []
        for spec in PHYSICAL_TRAIT_SPECS:
            weight = _PHYSICAL_TRAIT_WEIGHTS.get(spec.name, 0.5)
            if spec.name == "color_hue":
                kind = _KIND_HUE
            elif spec.discrete:
                kind = _KIND_DISCRETE
            else:
                kind = _KIND_CONTINUOUS
            rows.append((True, spec.name, kind, weight, spec.min_val, spec.max_val))
        for spec in BEHAVIORAL_TRAIT_SPECS:
            weight = _BEHAVIORAL_TRAIT_WEIGHTS.get(spec.name, 0.5)
            rows.append((False, spec.name, _KIND_CONTINUOUS, weight, spec.min_val, spec.max_val))

        kind_weight_rows = [(kind, weight) for _, _, kind, weight, _, _ in rows]
        base_total_weight = 0.0
        for _, weight in kind_weight_rows:
            base_total_weight += weight
        _trait_table = (rows, kind_weight_rows, base_total_weight)

        # OPTIMIZATION: Build per-kind index+weight lists for branch-free distance loops.
        _continuous_iw = []
        _discrete_iw = []
        _hue_iw = []
        for i, (kind, weight) in enumerate(kind_weight_rows):
            if kind == _KIND_CONTINUOUS:
                _continuous_iw.append((i, weight))
            elif kind == _KIND_DISCRETE:
                _discrete_iw.append((i, weight))
            else:
                _hue_iw.append((i, weight))

    return _trait_table


def _build_distance_profile(
    genome: Genome,
) -> tuple[tuple[float | int, ...], tuple[object, ...] | None]:
    """Precompute the per-genome values genetic_distance compares.

    Continuous traits are stored already normalized, discrete traits as ints,
    and hue as the raw float, so the distance loop needs no trait lookups.
    """
    from core.genetics.trait_utils import get_trait_value

    rows, _, _ = _get_trait_table()
    values: list[float | int] = []
    for is_physical, name, kind, _weight, min_val, max_val in rows:
        traits = genome.physical if is_physical else genome.behavioral
        val = get_trait_value(getattr(traits, name), default=0.0)
        if kind == _KIND_HUE:
            values.append(float(val))
        elif kind == _KIND_DISCRETE:
            values.append(int(val))
        else:
            values.append(_normalize_trait(float(val), min_val, max_val))

    behavior = genome.behavioral.behavior
    behavior_key: tuple[object, ...] | None = None
    if behavior is not None and behavior.value is not None:
        cb = behavior.value
        behavior_key = (cb.threat_response, cb.food_approach, cb.social_mode, cb.poker_engagement)
    return (tuple(values), behavior_key)


def _distance_profile(
    genome: Genome,
) -> tuple[tuple[float | int, ...], tuple[object, ...] | None]:
    """Return the genome's cached distance profile, building it if needed.

    The cache lives on the genome (cleared by Genome.invalidate_caches) and is
    valid because distance-relevant traits are fixed after genome creation:
    mutation happens when offspring genomes are created, never in place.
    """
    profile = getattr(genome, "_distance_profile_cache", None)
    if profile is None:
        profile = _build_distance_profile(genome)
        try:
            object.__setattr__(genome, "_distance_profile_cache", profile)
        except AttributeError:
            pass  # Duck-typed genome that rejects the attribute; skip caching
    return profile


def genetic_distance(genome1: Genome, genome2: Genome) -> float:
    """Calculate genetic distance between two genomes.

    Returns a non-negative float where 0.0 means identical genomes and
    higher values mean more genetic difference. The distance is a weighted
    Euclidean distance across all trait dimensions, normalized so that
    each trait contributes proportionally to its weight.

    This distance metric is used for:
    - Fitness sharing (diversity-aware reproduction)
    - Speciation (grouping genetically similar fish)
    - Diversity tracking (population-level metrics)

    Args:
        genome1: First genome
        genome2: Second genome

    Returns:
        Non-negative genetic distance (typically 0.0 to ~5.0)
    """
    _, _, total_weight = _get_trait_table()
    values1, behavior1 = _distance_profile(genome1)
    values2, behavior2 = _distance_profile(genome2)

    # OPTIMIZATION: Three tight branch-free loops instead of one loop with
    # a per-element `if kind` branch. Per-kind index+weight lists are built
    # once at table build time and stored in module-level lists.
    distance_sq = 0.0

    # Continuous traits: squared Euclidean distance
    for i, weight in _continuous_iw:
        d = values1[i] - values2[i]
        distance_sq += weight * d * d

    # Discrete traits: mismatch penalty (0 or 1)
    for i, weight in _discrete_iw:
        if values1[i] != values2[i]:
            distance_sq += weight

    # Hue traits: circular distance
    for i, weight in _hue_iw:
        d = _circular_distance(values1[i], values2[i])
        distance_sq += weight * d * d

    # Composable behavior sub-behavior distances (discrete mismatches)
    if behavior1 is not None and behavior2 is not None:
        for a, b in zip(behavior1, behavior2, strict=True):
            if a != b:
                distance_sq += _BEHAVIOR_MISMATCH_WEIGHT
                total_weight += _BEHAVIOR_MISMATCH_WEIGHT

    if total_weight <= 0:
        return 0.0

    return math.sqrt(distance_sq / total_weight)


# =============================================================================
# Population Diversity Metrics
# =============================================================================


def population_diversity(genomes: Sequence[Genome]) -> dict[str, float]:
    """Calculate diversity metrics for a population of genomes.

    Returns a dictionary with:
    - mean_distance: Average pairwise genetic distance
    - max_distance: Maximum pairwise genetic distance
    - min_distance: Minimum pairwise genetic distance (closest pair)
    - behavioral_entropy: Shannon entropy of composable behavior types
    - num_niches: Estimated number of genetic niches (clusters)
    - effective_diversity: Combined diversity score (0.0 = monoculture, 1.0 = max diverse)

    For large populations, uses sampling to keep computation tractable.

    Args:
        genomes: Sequence of Genome objects

    Returns:
        Dictionary of diversity metrics
    """
    n = len(genomes)
    if n < 2:
        return {
            "mean_distance": 0.0,
            "max_distance": 0.0,
            "min_distance": 0.0,
            "behavioral_entropy": 0.0,
            "num_niches": min(n, 1),
            "effective_diversity": 0.0,
        }

    # For large populations, sample pairs to keep O(n^2) tractable
    max_pairs = 500
    total_possible = n * (n - 1) // 2

    distances: list[float] = []

    if total_possible <= max_pairs:
        # Compute all pairs
        for i in range(n):
            for j in range(i + 1, n):
                distances.append(genetic_distance(genomes[i], genomes[j]))
    else:
        # Sample random pairs (deterministic via sorted indices)
        import random as _random

        sample_rng = _random.Random(42)  # Deterministic sampling
        seen = set()
        while len(distances) < max_pairs:
            i = sample_rng.randint(0, n - 1)
            j = sample_rng.randint(0, n - 1)
            if i == j:
                continue
            pair = (min(i, j), max(i, j))
            if pair in seen:
                continue
            seen.add(pair)
            distances.append(genetic_distance(genomes[i], genomes[j]))

    mean_dist = sum(distances) / len(distances) if distances else 0.0
    max_dist = max(distances) if distances else 0.0
    min_dist = min(distances) if distances else 0.0

    # Behavioral entropy: distribution of composable behavior types
    behavior_counts: dict[str, int] = {}
    for genome in genomes:
        b = genome.behavioral.behavior
        if b is not None and b.value is not None:
            bid = b.value.behavior_id
        else:
            bid = "none"
        behavior_counts[bid] = behavior_counts.get(bid, 0) + 1

    behavioral_entropy = _shannon_entropy(list(behavior_counts.values()), n)

    # Estimate niches using simple threshold-based clustering
    niche_threshold = 0.3  # Genomes closer than this are in the same niche
    num_niches = _estimate_niches(genomes, niche_threshold, max_sample=50)

    # Effective diversity: combines distance spread and behavioral variety
    # Normalize to 0-1 range (assuming max realistic distance ~3.0)
    distance_score = min(1.0, mean_dist / 2.0)
    max_entropy = math.log(max(len(behavior_counts), 1)) if behavior_counts else 0.0
    entropy_score = behavioral_entropy / max(max_entropy, 0.001) if max_entropy > 0 else 0.0
    effective_diversity = 0.5 * distance_score + 0.5 * entropy_score

    return {
        "mean_distance": round(mean_dist, 4),
        "max_distance": round(max_dist, 4),
        "min_distance": round(min_dist, 4),
        "behavioral_entropy": round(behavioral_entropy, 4),
        "num_niches": num_niches,
        "effective_diversity": round(effective_diversity, 4),
    }


def _shannon_entropy(counts: list[int], total: int) -> float:
    """Calculate Shannon entropy from count distribution."""
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count > 0:
            p = count / total
            entropy -= p * math.log(p)
    return entropy


def _estimate_niches(
    genomes: Sequence[Genome],
    threshold: float,
    max_sample: int = 50,
) -> int:
    """Estimate the number of genetic niches using greedy clustering.

    Uses a simple leader-based algorithm: iterate through genomes and create
    a new niche whenever a genome is farther than `threshold` from all
    existing niche centers.

    Args:
        genomes: Population of genomes
        threshold: Distance threshold for niche membership
        max_sample: Maximum number of genomes to sample for efficiency

    Returns:
        Estimated number of niches
    """
    n = len(genomes)
    if n == 0:
        return 0

    # Sample for large populations
    if n > max_sample:
        import random as _random

        sample_rng = _random.Random(42)
        indices = sample_rng.sample(range(n), max_sample)
        sample = [genomes[i] for i in sorted(indices)]
    else:
        sample = list(genomes)

    niche_centers: list[Genome] = [sample[0]]

    for genome in sample[1:]:
        is_new_niche = True
        for center in niche_centers:
            if genetic_distance(genome, center) < threshold:
                is_new_niche = False
                break
        if is_new_niche:
            niche_centers.append(genome)

    return len(niche_centers)


# =============================================================================
# Fitness Sharing
# =============================================================================


def sharing_factor(
    genome: Genome,
    population: Sequence[Genome],
    sigma: float = 0.5,
) -> float:
    """Calculate the fitness sharing factor for a genome.

    Fitness sharing reduces the effective fitness of individuals that are
    genetically similar to many others, preventing any single genotype from
    dominating the population. This encourages exploration of diverse strategies.

    The sharing factor is the sum of sharing values from all other individuals:
        sh(d) = 1 - (d/sigma)^2 if d < sigma, else 0

    A higher sharing factor means more neighbors, so effective fitness should
    be divided by this value.

    Args:
        genome: The genome to calculate sharing for
        population: All genomes in the population
        sigma: Sharing radius - genomes closer than this share fitness

    Returns:
        Sharing factor >= 1.0 (1.0 means no neighbors within sigma)
    """
    niche_count = 1.0  # Count self
    for other in population:
        if other is genome:
            continue
        d = genetic_distance(genome, other)
        if d < sigma:
            # Triangular sharing function
            niche_count += 1.0 - (d / sigma) ** 2

    return niche_count


def diversity_bonus(
    genome: Genome,
    population: Sequence[Genome],
    sigma: float = 0.5,
    bonus_weight: float = 0.1,
) -> float:
    """Calculate a diversity bonus for reproduction decisions.

    Returns a value between 0.0 and bonus_weight that rewards genetically
    unique individuals. This can be added to reproduction probability to
    give rare genotypes a slight reproductive advantage.

    Args:
        genome: The genome to evaluate
        population: All genomes in the population
        sigma: Sharing radius
        bonus_weight: Maximum bonus value

    Returns:
        Diversity bonus in [0.0, bonus_weight]
    """
    sf = sharing_factor(genome, population, sigma)
    # Inverse relationship: fewer neighbors = higher bonus
    # sf=1 (no neighbors) -> full bonus, sf=10 (crowded) -> ~10% bonus
    return bonus_weight / sf
