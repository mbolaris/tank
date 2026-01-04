"""Unit tests for RootSpot enhancements."""

import unittest
import random

from core.root_spots import RootSpot
from core.worlds.petri.dish import PetriDish
from core.worlds.petri.root_spots import CircularRootSpotManager


class TestRootSpots(unittest.TestCase):
    def test_root_spot_anchor_bottom(self):
        spot = RootSpot(spot_id=0, x=100, y=100)
        spot.anchor_mode = "bottom"
        
        # Plant 20x40
        x, y = spot.get_anchor_topleft(20, 40)
        
        # Should center X (100 - 10 = 90) and anchor bottom Y (100 - 40 = 60)
        self.assertEqual(x, 90)
        self.assertEqual(y, 60)

    def test_root_spot_anchor_center(self):
        spot = RootSpot(spot_id=0, x=100, y=100)
        spot.anchor_mode = "center"
        
        # Plant 20x40
        x, y = spot.get_anchor_topleft(20, 40)
        
        # Should center X (100 - 10 = 90) and center Y (100 - 20 = 80)
        self.assertEqual(x, 90)
        self.assertEqual(y, 80)

    def test_circular_manager_initialization(self):
        dish = PetriDish(cx=400.0, cy=300.0, r=290.0)
        manager = CircularRootSpotManager(dish=dish)
        self.assertGreater(len(manager.spots), 0)
        
        # Check spot properties
        for spot in manager.spots:
            self.assertEqual(spot.anchor_mode, "radial_inward")
            # Should be on the perimeter
            import math
            dist = math.hypot(spot.x - dish.cx, spot.y - dish.cy)
            self.assertAlmostEqual(dist, dish.r, places=3)

    def test_circular_manager_with_rng(self):
        dish = PetriDish(cx=400.0, cy=300.0, r=290.0)
        rng = random.Random(42)
        manager = CircularRootSpotManager(dish=dish, rng=rng)
        self.assertGreater(len(manager.spots), 0)

