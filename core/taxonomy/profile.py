from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Protocol

from core.algorithms.composable.definitions import FoodApproach, SocialMode, ThreatResponse
from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
from core.genetics.physical import PHYSICAL_TRAIT_SPECS
from core.genetics.trait_utils import get_trait_value


class TaxonomyProfile:
    """A normalized, immutable profile representing taxonomic traits of an organism."""

    def __init__(self, traits: Mapping[str, float], is_microbe: bool):
        """Initialize the taxonomy profile.

        Args:
            traits: Dictionary of trait names to normalized values in [0.0, 1.0].
            is_microbe: True if this profile belongs to a microbe, False for a fish.
        """
        # A type profile is historical evidence.  Copy and freeze it so a
        # caller cannot silently redefine an existing species after creation.
        self.traits: Mapping[str, float] = MappingProxyType(
            {name: max(0.0, min(1.0, float(value))) for name, value in traits.items()}
        )
        self.is_microbe = is_microbe

    def to_dict(self) -> dict[str, Any]:
        """Serialize the profile to a dictionary."""
        return {
            "traits": dict(self.traits),
            "is_microbe": self.is_microbe,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaxonomyProfile:
        """Load a profile from a dictionary."""
        return cls(traits=data["traits"], is_microbe=data["is_microbe"])

    def distance(self, other: TaxonomyProfile) -> float:
        """Calculate the weighted taxonomic distance to another profile.

        Returns 1.0 (maximum distance) if profiles belong to different domains.
        """
        if self.is_microbe != other.is_microbe:
            return 1.0

        if self.is_microbe:
            trait_weights = _MICROBE_TRAIT_WEIGHTS
            total_weight = _MICROBE_TOTAL_WEIGHT
        else:
            trait_weights = _FISH_TRAIT_WEIGHTS
            total_weight = _FISH_TOTAL_WEIGHT

        # `trait_weights` is a precomputed flat table in the same iteration
        # order the grouped definition below would produce, so the accumulation
        # here is bit-for-bit identical to the original grouped loop.
        st = self.traits
        ot = other.traits
        distance_sq = 0.0
        for trait, trait_weight, is_circular in trait_weights:
            v1 = st.get(trait, 0.5)
            v2 = ot.get(trait, 0.5)
            if is_circular:
                d = _circular_distance(v1, v2)
            else:
                d = v1 - v2
            distance_sq += trait_weight * (d * d)

        if total_weight <= 0.0:
            return 0.0
        return math.sqrt(distance_sq / total_weight)


# Group definitions and weights. These are constant for the lifetime of the
# process, so they are flattened once (below) into per-trait weight tables that
# `TaxonomyProfile.distance` iterates directly, instead of rebuilding the dicts,
# lists, and sets on every one of the hundreds of thousands of calls per sim.

# Microbe groups & weights (Core: 60%, Ecology: 25%, Accessory/HGT: 15%)
_MICROBE_GROUPS = {
    "core_structure_metabolism": [
        "cell_size",
        "shape_aspect",
        "elongation_fins",
        "metabolism_lifespan",
    ],
    "ecology_behavior": ["motility_aggression", "social_swarming", "food_approach"],
    "accessory_hgt": ["pigment_hue", "texture_pattern", "template_capsule"],
}
_MICROBE_GROUP_WEIGHTS = {
    "core_structure_metabolism": 0.60,
    "ecology_behavior": 0.25,
    "accessory_hgt": 0.15,
}
_MICROBE_CIRCULAR_TRAITS = {"pigment_hue"}

# Fish groups & weights (Body: 35%, Appearance: 15%, Temperament: 15%, Foraging: 20%, Behavior: 15%)
_FISH_GROUPS = {
    "body_structure": [
        "size_modifier",
        "body_aspect",
        "fin_size",
        "tail_size",
        "eye_size",
        "lifespan_modifier",
    ],
    "appearance": ["color_hue", "pattern_type", "pattern_intensity", "template_id"],
    "temperament": ["aggression", "social_tendency"],
    "foraging": [
        "pursuit_aggression",
        "prediction_skill",
        "hunting_stamina",
        "food_approach",
    ],
    "behavioral_architecture": [
        "threat_response",
        "social_mode",
        "movement_policy_family",
    ],
}
_FISH_GROUP_WEIGHTS = {
    "body_structure": 0.35,
    "appearance": 0.15,
    "temperament": 0.15,
    "foraging": 0.20,
    "behavioral_architecture": 0.15,
}
_FISH_CIRCULAR_TRAITS = {"color_hue"}


def _flatten_trait_weights(
    groups: Mapping[str, list[str]],
    group_weights: Mapping[str, float],
    circular_traits: set[str],
) -> tuple[tuple[tuple[str, float, bool], ...], float]:
    """Flatten grouped trait weights into a per-trait table plus total weight.

    The table preserves the exact (group, trait) iteration order and repeated
    ``gweight / len(traits)`` values of the original grouped loop, so summing it
    reproduces the same floating-point accumulation bit-for-bit.
    """
    table: list[tuple[str, float, bool]] = []
    total_weight = 0.0
    for group_name, traits in groups.items():
        if not traits:
            continue
        trait_weight = group_weights[group_name] / len(traits)
        for trait in traits:
            table.append((trait, trait_weight, trait in circular_traits))
            total_weight += trait_weight
    return tuple(table), total_weight


_MICROBE_TRAIT_WEIGHTS, _MICROBE_TOTAL_WEIGHT = _flatten_trait_weights(
    _MICROBE_GROUPS, _MICROBE_GROUP_WEIGHTS, _MICROBE_CIRCULAR_TRAITS
)
_FISH_TRAIT_WEIGHTS, _FISH_TOTAL_WEIGHT = _flatten_trait_weights(
    _FISH_GROUPS, _FISH_GROUP_WEIGHTS, _FISH_CIRCULAR_TRAITS
)


def _circular_distance(a: float, b: float) -> float:
    """Distance on a circular [0, 1] scale."""
    diff = abs(a - b) % 1.0
    return min(diff, 1.0 - diff)


def _normalize_trait(value: float, min_val: float, max_val: float) -> float:
    """Normalize a trait value to [0, 1] range."""
    span = max_val - min_val
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / span))


