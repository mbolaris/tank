"""Focused behavioral-equivalence tests for shared steering primitives."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from core.behavior.primitives.steering import (
    boids_steering,
    flee_components,
    flee_direction,
    lead_target,
    normalize_angle,
    normalized_components,
    safe_normalize,
    seek_direction,
    turn_then_dash,
)
from core.math_utils import Vector2


@dataclass
class _Boid:
    pos: Vector2
    vel: Vector2


def test_safe_normalization_and_directions_handle_zero_and_exact_target() -> None:
    origin = Vector2(3, -2)

    assert safe_normalize(Vector2(0, 0)) == Vector2(0, 0)
    assert safe_normalize(Vector2(1e-7, 0)) == Vector2(0, 0)
    assert seek_direction(origin, origin) == Vector2(0, 0)
    assert flee_direction(origin, origin) == Vector2(0, 0)
    assert seek_direction(origin, Vector2(6, 2)) == Vector2(0.6, 0.8)
    assert flee_direction(origin, Vector2(6, 2)) == Vector2(-0.6, -0.8)


def test_scalar_directions_preserve_zero_and_opposite_heading() -> None:
    assert normalized_components(0.0, 0.0) == (0.0, 0.0)
    assert flee_components(0.0, 0.0) == (0.0, 0.0)
    assert math.copysign(1.0, flee_components(0.0, 0.0)[0]) == 1.0
    assert normalized_components(3.0, 4.0) == (0.6, 0.8)
    assert flee_components(3.0, 4.0) == (-0.6, -0.8)


def test_turn_then_dash_honors_turn_limit_commit_distance_and_stamina_floor() -> None:
    # An external target requires a bounded turn before any dash.
    turn, dash = turn_then_dash(-100.0, 0.0, 0.0, 1.0, 0.35)
    assert turn == pytest.approx(1.0)
    assert dash == 0.0

    # An aligned target inside the commit radius is intentionally not chased.
    assert turn_then_dash(0.4, 0.0, 0.0, 1.0, 0.35) == (0.0, 0.0)

    # Low stamina preserves the legacy taper while an aligned target is distant.
    assert turn_then_dash(2.0, 0.0, 0.0, 0.1, 0.35) == pytest.approx((0.0, 0.3))


def test_lead_angle_and_boids_primitives_are_deterministic() -> None:
    assert lead_target(4.0, -2.0, 0.5, -1.5, 6.0) == (7.0, -11.0)
    assert normalize_angle(3 * math.pi) == pytest.approx(math.pi)
    assert normalize_angle(-3 * math.pi) == pytest.approx(-math.pi)

    neighbors = [_Boid(Vector2(2, 0), Vector2(1, 0)), _Boid(Vector2(0, 2), Vector2(0, 1))]
    first = boids_steering(Vector2(0, 0), neighbors, cohesion=0.4, alignment=0.2, separation=3.0)
    second = boids_steering(Vector2(0, 0), neighbors, cohesion=0.4, alignment=0.2, separation=3.0)

    assert first == second
    assert boids_steering(Vector2(0, 0), [], cohesion=0.4, alignment=0.2, separation=3.0) == (
        0.0,
        0.0,
    )
