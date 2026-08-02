"""Pure soccer coordinate conversion utilities."""

from core.minigames.soccer.coords.canonical import (
    CanonicalPoint,
    CanonicalCoordinate,
    LegacyPoint,
    LegacyCoordinate,
    canonical_angle_to_legacy,
    canonical_to_legacy,
    legacy_angle_to_canonical,
    legacy_to_canonical,
)

__all__ = [
    "CanonicalPoint",
    "CanonicalCoordinate",
    "LegacyPoint",
    "LegacyCoordinate",
    "canonical_to_legacy",
    "legacy_to_canonical",
    "canonical_angle_to_legacy",
    "legacy_angle_to_canonical",
]
