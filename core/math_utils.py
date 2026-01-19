"""Centralized math utilities for the simulation.

This module provides pure Python mathematical utilities for the simulation,
including a Vector2 implementation for 2D vector operations.
"""

from __future__ import annotations

import math

_EPSILON = 1e-9


class Vector2:
    """A 2D vector class for mathematical operations."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x: float = float(x)
        self.y: float = float(y)

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __iadd__(self, other: Vector2) -> Vector2:
        self.x += other.x
        self.y += other.y
        return self

    def __isub__(self, other: Vector2) -> Vector2:
        self.x -= other.x
        self.y -= other.y
        return self

    def __imul__(self, scalar: float) -> Vector2:
        self.x *= scalar
        self.y *= scalar
        return self

    def __itruediv__(self, scalar: float) -> Vector2:
        self.x /= scalar
        self.y /= scalar
        return self

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalize(self) -> Vector2:
        length = math.sqrt(self.x * self.x + self.y * self.y)
        if length == 0:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def update(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def copy(self) -> Vector2:
        """Return a copy of this vector."""
        return Vector2(self.x, self.y)

    def __eq__(self, other: object) -> bool:
        """Check if two vectors are equal."""
        if not isinstance(other, Vector2):
            return NotImplemented
        return math.isclose(self.x, other.x, abs_tol=_EPSILON) and math.isclose(
            self.y, other.y, abs_tol=_EPSILON
        )

    def __ne__(self, other: object) -> bool:
        """Check if two vectors are not equal."""
        eq_result = self.__eq__(other)
        if eq_result is NotImplemented:
            return NotImplemented
        return not eq_result

    def __repr__(self) -> str:
        return f"Vector2({self.x}, {self.y})"

    def add_inplace(self, other: Vector2) -> Vector2:
        """Add another vector to this one in-place."""
        self.x += other.x
        self.y += other.y
        return self

    def sub_inplace(self, other: Vector2) -> Vector2:
        """Subtract another vector from this one in-place."""
        self.x -= other.x
        self.y -= other.y
        return self

    def mul_inplace(self, scalar: float) -> Vector2:
        """Multiply this vector by a scalar in-place."""
        self.x *= scalar
        self.y *= scalar
        return self

    def div_inplace(self, scalar: float) -> Vector2:
        """Divide this vector by a scalar in-place."""
        self.x /= scalar
        self.y /= scalar
        return self

    def normalize_inplace(self) -> Vector2:
        """Normalize this vector in-place."""
        length = math.sqrt(self.x * self.x + self.y * self.y)
        if length > 0:
            self.x /= length
            self.y /= length
        else:
            self.x = 0.0
            self.y = 0.0
        return self

    def limit_inplace(self, max_length: float) -> Vector2:
        """Limit the length of this vector in-place."""
        length_sq = self.x * self.x + self.y * self.y
        if length_sq > max_length * max_length and length_sq > 0:
            length = math.sqrt(length_sq)
            self.x = (self.x / length) * max_length
            self.y = (self.y / length) * max_length
        return self

    @staticmethod
    def distance_squared(x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate squared distance between two points without allocating Vector2 objects.

        This is a performance optimization for hot paths where we only need to compare
        distances or don't need the actual distance value.

        Args:
            x1, y1: First point coordinates
            x2, y2: Second point coordinates

        Returns:
            Squared distance between the points
        """
        dx = x2 - x1
        dy = y2 - y1
        return dx * dx + dy * dy

    @staticmethod
    def distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate distance between two points without allocating Vector2 objects.

        This is a performance optimization for hot paths.

        Args:
            x1, y1: First point coordinates
            x2, y2: Second point coordinates

        Returns:
            Distance between the points
        """
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def distance_between(v1: Vector2, v2: Vector2) -> float:
        """Calculate distance between two Vector2 objects.

        This is a convenience method that avoids creating temporary Vector2 objects
        from subtraction. Use this instead of (v1 - v2).length() for better performance.

        Args:
            v1: First vector/position
            v2: Second vector/position

        Returns:
            Distance between the vectors

        Example:
            >>> pos1 = Vector2(0, 0)
            >>> pos2 = Vector2(3, 4)
            >>> distance = Vector2.distance_between(pos1, pos2)  # Returns 5.0
        """
        dx = v2.x - v1.x
        dy = v2.y - v1.y
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def distance_squared_between(v1: Vector2, v2: Vector2) -> float:
        """Calculate squared distance between two Vector2 objects.

        This is a convenience method for distance comparisons where you don't need
        the actual distance value. Avoids the expensive sqrt() operation.

        Args:
            v1: First vector/position
            v2: Second vector/position

        Returns:
            Squared distance between the vectors

        Example:
            >>> pos1 = Vector2(0, 0)
            >>> pos2 = Vector2(3, 4)
            >>> dist_sq = Vector2.distance_squared_between(pos1, pos2)  # Returns 25.0
        """
        dx = v2.x - v1.x
        dy = v2.y - v1.y
        return dx * dx + dy * dy


__all__ = ["Vector2"]
