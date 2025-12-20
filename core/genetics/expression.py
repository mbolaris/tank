"""Gene expression logic for translating genotype to phenotype.

This module contains the functional logic to calculate physical and behavioral
characteristics from genetic traits. Separating this logic from the data storage
(Genome) allows for easier testing, tuning, and clearer separation of concerns.
"""

from typing import Dict, Tuple

from core.genetics.behavioral import MATE_PREFERENCE_SPECS, BehavioralTraits, normalize_mate_preferences
from core.genetics.physical import PhysicalTraits

# =============================================================================
# Tuning Constants
# =============================================================================

# Speed modifiers for different body templates
_TEMPLATE_SPEED_BONUS = {0: 1.0, 1: 1.2, 2: 0.8, 3: 1.0, 4: 0.9, 5: 1.1}

_SPEED_MODIFIER_MIN = 0.5
_SPEED_MODIFIER_MAX = 1.5

_METABOLISM_RATE_MIN = 0.5
_PATTERN_INTENSITY_BASELINE = 0.5
_PATTERN_INTENSITY_COST_WEIGHT = 0.3


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _normalized_similarity(
    value: float,
    target: float,
    min_value: float,
    max_value: float,
    *,
    circular: bool = False,
) -> float:
    span = max_value - min_value
    if span <= 0:
        return 1.0
    diff = abs(value - target)
    if circular:
        diff = diff % span
        diff = min(diff, span - diff)
    return 1.0 - min(diff / span, 1.0)


def calculate_speed_modifier(physical: PhysicalTraits) -> float:
    """Calculate speed modifier based on physical traits.
    
    Combines template bonuses, propulsion from fins/tail, and hydrodynamic efficiency.
    """
    # Defensive checks handled by type system mostly, but we ensure values exist
    if physical.template_id is None or getattr(physical.template_id, "value", None) is None:
        return 1.0
        
    template_id = physical.template_id.value
    template_speed_bonus = _TEMPLATE_SPEED_BONUS.get(template_id, 1.0)
    
    fin_val = physical.fin_size.value if physical.fin_size else 1.0
    tail_val = physical.tail_size.value if physical.tail_size else 1.0
    aspect_val = physical.body_aspect.value if physical.body_aspect else 1.0
    
    propulsion = fin_val * 0.4 + tail_val * 0.6
    hydrodynamics = 1.0 - abs(aspect_val - 0.8) * 0.5
    
    result = template_speed_bonus * propulsion * hydrodynamics
    return _clamp(result, _SPEED_MODIFIER_MIN, _SPEED_MODIFIER_MAX)


def calculate_metabolism_rate(physical: PhysicalTraits, speed_modifier: float) -> float:
    """Calculate metabolism rate based on physical traits and capabilities.
    
    Larger, faster, or more decorative fish have higher metabolic costs.
    """
    cost = 1.0
    
    size_val = physical.size_modifier.value if physical.size_modifier else 1.0
    eye_val = physical.eye_size.value if physical.eye_size else 1.0
    pattern_val = physical.pattern_intensity.value if physical.pattern_intensity else 0.0
    
    cost += (size_val - 1.0) * 0.5
    cost += (speed_modifier - 1.0) * 0.8
    cost += (eye_val - 1.0) * 0.3
    cost += (pattern_val - _PATTERN_INTENSITY_BASELINE) * _PATTERN_INTENSITY_COST_WEIGHT
    
    return max(_METABOLISM_RATE_MIN, cost)


def calculate_vision_range(physical: PhysicalTraits) -> float:
    """Calculate vision range based on eye size."""
    if physical.eye_size is None or getattr(physical.eye_size, "value", None) is None:
        return 1.0
        
    # Clamp to allowed physical bounds to avoid out-of-range visual traits
    from core.constants import EYE_SIZE_MAX, EYE_SIZE_MIN
    val = float(physical.eye_size.value)
    return max(EYE_SIZE_MIN, min(EYE_SIZE_MAX, val))


def calculate_color_tint(physical: PhysicalTraits) -> Tuple[int, int, int]:
    """Get RGB color tint based on genome."""
    if physical.color_hue is None or getattr(physical.color_hue, "value", None) is None:
        return (255, 255, 255)

    hue = physical.color_hue.value * 360
    if hue < 60:
        r, g, b = 255, int(hue / 60 * 255), 0
    elif hue < 120:
        r, g, b = int((120 - hue) / 60 * 255), 255, 0
    elif hue < 180:
        r, g, b = 0, 255, int((hue - 120) / 60 * 255)
    elif hue < 240:
        r, g, b = 0, int((240 - hue) / 60 * 255), 255
    elif hue < 300:
        r, g, b = int((hue - 240) / 60 * 255), 0, 255
    else:
        r, g, b = 255, 0, int((360 - hue) / 60 * 255)

    saturation = 0.3
    r = int(r * saturation + 255 * (1 - saturation))
    g = int(g * saturation + 255 * (1 - saturation))
    b = int(b * saturation + 255 * (1 - saturation))
    return (r, g, b)


def calculate_mate_compatibility(
    self_physical: PhysicalTraits,
    self_behavioral: BehavioralTraits,
    other_physical: PhysicalTraits
) -> float:
    """Calculate compatibility score with potential mate (0.0-1.0).

    Compatibility is based on how closely the mate matches this fish's
    preferred physical trait values, plus a bonus for higher pattern intensity.
    """
    raw_prefs = self_behavioral.mate_preferences.value if self_behavioral.mate_preferences else {}
    preferences = raw_prefs if isinstance(raw_prefs, dict) else {}
    
    # We need to normalize preferences based on self_physical to fill in defaults
    # correctly (often defaulting to own traits).
    normalized_prefs = normalize_mate_preferences(
        preferences,
        physical=self_physical,
    )

    scores = []
    weights = []
    
    for trait_name, spec in MATE_PREFERENCE_SPECS.items():
        desired = normalized_prefs[trait_name]
        other_trait = getattr(other_physical, trait_name, None)
        
        if other_trait is None or getattr(other_trait, "value", None) is None:
            # Skip missing traits or default to low score
            continue
            
        mate_value = other_trait.value
        score = _normalized_similarity(
            mate_value,
            desired,
            spec.min_val,
            spec.max_val,
            circular=(trait_name == "color_hue"),
        )
        scores.append(score)
        weights.append(1.0)

    pattern_weight = normalized_prefs.get("prefer_high_pattern_intensity", 0.5)
    if pattern_weight > 0.0 and other_physical.pattern_intensity is not None:
        scores.append(_clamp(other_physical.pattern_intensity.value, 0.0, 1.0))
        weights.append(pattern_weight)

    total_weight = sum(weights)
    if total_weight <= 0.0:
        return 0.0
        
    compatibility = sum(score * weight for score, weight in zip(scores, weights)) / total_weight
    return min(max(compatibility, 0.0), 1.0)
