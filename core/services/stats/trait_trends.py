"""Shared definition of the heritable traits we track to measure Layer 0 evolution.

A population can churn through many generations while its mean traits stay flat
(pure genetic drift, no selection). To tell *directional selection* from noise we
track the population mean of the heritable traits that most directly drive
survival and foraging, plus the expressed speed and size modifiers.

This module is the single source of truth for that trait set, so the live
metrics-history buffer (``backend/metrics_history.py``), the offline diagnostics
(``scripts/diagnose_evolution.py``), and the evolution report tool
(``tools/evolution_report.py``) all agree on what "trait drift" means and report
the same numbers.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.genetics.trait_utils import get_trait_value

# Heritable behavioral traits that most directly affect survival/foraging.
# Order is significant: it is the series order used by reports and charts.
BEHAVIORAL_TRAIT_KEYS: tuple[str, ...] = (
    "pursuit_aggression",
    "prediction_skill",
    "hunting_stamina",
    "aggression",
)

# Expressed (derived) trait keys, appended after the behavioral ones.
DERIVED_TRAIT_KEYS: tuple[str, ...] = ("speed", "size")

# Full ordered set of trait-mean keys exposed in samples/reports.
EVOLUTION_TRAIT_KEYS: tuple[str, ...] = BEHAVIORAL_TRAIT_KEYS + DERIVED_TRAIT_KEYS


def _mean(total: float, count: int) -> float | None:
    return round(total / count, 5) if count else None


def compute_trait_means(fish_list: Iterable[Any]) -> dict[str, float]:
    """Return the population mean of each tracked trait across the given fish.

    The caller is expected to pass the *living* fish. This function is read-only:
    it only reads genome attributes and never mutates simulation state or touches
    the RNG, so it is safe to call inside the deterministic step loop.

    Traits are averaged independently with per-trait counts, so a partially
    initialised population (a fish missing a trait) still yields sane means for
    the traits it does have. Returns an empty dict when there are no fish with a
    genome, so callers can treat "no data" uniformly.

    Args:
        fish_list: Iterable of fish-like objects exposing ``.genome``.

    Returns:
        Mapping of trait key -> mean value, restricted to keys that had data.
    """
    fish = [f for f in fish_list if getattr(f, "genome", None) is not None]
    if not fish:
        return {}

    means: dict[str, float] = {}

    for key in BEHAVIORAL_TRAIT_KEYS:
        total = 0.0
        count = 0
        for f in fish:
            behavioral = getattr(f.genome, "behavioral", None)
            value = get_trait_value(getattr(behavioral, key, None), default=None)
            if value is not None:
                total += float(value)
                count += 1
        mean = _mean(total, count)
        if mean is not None:
            means[key] = mean

    speed_total = 0.0
    speed_count = 0
    size_total = 0.0
    size_count = 0
    for f in fish:
        speed = getattr(f.genome, "speed_modifier", None)
        if speed is not None:
            speed_total += float(speed)
            speed_count += 1
        physical = getattr(f.genome, "physical", None)
        size_val = get_trait_value(getattr(physical, "size_modifier", None), default=None)
        if size_val is not None:
            size_total += float(size_val)
            size_count += 1

    speed_mean = _mean(speed_total, speed_count)
    if speed_mean is not None:
        means["speed"] = speed_mean
    size_mean = _mean(size_total, size_count)
    if size_mean is not None:
        means["size"] = size_mean

    return means