def _hash_to_float(s: str | None) -> float:
    """Deterministically hash a string to a float in [0.0, 1.0]."""
    if not s:
        return 0.0
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return int(h[:6], 16) / 16777215.0


class TaxonomyProfileBuilder(Protocol):
    """Protocol for taxonomy profile builders."""

    def build_profile(self, entity: Any) -> TaxonomyProfile:
        """Build a TaxonomyProfile from an entity."""
        ...


class FishTaxonomyProfileBuilder:
    """Taxonomy profile builder for Fish."""

    def build_profile(self, entity: Any) -> TaxonomyProfile:
        genome = entity.genome
        ptraits = genome.physical
        btraits = genome.behavioral

        traits: dict[str, float] = {}

        # 1. Physical traits normalization
        for spec in PHYSICAL_TRAIT_SPECS:
            val = get_trait_value(getattr(ptraits, spec.name), default=0.0)
            traits[spec.name] = _normalize_trait(val, spec.min_val, spec.max_val)

        # 2. Behavioral traits normalization
        for spec in BEHAVIORAL_TRAIT_SPECS:
            val = get_trait_value(getattr(btraits, spec.name), default=0.0)
            traits[spec.name] = _normalize_trait(val, spec.min_val, spec.max_val)

        # 3. Composable sub-behaviors
        cb = btraits.behavior.value

        if cb is not None:
            # ThreatResponse: 4 options, normalized to [0, 1]
            threat_val = cb.threat_response.value / max(1, len(ThreatResponse) - 1)
            traits["threat_response"] = threat_val

            # FoodApproach: 6 options
            food_val = cb.food_approach.value / max(1, len(FoodApproach) - 1)
            traits["food_approach"] = food_val

            # SocialMode: 4 options
            social_val = cb.social_mode.value / max(1, len(SocialMode) - 1)
            traits["social_mode"] = social_val
        else:
            traits["threat_response"] = 0.0
            traits["food_approach"] = 0.0
            traits["social_mode"] = 0.0

        # 4. Movement policy family
        movement_policy_id = get_trait_value(btraits.movement_policy_id, default=None)
        traits["movement_policy_family"] = _hash_to_float(movement_policy_id)

        return TaxonomyProfile(traits, is_microbe=False)


