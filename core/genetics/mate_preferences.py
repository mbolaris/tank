"""Mate preference system for fish genomes.

This module owns the mate-preference trait dictionary: its defaults, the
specs that bound each preferred-trait value, normalization of stored
preference dicts, and inheritance of preferences from two parents.

Extracted verbatim from core/genetics/behavioral.py (behavior-preserving
split). The behavioral module re-exports these names for backwards
compatibility.
"""

import random as pyrandom
from typing import TYPE_CHECKING, Any, Optional

from core.evolution.inheritance import inherit_discrete_trait as _inherit_discrete_trait
from core.evolution.inheritance import inherit_trait as _inherit_trait
from core.genetics.physical import PHYSICAL_TRAIT_SPECS
from core.genetics.trait import TraitSpec

if TYPE_CHECKING:
    from core.genetics.physical import PhysicalTraits

# Default mate preferences keep keys stable across versions and inheritance.
DEFAULT_MATE_PREFERENCES: dict[str, float] = {
    "prefer_similar_size": 0.5,
    "prefer_different_color": 0.5,
    "prefer_high_energy": 0.5,
    "prefer_high_pattern_intensity": 0.5,
    # Behavioral preference weights: how much to prefer mates with matching behavioral traits.
    # These enable sexual selection to act on behavioral characteristics, creating
    # evolutionary pressure for behavioral compatibility and specialization.
    "prefer_high_aggression": 0.5,
    "prefer_high_social_tendency": 0.5,
    # Assortative-mating weight on composable behavior profile similarity
    # (threat_response/food_approach/social_mode/poker_engagement match).
    # 0.5 = neutral (no effect), >0.5 = prefer similar (assortative,
    # protects niches -> sympatric speciation), <0.5 = prefer different
    # (disassortative). Heritable and mutable like every other preference.
    "prefer_similar_behavior": 0.5,
}

MATE_PREFERENCE_TRAIT_NAMES = (
    "size_modifier",
    "color_hue",
    "template_id",
    "fin_size",
    "tail_size",
    "body_aspect",
    "eye_size",
    "pattern_type",
)

MATE_PREFERENCE_SPECS: dict[str, TraitSpec] = {
    spec.name: spec for spec in PHYSICAL_TRAIT_SPECS if spec.name in MATE_PREFERENCE_TRAIT_NAMES
}


def default_preference_value(spec: TraitSpec) -> float:
    midpoint = (spec.min_val + spec.max_val) / 2.0
    if spec.discrete:
        return float(int(round(midpoint)))
    return float(midpoint)


def coerce_preference_value(value: Any, spec: TraitSpec) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default_preference_value(spec)
    if spec.discrete:
        numeric = int(round(numeric))
        numeric = max(int(spec.min_val), min(int(spec.max_val), numeric))
        return float(numeric)
    numeric = max(spec.min_val, min(spec.max_val, numeric))
    return float(numeric)


def default_preference_for_key(pref_key: str) -> float:
    spec = MATE_PREFERENCE_SPECS.get(pref_key)
    if spec is not None:
        return default_preference_value(spec)
    return DEFAULT_MATE_PREFERENCES.get(pref_key, 0.5)


def normalize_mate_preferences(
    prefs: dict[str, float],
    *,
    physical: Optional["PhysicalTraits"] = None,
    rng: pyrandom.Random | None = None,
) -> dict[str, float]:
    """Normalize mate preferences by filling defaults and clamping to valid ranges."""
    normalized: dict[str, float] = {str(k): v for k, v in (prefs or {}).items()}

    for pref_key, default_val in DEFAULT_MATE_PREFERENCES.items():
        normalized.setdefault(pref_key, default_val)
        if pref_key not in MATE_PREFERENCE_SPECS:
            try:
                numeric = float(normalized[pref_key])
            except (TypeError, ValueError):
                numeric = default_val
            normalized[pref_key] = max(0.0, min(1.0, numeric))

    for name, spec in MATE_PREFERENCE_SPECS.items():
        if name not in normalized:
            if physical is not None:
                normalized[name] = getattr(physical, name).value
            elif rng is not None:
                normalized[name] = spec.random_value(rng).value
            else:
                normalized[name] = default_preference_value(spec)
        normalized[name] = coerce_preference_value(normalized[name], spec)

    return normalized


def inherit_mate_preference_value(
    pref_key: str,
    p1_val: float,
    p2_val: float,
    *,
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> float:
    spec = MATE_PREFERENCE_SPECS.get(pref_key)
    if spec is None:
        legacy_spec = TraitSpec(pref_key, 0.0, 1.0)
        p1_val = coerce_preference_value(p1_val, legacy_spec)
        p2_val = coerce_preference_value(p2_val, legacy_spec)
        return _inherit_trait(
            float(p1_val),
            float(p2_val),
            0.0,
            1.0,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )

    p1_val = coerce_preference_value(p1_val, spec)
    p2_val = coerce_preference_value(p2_val, spec)
    if spec.discrete:
        return float(
            _inherit_discrete_trait(
                int(round(p1_val)),
                int(round(p2_val)),
                int(spec.min_val),
                int(spec.max_val),
                weight1=weight1,
                mutation_rate=mutation_rate,
                rng=rng,
            )
        )
    return _inherit_trait(
        float(p1_val),
        float(p2_val),
        spec.min_val,
        spec.max_val,
        weight1=weight1,
        mutation_rate=mutation_rate,
        mutation_strength=mutation_strength,
        rng=rng,
    )


def inherit_mate_preferences(
    prefs1: dict[str, float],
    prefs2: dict[str, float],
    weight1: float,
    mutation_rate: float,
    mutation_strength: float,
    rng: pyrandom.Random,
) -> dict[str, float]:
    """Inherit mate preferences from parents."""
    result = {}
    keys = sorted(
        set(DEFAULT_MATE_PREFERENCES) | set(MATE_PREFERENCE_SPECS) | set(prefs1) | set(prefs2)
    )
    for pref_key in keys:
        default_val = default_preference_for_key(pref_key)
        p1_val = prefs1.get(pref_key, default_val)
        p2_val = prefs2.get(pref_key, default_val)
        result[pref_key] = inherit_mate_preference_value(
            pref_key,
            p1_val,
            p2_val,
            weight1=weight1,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            rng=rng,
        )
    return result
