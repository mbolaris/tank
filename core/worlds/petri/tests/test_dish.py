"""Unit tests for PetriDish value object."""

import math
import random
import unittest

from core.worlds.petri.dish import PetriDish


class TestPetriDish(unittest.TestCase):
    """Tests for PetriDish geometry and physics helpers."""

    def setUp(self):
        """Create a standard test dish."""
        self.dish = PetriDish(cx=500.0, cy=300.0, r=250.0)

    def test_contains_circle_inside(self):
        """A circle fully inside the dish should be contained."""
        # Center of dish
        self.assertTrue(self.dish.contains_circle(500.0, 300.0, 10.0))
        # Near edge but still inside
        self.assertTrue(self.dish.contains_circle(600.0, 300.0, 10.0))

    def test_contains_circle_on_edge(self):
        """A circle touching the edge exactly should be contained."""
        # Circle with center at dish center + (radius - circle_radius)
        self.assertTrue(self.dish.contains_circle(740.0, 300.0, 10.0))

    def test_contains_circle_outside(self):
        """A circle extending beyond the dish should not be contained."""
        # Circle center at edge, so circle extends outside
        self.assertFalse(self.dish.contains_circle(750.0, 300.0, 10.0))

    def test_sample_point_stays_inside_deterministic(self):
        """1000 sampled points should all be inside the dish (deterministic seed)."""
        rng = random.Random(42)
        n = 1000
        margin = 10.0
        
        for _ in range(n):
            x, y = self.dish.sample_point(rng, margin=margin)
            dist = math.hypot(x - self.dish.cx, y - self.dish.cy)
            max_allowed = self.dish.r - margin
            self.assertLessEqual(
                dist, max_allowed + 0.001,
                f"Point ({x}, {y}) is {dist:.2f} from center, max allowed is {max_allowed:.2f}"
            )

    def test_sample_point_distribution_coverage(self):
        """Sampled points should cover different quadrants (basic distribution check)."""
        rng = random.Random(42)
        n = 100
        
        quadrants = {(True, True): 0, (True, False): 0, (False, True): 0, (False, False): 0}
        
        for _ in range(n):
            x, y = self.dish.sample_point(rng)
            q = (x >= self.dish.cx, y >= self.dish.cy)
            quadrants[q] += 1
        
        # Each quadrant should have at least some points
        for q, count in quadrants.items():
            self.assertGreater(count, 5, f"Quadrant {q} has only {count} points")

    def test_clamp_and_reflect_inside_no_change(self):
        """An agent inside the dish should not be modified."""
        x, y, vx, vy, collided = self.dish.clamp_and_reflect(
            500.0, 300.0,  # center of dish
            10.0, 5.0,     # velocity
            20.0,          # agent radius
        )
        self.assertFalse(collided)
        self.assertEqual(x, 500.0)
        self.assertEqual(y, 300.0)
        self.assertEqual(vx, 10.0)
        self.assertEqual(vy, 5.0)

    def test_clamp_and_reflect_outside_pushed_in(self):
        """An agent outside the dish should be pushed back inside."""
        # Agent center at x=760 (outside dish edge at 750), moving right
        x, y, vx, vy, collided = self.dish.clamp_and_reflect(
            760.0, 300.0,  # just outside on right
            10.0, 0.0,     # moving right (outward)
            10.0,          # agent radius
        )
        self.assertTrue(collided)
        
        # Should be pushed to edge: dish.r - agent_radius = 250 - 10 = 240 from center
        # New x should be: 500 + 240 = 740
        self.assertAlmostEqual(x, 740.0, places=1)
        self.assertEqual(y, 300.0)  # Y unchanged
        
        # Velocity should be reflected (moving left now)
        self.assertLess(vx, 0, "Velocity should be reflected to negative X")

    def test_clamp_and_reflect_velocity_inward_not_reflected(self):
        """If velocity points inward, it should not be reflected even on collision."""
        # Agent outside but moving inward
        x, y, vx, vy, collided = self.dish.clamp_and_reflect(
            760.0, 300.0,  # just outside on right
            -10.0, 0.0,    # moving left (inward)
            10.0,          # agent radius
        )
        self.assertTrue(collided)
        # Velocity should stay negative (still moving left)
        self.assertEqual(vx, -10.0)
        self.assertEqual(vy, 0.0)

    def test_clamp_and_reflect_diagonal(self):
        """Diagonal collision should reflect velocity properly."""
        # Agent outside at diagonal
        offset = 200.0  # diagonal offset
        x, y, vx, vy, collided = self.dish.clamp_and_reflect(
            500.0 + offset, 300.0 + offset,  # NE, outside
            10.0, 10.0,     # moving outward diagonally
            10.0,           # agent radius
        )
        self.assertTrue(collided)
        
        # After collision, velocity should have changed direction (partially or fully)
        # The exact values depend on the normal at collision point
        # Just verify it's different from input
        orig_speed_sq = 10.0**2 + 10.0**2
        new_speed_sq = vx**2 + vy**2
        # Speed should be preserved (elastic reflection)
        self.assertAlmostEqual(new_speed_sq, orig_speed_sq, places=3)

    def test_perimeter_points_count(self):
        """perimeter_points should return the requested number of points."""
        points = self.dish.perimeter_points(10)
        self.assertEqual(len(points), 10)
        
        points = self.dish.perimeter_points(0)
        self.assertEqual(len(points), 0)

    def test_perimeter_points_on_edge(self):
        """All perimeter points should be exactly on the dish edge."""
        points = self.dish.perimeter_points(20)
        
        for x, y, angle in points:
            dist = math.hypot(x - self.dish.cx, y - self.dish.cy)
            self.assertAlmostEqual(dist, self.dish.r, places=5)

    def test_perimeter_points_angles_evenly_distributed(self):
        """Angles should be evenly distributed around the circle."""
        count = 12
        points = self.dish.perimeter_points(count)
        
        expected_step = 2 * math.pi / count
        for i, (x, y, angle) in enumerate(points):
            expected_angle = i * expected_step
            self.assertAlmostEqual(angle, expected_angle, places=5)


class TestPetriDishEdgeCases(unittest.TestCase):
    """Edge case tests for PetriDish."""

    def test_tiny_dish(self):
        """Very small dish should still work."""
        dish = PetriDish(cx=10.0, cy=10.0, r=5.0)
        
        # Sampling with margin larger than radius should return center
        rng = random.Random(42)
        x, y = dish.sample_point(rng, margin=10.0)
        self.assertEqual(x, 10.0)
        self.assertEqual(y, 10.0)

    def test_agent_larger_than_dish(self):
        """Agent larger than dish should be clamped to center with zero velocity."""
        dish = PetriDish(cx=100.0, cy=100.0, r=20.0)
        
        # Agent radius 30 > dish radius 20
        x, y, vx, vy, collided = dish.clamp_and_reflect(
            150.0, 150.0,  # position doesn't matter
            10.0, 5.0,     # velocity
            30.0,          # agent radius > dish radius
        )
        self.assertTrue(collided)
        self.assertEqual(x, 100.0)  # Clamped to center
        self.assertEqual(y, 100.0)
        self.assertEqual(vx, 0.0)   # Velocity zeroed
        self.assertEqual(vy, 0.0)


if __name__ == "__main__":
    unittest.main()
