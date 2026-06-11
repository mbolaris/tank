"""Unified parameter-bounds registry (backlog item 3.2).

Composes the three existing bounds tables WITHOUT moving them; the source
modules remain the single source of truth for their domains:

- ``"behavior"``: ``core.algorithms.composable.definitions.SUB_BEHAVIOR_PARAMS``
  (the 28 continuous params shared by all composable tank behaviors)
- ``"poker"``: ``core.poker.strategy.composable.definitions.POKER_SUB_BEHAVIOR_PARAMS``
  (clamping is delegated to ``PokerStrategyValidator``, the single owner of
  that parameter space)
- ``"algorithm:<algorithm_id>"``: one domain per entry in
  ``core.algorithms.base.ALGORITHM_PARAMETER_BOUNDS`` (per-algorithm params)

Determinism contract (relied upon by the evolution loop):

- Clamping never consumes RNG.
- Values already inside their design range are returned unchanged
  (bit-identical), so clamping in-range populations cannot alter
  seeded benchmark trajectories.
- Parameters without declared bounds are never modified.
"""

from collections.abc import Iterator, Mapping
from typing import Any

from core.algorithms.base import ALGORITHM_PARAMETER_BOUNDS
from core.algorithms.composable.definitions import SUB_BEHAVIOR_PARAMS
from core.poker.strategy.composable.definitions import POKER_SUB_BEHAVIOR_PARAMS
from core.poker.strategy.composable.validator import PokerStrategyValidator

DOMAIN_BEHAVIOR = "behavior"
DOMAIN_POKER = "poker"
ALGORITHM_DOMAIN_PREFIX = "algorithm:"


class ParameterRegistry:
    """Read-only composition of the three parameter-bounds tables.

    All methods are class-level: the registry holds no state of its own and
    always reads through to the source tables, so it can never drift from
    them.
    """

    @staticmethod
    def domains() -> list[str]:
        """All known domains: 'behavior', 'poker', and one per algorithm."""
        return [DOMAIN_BEHAVIOR, DOMAIN_POKER] + [
            f"{ALGORITHM_DOMAIN_PREFIX}{algo_id}" for algo_id in sorted(ALGORITHM_PARAMETER_BOUNDS)
        ]

    @staticmethod
    def _domain_table(domain: str) -> Mapping[str, tuple[float, float]] | None:
        """Return the live source table backing a domain (None if unknown)."""
        if domain == DOMAIN_BEHAVIOR:
            return SUB_BEHAVIOR_PARAMS
        if domain == DOMAIN_POKER:
            return POKER_SUB_BEHAVIOR_PARAMS
        if domain.startswith(ALGORITHM_DOMAIN_PREFIX):
            return ALGORITHM_PARAMETER_BOUNDS.get(domain[len(ALGORITHM_DOMAIN_PREFIX) :])
        return None

    @classmethod
    def get_bounds(cls, domain: str, name: str) -> tuple[float, float] | None:
        """Return (low, high) design bounds, or None if domain/name is unknown."""
        table = cls._domain_table(domain)
        if table is None:
            return None
        bounds = table.get(name)
        if bounds is None:
            return None
        return (float(bounds[0]), float(bounds[1]))

    @classmethod
    def clamp(cls, domain: str, name: str, value: float) -> float:
        """Clamp a value into its design bounds.

        Unknown domains/names pass through unchanged, and in-range values are
        returned bit-identical. Never consumes RNG.
        """
        if domain == DOMAIN_POKER:
            # PokerStrategyValidator is the single owner of poker clamping.
            return PokerStrategyValidator.clamp_known(name, value)
        bounds = cls.get_bounds(domain, name)
        if bounds is None:
            return value
        low, high = bounds
        if value < low:
            return low
        if value > high:
            return high
        return value

    @classmethod
    def clamp_params(cls, domain: str, params: Mapping[str, Any]) -> dict[str, Any]:
        """Return a copy of ``params`` with every known numeric value clamped.

        Unknown keys and non-numeric values are copied through untouched.
        """
        table = cls._domain_table(domain)
        if not table:
            return dict(params)
        result: dict[str, Any] = {}
        for key, value in params.items():
            if key in table and isinstance(value, (int, float)) and not isinstance(value, bool):
                result[key] = cls.clamp(domain, key, value)
            else:
                result[key] = value
        return result

    @classmethod
    def iter_parameters(cls) -> Iterator[tuple[str, str, float, float]]:
        """Yield (domain, name, low, high) for every registered parameter.

        Intended for tooling (catalogs, audits, mutation engines).
        """
        for domain in cls.domains():
            table = cls._domain_table(domain)
            if table is None:  # pragma: no cover - domains() only yields known
                continue
            for name in sorted(table):
                low, high = table[name]
                yield domain, name, float(low), float(high)
