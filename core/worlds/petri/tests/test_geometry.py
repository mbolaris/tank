"""Unit tests for Petri geometry helpers."""

import math
import unittest

from core.worlds.petri.geometry import circle_perimeter_points, reflect_velocity


class TestPetriGeometry(unittest.TestCase):
    def test_reflect_velocity_simple(self):
        # Reflect bouncing off a vertical wall (normal pointing right +x)
        vx, vy = -10, 0
        nx, ny = 1, 0  # Wall on left, normal pointing in
        rx, ry = reflect_velocity(vx, vy, nx, ny)
        self.assertAlmostEqual(rx, 10)
        self.assertAlmostEqual(ry, 0)

    def test_reflect_velocity_diagonal(self):
        # 45 degree impact
        vx, vy = -10, -10
        # Normal pointing diagonal in (1, 1) normalized
        inv_sqrt2 = 1.0 / math.sqrt(2)
        nx, ny = inv_sqrt2, inv_sqrt2
        
        rx, ry = reflect_velocity(vx, vy, nx, ny)
        # Should bounce back opposite? 
        # v = (-10, -10), n = (0.7, 0.7)
        # dot = -14.14
        # r = v - 2*dot*n = (-10, -10) - 2*(-14.14)*(0.7, 0.7)
        # = (-10, -10) + 20 -> (10, 10) roughly.
        self.assertAlmostEqual(rx, 10)
        self.assertAlmostEqual(ry, 10)

    def test_circle_perimeter_points(self):
        cx, cy, r = 100, 100, 50
        count = 4
        points = circle_perimeter_points(cx, cy, r, count)
        
        self.assertEqual(len(points), 4)
        
        # Check point 0 (at angle 0 -> right)
        x, y, nx, ny = points[0]
        self.assertAlmostEqual(x, 150)
        self.assertAlmostEqual(y, 100)
        # Normal should point inward (left) -> (-1, 0)
        self.assertAlmostEqual(nx, -1)
        self.assertAlmostEqual(ny, 0)
        
        # Check point 1 (at angle 90 -> down in screen coords)
        # angle = pi/2
        x, y, nx, ny = points[1]
        self.assertAlmostEqual(x, 100)
        self.assertAlmostEqual(y, 150)
        # Normal should point inward (up) -> (0, -1)
        self.assertAlmostEqual(nx, 0)
        self.assertAlmostEqual(ny, -1)
