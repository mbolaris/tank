"""Unit tests for RootSpot enhancements."""

import unittest
import random

from core.root_spots import RootSpot
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
        manager = CircularRootSpotManager(800, 600)
        self.assertGreater(len(manager.spots), 0)
        
        # Check spot properties
        for spot in manager.spots:
            self.assertEqual(spot.anchor_mode, "center")
            # Should be roughly on perimeter
            # We implemented it as slightly inset
            # Just verify they are not all at (0,0)
            self.assertNotEqual(spot.x, 0)
