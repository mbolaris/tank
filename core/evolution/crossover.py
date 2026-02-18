"""Crossover operations for combining parent genomes.

Sexual reproduction in ALife: two successful organisms combine their genes.
The key insight is that BOTH parents survived and reproduced - that's the
only "selection" happening. There's no explicit fitness comparison.

Crossover Modes:
- AVERAGING: Blend parent values (smooth, conservative)
- RECOMBINATION: Pick genes from each parent (more variation)
- WEIGHTED: One parent contributes more (e.g., poker winner)

The weighted mode is particularly important for poker evolution:
when fish reproduce after poker, the winner contributes more DNA,
creating selection pressure for poker skill without explicit fitness.

**API Note**: For production code, prefer the canonical API:
- `Genome.from_parents()` - standard crossover
- `Genome.from_parents_weighted()` - weighted crossover (e.g., poker winner)

The helper functions in this module (blend_values, etc.) are primarily
for testing and internal use.
"""

import random
from enum import Enum
from typing import Optional


class CrossoverMode(Enum):
    """Methods for combining parent genetic values."""

    AVERAGING = "averaging"
    """Simple average of parent values. Most conservative."""

    RECOMBINATION = "recombination"
    """Randomly select from each parent with some blending."""

    WEIGHTED = "weighted"
    """Weighted combination based on parent contributions."""


def blend_values(
    val1: float,
    val2: float,
    weight1: float = 0.5,
    mode: CrossoverMode = CrossoverMode.RECOMBINATION,
    rng: Optional[random.Random] = None,
) -> float:
    """Blend two parent values using the specified crossover mode.

    Args:
        val1: First parent's value
        val2: Second parent's value
        weight1: Weight for first parent (0.0-1.0), second gets (1-weight1)
        mode: Crossover mode to use
        rng: Random number generator

    Returns:
        Blended value
    """
    from core.util.rng import require_rng_param

    rng = require_rng_param(rng, "__init__")
    weight2 = 1.0 - weight1

    if mode == CrossoverMode.AVERAGING:
        # Simple average (ignores weights)
        return (val1 + val2) * 0.5

    elif mode == CrossoverMode.RECOMBINATION:
        # Random selection with some blending
        if rng.random() < 0.5:
            # Pick one parent's value
            return val1 if rng.random() < 0.5 else val2
        else:
            # Blend with some randomness
            return val1 * 0.7 + val2 * 0.15 + (val1 + val2) * 0.075

    elif mode == CrossoverMode.WEIGHTED:
        # Weighted average based on parent contribution
        return val1 * weight1 + val2 * weight2

    # Default to averaging
    return (val1 + val2) * 0.5


def blend_discrete(
    val1: int,
    val2: int,
    weight1: float = 0.5,
    rng: Optional[random.Random] = None,
) -> int:
    """Blend two discrete parent values (probabilistic selection).

    For discrete traits like template_id, we can't average.
    Instead, we select one parent's value with probability
    proportional to their weight.

    Args:
        val1: First parent's value
        val2: Second parent's value
        weight1: Probability of selecting first parent's value
        rng: Random number generator

    Returns:
        Selected value (either val1 or val2)
    """
    from core.util.rng import require_rng_param

    rng = require_rng_param(rng, "__init__")
    return val1 if rng.random() < weight1 else val2


def crossover_dict_values(
    dict1: dict[str, float],
    dict2: dict[str, float],
    weight1: float = 0.5,
    mode: CrossoverMode = CrossoverMode.WEIGHTED,
    rng: Optional[random.Random] = None,
) -> dict[str, float]:
    """Crossover two dictionaries of float values (e.g., algorithm parameters).

    Handles keys that exist in one parent but not the other.

    Args:
        dict1: First parent's dictionary
        dict2: Second parent's dictionary
        weight1: Weight for first parent
        mode: Crossover mode
        rng: Random number generator

    Returns:
        Blended dictionary
    """
    from core.util.rng import require_rng_param

    rng = require_rng_param(rng, "__init__")
    result: dict[str, float] = {}

    # Get all keys from both parents
    all_keys = set(dict1.keys()) | set(dict2.keys())

    for key in all_keys:
        if key in dict1 and key in dict2:
            # Both parents have this key - blend
            result[key] = blend_values(dict1[key], dict2[key], weight1, mode, rng)
        elif key in dict1:
            # Only first parent has this key
            result[key] = dict1[key]
        else:
            # Only second parent has this key
            result[key] = dict2[key]

    return result
