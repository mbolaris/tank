"""Color conversion utilities.

This module provides color space conversions and manipulation functions
used throughout the simulation. Separating these from domain-specific
code enables reuse and clearer testing.

Design Note:
    These are pure functions with no simulation dependencies.
    They can be tested in isolation and used by any module.
"""


def hue_to_rgb(hue: float, saturation: float = 0.3) -> tuple[int, int, int]:
    """Convert a hue value (0.0-1.0) to an RGB color tuple.

    Uses a simplified HSL-to-RGB conversion with configurable saturation.
    The lightness is fixed at 0.5 (pastel colors) for aesthetic consistency.

    Args:
        hue: Hue value from 0.0 to 1.0 (wraps around like a color wheel)
        saturation: Color saturation from 0.0 (gray) to 1.0 (vivid)

    Returns:
        Tuple of (R, G, B) values, each 0-255

    Example:
        >>> hue_to_rgb(0.0)   # Red-ish
        (255, 178, 178)
        >>> hue_to_rgb(0.33)  # Green-ish
        (178, 255, 178)
        >>> hue_to_rgb(0.66)  # Blue-ish
        (178, 178, 255)
    """
    # Convert normalized hue to degrees
    hue_degrees = hue * 360

    # Calculate base RGB from hue (6-sector color wheel)
    if hue_degrees < 60:
        r, g, b = 255, int(hue_degrees / 60 * 255), 0
    elif hue_degrees < 120:
        r, g, b = int((120 - hue_degrees) / 60 * 255), 255, 0
    elif hue_degrees < 180:
        r, g, b = 0, 255, int((hue_degrees - 120) / 60 * 255)
    elif hue_degrees < 240:
        r, g, b = 0, int((240 - hue_degrees) / 60 * 255), 255
    elif hue_degrees < 300:
        r, g, b = int((hue_degrees - 240) / 60 * 255), 0, 255
    else:
        r, g, b = 255, 0, int((360 - hue_degrees) / 60 * 255)

    # Apply saturation (blend toward white for pastel effect)
    r = int(r * saturation + 255 * (1 - saturation))
    g = int(g * saturation + 255 * (1 - saturation))
    b = int(b * saturation + 255 * (1 - saturation))

    return (r, g, b)


# Default saturation used for fish coloring
FISH_COLOR_SATURATION = 0.3
