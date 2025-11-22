"""Centralized math utilities for the simulation.

This module provides pure Python mathematical utilities for the simulation,
including a Vector2 implementation for 2D vector operations.
"""

from __future__ import annotations

import math


class Vector2:
    """A 2D vector class for mathematical operations."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x: float = float(x)
        self.y: float = float(y)

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> "Vector2":
        return Vector2(self.x / scalar, self.y / scalar)

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalize(self) -> "Vector2":
        length = math.sqrt(self.x * self.x + self.y * self.y)
        if length == 0:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)

    def dot(self, other: "Vector2") -> float:
        return self.x * other.x + self.y * other.y

    def update(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def copy(self) -> "Vector2":
        """Return a copy of this vector."""
        return Vector2(self.x, self.y)

    def __eq__(self, other: object) -> bool:
        """Check if two vectors are equal."""
        if other.__class__ is not Vector2:
            return False
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __ne__(self, other: object) -> bool:
        """Check if two vectors are not equal."""
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"Vector2({self.x}, {self.y})"


    def add_inplace(self, other: "Vector2") -> "Vector2":
        """Add another vector to this one in-place."""
        self.x += other.x
        self.y += other.y
        return self

    def sub_inplace(self, other: "Vector2") -> "Vector2":
        """Subtract another vector from this one in-place."""
        self.x -= other.x
        self.y -= other.y
        return self

    def mul_inplace(self, scalar: float) -> "Vector2":
        """Multiply this vector by a scalar in-place."""
        self.x *= scalar
        self.y *= scalar
        return self

    def div_inplace(self, scalar: float) -> "Vector2":
        """Divide this vector by a scalar in-place."""
        self.x /= scalar
        self.y /= scalar
        return self

    def normalize_inplace(self) -> "Vector2":
        """Normalize this vector in-place."""
        length = math.sqrt(self.x * self.x + self.y * self.y)
        if length > 0:
            self.x /= length
            self.y /= length
        else:
            self.x = 0.0
            self.y = 0.0
        return self

    def limit_inplace(self, max_length: float) -> "Vector2":
        """Limit the length of this vector in-place."""
        length_sq = self.x * self.x + self.y * self.y
        if length_sq > max_length * max_length and length_sq > 0:
            length = math.sqrt(length_sq)
            self.x = (self.x / length) * max_length
            self.y = (self.y / length) * max_length
        return self


__all__ = ["Vector2"]
