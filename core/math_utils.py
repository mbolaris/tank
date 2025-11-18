"""Centralized math utilities for the simulation.

This module provides a single source of truth for mathematical utilities,
including Vector2 implementation that works with or without pygame.
"""

import math

try:
    from pygame.math import Vector2
except ImportError:
    # Fallback for environments without pygame
    class Vector2:
        """A 2D vector class compatible with pygame.math.Vector2 interface."""

        def __init__(self, x=0, y=0):
            self.x = float(x)
            self.y = float(y)

        def __add__(self, other):
            return Vector2(self.x + other.x, self.y + other.y)

        def __sub__(self, other):
            return Vector2(self.x - other.x, self.y - other.y)

        def __mul__(self, scalar):
            return Vector2(self.x * scalar, self.y * scalar)

        def __truediv__(self, scalar):
            return Vector2(self.x / scalar, self.y / scalar)

        def length(self):
            return math.sqrt(self.x**2 + self.y**2)

        def length_squared(self):
            return self.x**2 + self.y**2

        def normalize(self):
            length = self.length()
            if length == 0:
                return Vector2(0, 0)
            return Vector2(self.x / length, self.y / length)

        def dot(self, other):
            return self.x * other.x + self.y * other.y

        def update(self, x, y):
            self.x = float(x)
            self.y = float(y)

        def copy(self):
            """Return a copy of this vector."""
            return Vector2(self.x, self.y)

        def __eq__(self, other):
            """Check if two vectors are equal."""
            if not isinstance(other, Vector2):
                return False
            return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

        def __ne__(self, other):
            """Check if two vectors are not equal."""
            return not self.__eq__(other)

        def __repr__(self):
            return f"Vector2({self.x}, {self.y})"


__all__ = ["Vector2"]
