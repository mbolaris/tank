"""Coordinate-only canonical/legacy conversion.

Legacy soccer render coordinates use +y down and clockwise angles. Canonical
domain coordinates use +y north and counter-clockwise angles. This module has
no knowledge of pixels, canvas dimensions, DPR, or layout.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalPoint:
    x: float
    y: float


@dataclass(frozen=True)
class LegacyPoint:
    x: float
    y: float


CanonicalCoordinate = CanonicalPoint
LegacyCoordinate = LegacyPoint


def legacy_to_canonical(point: LegacyPoint | tuple[float, float]) -> CanonicalPoint:
    x, y = (point.x, point.y) if isinstance(point, LegacyPoint) else point
    return CanonicalPoint(float(x), -float(y))


def canonical_to_legacy(point: CanonicalPoint | tuple[float, float]) -> LegacyPoint:
    x, y = (point.x, point.y) if isinstance(point, CanonicalPoint) else point
    return LegacyPoint(float(x), -float(y))


def _normalize(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def legacy_angle_to_canonical(angle: float) -> float:
    return _normalize(-float(angle))


def canonical_angle_to_legacy(angle: float) -> float:
    return _normalize(-float(angle))
