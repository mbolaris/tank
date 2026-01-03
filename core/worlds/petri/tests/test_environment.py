"""Unit tests for Petri environment physics."""

import unittest
from unittest.mock import MagicMock

from core.math_utils import Vector2
from core.worlds.petri.environment import PetriEnvironment
from core.worlds.petri.geometry import PETRI_CENTER_X, PETRI_CENTER_Y, PETRI_RADIUS


class TestPetriEnvironment(unittest.TestCase):
    def setUp(self):
        self.env = PetriEnvironment(
            width=1000,
            height=1000,
            rng=MagicMock(),
        )

    def test_collision_inside_dish(self):
        # Agent safely inside
        agent = MagicMock()
        agent.pos = Vector2(PETRI_CENTER_X, PETRI_CENTER_Y)
        agent.width = 20
        agent.vel = Vector2(0, 0)
        
        resolved = self.env.resolve_boundary_collision(agent)
        self.assertTrue(resolved)

    def test_collision_boundary(self):
        # Agent outside dish
        # Place agent far to the right
        agent = MagicMock()
        agent.width = 20
        r = agent.width / 2
        
        # Position so center is outside
        # Center X = PETRI_CENTER_X + PETRI_RADIUS + 10
        agent.pos = Vector2(PETRI_CENTER_X + PETRI_RADIUS + 10 - r, PETRI_CENTER_Y - r)
        agent.rect = MagicMock()
        
        # Moving outward
        agent.vel = Vector2(10, 0)
        
        resolved = self.env.resolve_boundary_collision(agent)
        self.assertTrue(resolved)
        
        # Should be pushed back in
        # agent.pos.x + r should be <= PETRI_CENTER_X + PETRI_RADIUS
        agent_cx = agent.pos.x + r
        dist = agent_cx - PETRI_CENTER_X
        self.assertLessEqual(dist, PETRI_RADIUS + 0.001)
        
        # Should have reflected velocity (moving left now)
        self.assertLess(agent.vel.x, 0)
