"""Unit tests for Petri environment physics."""

import unittest
from unittest.mock import MagicMock

from core.math_utils import Vector2
from core.worlds.petri.dish import PetriDish
from core.worlds.petri.environment import PetriEnvironment


class TestPetriEnvironment(unittest.TestCase):
    def setUp(self):
        # Create a dish matching the test dimensions
        self.dish = PetriDish(cx=500.0, cy=500.0, r=290.0)
        self.env = PetriEnvironment(
            width=1000,
            height=1000,
            rng=MagicMock(),
            dish=self.dish,
        )

    def test_collision_inside_dish(self):
        # Agent safely inside (at dish center)
        agent = MagicMock()
        agent.pos = Vector2(self.dish.cx - 10, self.dish.cy - 10)  # Offset by half width
        agent.width = 20
        agent.height = 20
        agent.vel = Vector2(0, 0)

        resolved = self.env.resolve_boundary_collision(agent)
        self.assertTrue(resolved)

    def test_collision_boundary(self):
        # Agent outside dish
        # Place agent far to the right
        agent = MagicMock()
        agent.width = 20
        agent.height = 20
        r = agent.width / 2

        # Position so center is outside: dish center + dish radius + 10
        outside_x = self.dish.cx + self.dish.r + 10 - r
        agent.pos = Vector2(outside_x, self.dish.cy - r)
        agent.rect = MagicMock()

        # Moving outward
        agent.vel = Vector2(10, 0)

        resolved = self.env.resolve_boundary_collision(agent)
        self.assertTrue(resolved)

        # Should be pushed back in
        agent_cx = agent.pos.x + r
        dist = agent_cx - self.dish.cx
        max_allowed = self.dish.r
        self.assertLessEqual(dist, max_allowed + 0.001)

        # Should have reflected velocity (moving left now)
        self.assertLess(agent.vel.x, 0)

    def test_collision_uses_max_dimension_for_radius(self):
        # Agent with different width and height
        agent = MagicMock()
        agent.width = 20
        agent.height = 40  # height > width

        # Position agent exactly at max distance for height-based radius
        # max_dist = dish.r - max(w, h)/2 = 290 - 20 = 270
        # So agent center at dish_cx + 271 should trigger collision
        agent.pos = Vector2(self.dish.cx + 271 - 10, self.dish.cy - 20)
        agent.rect = MagicMock()
        agent.vel = Vector2(10, 0)

        resolved = self.env.resolve_boundary_collision(agent)
        self.assertTrue(resolved)

        # Velocity should be reflected since we're outside and moving outward
        self.assertLess(agent.vel.x, 0)
