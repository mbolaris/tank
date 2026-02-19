"""Visual geometry calculations for fish entities.

This module provides utilities for calculating visual bounds and offsets
for fish rendering. These calculations account for:
- Fish size (lifecycle scaling)
- Genetic traits (fin size, tail size, body aspect)
- Template variations (6 different fish templates)

Extracting this logic from Fish entity improves:
- Testability: geometry calculations can be unit tested in isolation
- Clarity: visual concerns separated from domain logic
- Reusability: could be used by other rendering systems

Design Note:
-----------
This module uses dataclasses to represent trait values, making the
geometry calculations pure functions that don't depend on entity state.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FishTraits:
    """Immutable snapshot of fish physical traits for geometry calculation.

    Attributes:
        fin_size: Fin size modifier (default 1.0)
        tail_size: Tail size modifier (default 1.0)
        body_aspect: Body aspect ratio modifier (default 1.0)
        template_id: Fish template ID (0-5)
    """

    fin_size: float = 1.0
    tail_size: float = 1.0
    body_aspect: float = 1.0
    template_id: int = 0


def extract_traits_from_genome(genome) -> FishTraits:
    """Extract visual traits from a fish genome.

    Args:
        genome: Fish genome object with physical traits

    Returns:
        FishTraits containing extracted trait values
    """
    physical = getattr(genome, "physical", None) if genome is not None else None
    if physical is None:
        return FishTraits()

    fin_trait = getattr(physical, "fin_size", None)
    tail_trait = getattr(physical, "tail_size", None)
    body_trait = getattr(physical, "body_aspect", None)
    template_trait = getattr(physical, "template_id", None)

    fin_size = fin_trait.value if fin_trait is not None and fin_trait.value is not None else 1.0
    tail_size = tail_trait.value if tail_trait is not None and tail_trait.value is not None else 1.0
    body_aspect = (
        body_trait.value if body_trait is not None and body_trait.value is not None else 1.0
    )
    template_id = (
        int(template_trait.value)
        if template_trait is not None and template_trait.value is not None
        else 0
    )
    template_id = max(0, min(5, template_id))

    return FishTraits(
        fin_size=fin_size,
        tail_size=tail_size,
        body_aspect=body_aspect,
        template_id=template_id,
    )


def calculate_visual_bounds(
    base_size: float,
    size_multiplier: float,
    traits: FishTraits | None = None,
) -> tuple[float, float, float, float]:
    """Calculate visual bounds offsets for a fish.

    Accounts for lifecycle scaling and parametric template geometry so the
    rendered fish stays inside the tank bounds.

    Args:
        base_size: Base size (max of width, height)
        size_multiplier: Size multiplier from lifecycle component
        traits: Fish physical traits (defaults if None)

    Returns:
        Tuple of (min_x, max_x, min_y, max_y) offsets from position
    """
    if traits is None:
        traits = FishTraits()

    scaled_base = base_size * size_multiplier

    # Get template-specific geometry ratios
    width_scale, height_scale, ratios = _get_template_geometry(traits)

    min_x_ratio, max_x_ratio, min_y_ratio, max_y_ratio = ratios

    # Calculate actual offsets
    width = scaled_base * width_scale
    height = scaled_base * height_scale
    min_x = min_x_ratio * width
    max_x = max_x_ratio * width
    min_y = min_y_ratio * height
    max_y = max_y_ratio * height

    # Account for fish flipping (facing left vs right)
    flipped_min_x = scaled_base - max_x
    flipped_max_x = scaled_base - min_x

    # Take the most conservative bounds
    effective_min_x = min(0.0, min_x, flipped_min_x)
    effective_max_x = max(scaled_base, max_x, flipped_max_x)
    effective_min_y = min(0.0, min_y)
    effective_max_y = max(scaled_base, max_y)

    return (effective_min_x, effective_max_x, effective_min_y, effective_max_y)


def _get_template_geometry(
    traits: FishTraits,
) -> tuple[float, float, tuple[float, float, float, float]]:
    """Get geometry parameters for a specific fish template.

    Args:
        traits: Fish physical traits

    Returns:
        Tuple of (width_scale, height_scale, (min_x_ratio, max_x_ratio, min_y_ratio, max_y_ratio))
    """
    fin_size = traits.fin_size
    tail_size = traits.tail_size
    body_aspect = traits.body_aspect
    template_id = traits.template_id

    width_scale = body_aspect
    height_scale = 1.0

    if template_id == 5:
        # Wide, flat fish template
        width_scale = body_aspect * 1.3
        height_scale = 0.7
        min_x_ratio = min(0.05, 0.3 - 0.08 * fin_size, 0.1 - 0.15 * tail_size)
        max_x_ratio = 0.98
        min_y_ratio = min(0.25, 0.35 - 0.12 * fin_size)
        max_y_ratio = 0.75
    elif template_id == 4:
        # Template 4 geometry
        min_x_ratio = min(0.2, 0.4 - 0.2 * fin_size, 0.25 - 0.18 * tail_size)
        max_x_ratio = 0.92
        min_y_ratio = 0.15 - 0.15 * fin_size
        max_y_ratio = 0.85
    elif template_id == 3:
        # Template 3 geometry
        min_x_ratio = 0.3 - 0.25 * tail_size
        max_x_ratio = 0.9
        min_y_ratio = min(0.2, 0.22 - 0.3 * fin_size)
        max_y_ratio = 0.78 + 0.3 * fin_size
    elif template_id == 2:
        # Template 2 geometry
        min_x_ratio = min(0.2, 0.25 - 0.3 * tail_size)
        max_x_ratio = 0.95
        min_y_ratio = 0.2 - 0.25 * fin_size
        max_y_ratio = 0.8 + 0.25 * fin_size
    elif template_id == 1:
        # Template 1 geometry
        min_x_ratio = min(0.1, 0.4 - 0.1 * fin_size, 0.15 - 0.2 * tail_size)
        max_x_ratio = 0.95
        min_y_ratio = min(0.2, 0.3 - 0.15 * fin_size)
        max_y_ratio = 0.8
    else:
        # Default template (0) geometry
        min_x_ratio = min(0.1, 0.35 - 0.15 * fin_size, 0.2 - 0.25 * tail_size)
        max_x_ratio = 0.95
        min_y_ratio = min(0.1, 0.15 - 0.2 * fin_size)
        max_y_ratio = 0.9

    return (width_scale, height_scale, (min_x_ratio, max_x_ratio, min_y_ratio, max_y_ratio))
