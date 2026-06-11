"""Parameter validation for composable poker strategies.

PokerStrategyValidator is the single owner of the continuous parameter
space defined by ``POKER_SUB_BEHAVIOR_PARAMS``: bounds lookup, clamping
(the runtime enforcement that mutated values stay in their design range),
midpoint defaults, and random sampling within bounds.
"""

import random

from core.poker.strategy.composable.definitions import POKER_SUB_BEHAVIOR_PARAMS


class PokerStrategyValidator:
    """Validates and constrains ComposablePokerStrategy parameters."""

    # Bounds assumed for parameters not present in POKER_SUB_BEHAVIOR_PARAMS.
    FALLBACK_BOUNDS: tuple[float, float] = (0.0, 1.0)
    # Default value bounds for unknown keys when blending parent parameters
    # (midpoint 0.5, matching the historical crossover behavior).
    FALLBACK_DEFAULT_BOUNDS: tuple[float, float] = (0.5, 0.5)

    @classmethod
    def parameter_bounds(cls, key: str) -> tuple[float, float]:
        """Return (low, high) bounds for a parameter key."""
        return POKER_SUB_BEHAVIOR_PARAMS.get(key, cls.FALLBACK_BOUNDS)

    @classmethod
    def clamp(cls, key: str, value: float) -> float:
        """Clamp a parameter value into its design bounds."""
        low, high = cls.parameter_bounds(key)
        return max(low, min(high, value))

    @classmethod
    def clamp_known(cls, key: str, value: float) -> float:
        """Clamp only parameters declared in POKER_SUB_BEHAVIOR_PARAMS.

        Unknown keys pass through unchanged (no fallback bounds), and in-range
        values are returned bit-identical. Never consumes RNG. This is the
        bounds-enforcement primitive used at mutation/crossover boundaries.
        """
        bounds = POKER_SUB_BEHAVIOR_PARAMS.get(key)
        if bounds is None:
            return value
        low, high = bounds
        if value < low:
            return low
        if value > high:
            return high
        return value

    @staticmethod
    def default_parameters() -> dict[str, float]:
        """Midpoint defaults for every known parameter."""
        return {key: (low + high) / 2 for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items()}

    @classmethod
    def parameter_default(cls, key: str) -> float:
        """Midpoint default for a single parameter (0.5 for unknown keys)."""
        default = POKER_SUB_BEHAVIOR_PARAMS.get(key, cls.FALLBACK_DEFAULT_BOUNDS)
        return (default[0] + default[1]) / 2

    @staticmethod
    def random_parameters(rng: random.Random) -> dict[str, float]:
        """Generate random parameters within bounds."""
        return {
            key: rng.uniform(low, high) for key, (low, high) in POKER_SUB_BEHAVIOR_PARAMS.items()
        }
