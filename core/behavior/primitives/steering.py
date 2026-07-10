"""Deterministic steering math shared across Tank World domains.

This module is intentionally a small collection of pure functions. It is the
first reusable-behavior step: existing fish and soccer call sites delegate here
without changing genomes, action selection, or RNG consumption.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol, cast

from core.math_utils import Vector2


class Positioned(Protocol):
    """Minimal position contract needed by :func:`boids_steering`."""

    pos: Vector2


class HasVelocity(Protocol):
    """Optional velocity contract used for boids alignment."""

    vel: Vector2


def safe_normalize(vector: Vector2) -> Vector2:
    """Normalize ``vector``, returning zero for zero or near-zero length."""
    length = vector.length()
    if length < 1e-6:
        return Vector2(0, 0)
    return vector.normalize()


def seek_direction(origin: Vector2, target: Vector2) -> Vector2:
    """Return the safe unit direction from ``origin`` toward ``target``."""
    return safe_normalize(target - origin)


def flee_direction(origin: Vector2, threat: Vector2) -> Vector2:
    """Return the safe unit direction from ``threat`` away from ``origin``."""
    return safe_normalize(origin - threat)


def normalized_components(x: float, y: float) -> tuple[float, float]:
    """Return normalized scalar components, preserving a zero vector exactly."""
    length_sq = x * x + y * y
    if length_sq > 0:
        length = math.sqrt(length_sq)
        return x / length, y / length
    return 0.0, 0.0


def flee_components(x: float, y: float) -> tuple[float, float]:
    """Return normalized scalar components pointing opposite ``(x, y)``."""
    normalized_x, normalized_y = normalized_components(x, y)
    if normalized_x == 0.0 and normalized_y == 0.0:
        return 0.0, 0.0
    return -normalized_x, -normalized_y


def normalize_angle(angle: float) -> float:
    """Normalize an angle to the inclusive range ``[-pi, pi]``."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def lead_target(
    target_x: float, target_y: float, velocity_x: float, velocity_y: float, lead: float
) -> tuple[float, float]:
    """Return a constant-velocity lead point for a moving target."""
    return target_x + velocity_x * lead, target_y + velocity_y * lead


def turn_then_dash(
    target_x: float,
    target_y: float,
    facing_angle: float,
    stamina_ratio: float,
    stamina_floor: float,
    align_threshold: float = 0.25,
    commit_dist: float = 0.4,
) -> tuple[float, float]:
    """Return turn and dash values for a target in the actor's relative frame."""
    distance = math.sqrt(target_x * target_x + target_y * target_y)
    angle_delta = normalize_angle(math.atan2(target_y, target_x) - facing_angle)

    if abs(angle_delta) >= align_threshold:
        return max(-1.0, min(1.0, (angle_delta * 1.5) / math.pi)), 0.0

    if distance > commit_dist:
        dash = (
            1.0
            if stamina_ratio > stamina_floor
            else max(0.3, stamina_ratio / max(stamina_floor, 1e-6))
        )
    else:
        dash = 0.0
    return 0.0, dash


def boids_steering(
    position: Vector2,
    neighbors: Sequence[Positioned],
    cohesion: float,
    alignment: float,
    separation: float,
) -> tuple[float, float]:
    """Return the existing cohesion, alignment, and separation steering vector."""
    if not neighbors:
        return 0.0, 0.0

    center_x = sum(neighbor.pos.x for neighbor in neighbors) / len(neighbors)
    center_y = sum(neighbor.pos.y for neighbor in neighbors) / len(neighbors)
    cohesion_direction = safe_normalize(Vector2(center_x - position.x, center_y - position.y))

    alignment_x, alignment_y = 0.0, 0.0
    for neighbor in neighbors:
        if hasattr(neighbor, "vel"):
            velocity = cast(HasVelocity, neighbor).vel
            alignment_x += velocity.x
            alignment_y += velocity.y
    alignment_x /= len(neighbors)
    alignment_y /= len(neighbors)
    alignment_direction = safe_normalize(Vector2(alignment_x, alignment_y))

    separation_x, separation_y = 0.0, 0.0
    for neighbor in neighbors:
        distance = (neighbor.pos - position).length()
        if distance < separation and distance > 0:
            away = safe_normalize(position - neighbor.pos)
            separation_x += away.x / distance
            separation_y += away.y / distance

    return (
        cohesion_direction.x * cohesion + alignment_direction.x * alignment + separation_x * 0.5,
        cohesion_direction.y * cohesion + alignment_direction.y * alignment + separation_y * 0.5,
    )