class MicrobeTaxonomyProfileBuilder:
    """Taxonomy profile builder for Microbes (adapting Fish Genome)."""

    def build_profile(self, entity: Any) -> TaxonomyProfile:
        genome = entity.genome
        ptraits = genome.physical
        btraits = genome.behavioral

        # Extract underlying values
        size_val = get_trait_value(ptraits.size_modifier, default=1.0)
        aspect_val = get_trait_value(ptraits.body_aspect, default=1.0)
        fin_val = get_trait_value(ptraits.fin_size, default=1.0)
        lifespan_val = get_trait_value(ptraits.lifespan_modifier, default=1.0)

        aggression_val = get_trait_value(btraits.aggression, default=0.5)
        social_val = get_trait_value(btraits.social_tendency, default=0.5)

        hue_val = get_trait_value(ptraits.color_hue, default=0.0)
        intensity_val = get_trait_value(ptraits.pattern_intensity, default=0.0)
        template_val = get_trait_value(ptraits.template_id, default=0)

        # Get discrete behavior for food approach
        cb = btraits.behavior.value
        food_approach_val = 0.0
        if cb is not None:
            food_approach_val = cb.food_approach.value / max(1, len(FoodApproach) - 1)

        # Fetch specifications for physical/behavioral traits
        p_specs = {spec.name: spec for spec in PHYSICAL_TRAIT_SPECS}
        b_specs = {spec.name: spec for spec in BEHAVIORAL_TRAIT_SPECS}

        traits: dict[str, float] = {}

        # Group 1: Core structure and metabolism (60%)
        # cell_size (size_modifier)
        spec = p_specs["size_modifier"]
        traits["cell_size"] = _normalize_trait(size_val, spec.min_val, spec.max_val)
        # shape_aspect (body_aspect)
        spec = p_specs["body_aspect"]
        traits["shape_aspect"] = _normalize_trait(aspect_val, spec.min_val, spec.max_val)
        # elongation_fins (fin_size)
        spec = p_specs["fin_size"]
        traits["elongation_fins"] = _normalize_trait(fin_val, spec.min_val, spec.max_val)
        # metabolism_lifespan (lifespan_modifier)
        spec = p_specs["lifespan_modifier"]
        traits["metabolism_lifespan"] = _normalize_trait(lifespan_val, spec.min_val, spec.max_val)

        # Group 2: Ecology and stable behavior (25%)
        # motility_aggression (aggression)
        spec = b_specs["aggression"]
        traits["motility_aggression"] = _normalize_trait(aggression_val, spec.min_val, spec.max_val)
        # social_swarming (social_tendency)
        spec = b_specs["social_tendency"]
        traits["social_swarming"] = _normalize_trait(social_val, spec.min_val, spec.max_val)
        # food_approach
        traits["food_approach"] = food_approach_val

        # Group 3: Accessory/HGT modules (15%)
        # pigment_hue (color_hue) - circular
        traits["pigment_hue"] = hue_val
        # texture_pattern (pattern_intensity)
        spec = p_specs["pattern_intensity"]
        traits["texture_pattern"] = _normalize_trait(intensity_val, spec.min_val, spec.max_val)
        # template_capsule (template_id)
        spec = p_specs["template_id"]
        traits["template_capsule"] = _normalize_trait(
            float(template_val), spec.min_val, spec.max_val
        )

        return TaxonomyProfile(traits, is_microbe=True)
