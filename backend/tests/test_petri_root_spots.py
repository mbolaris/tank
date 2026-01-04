
import math
import pytest
from core.root_spots import RootSpot
from core.worlds.petri.root_spots import CircularRootSpotManager
from core.worlds.petri.geometry import PETRI_RADIUS, PETRI_CENTER_X, PETRI_CENTER_Y

class TestRootSpotRadialInward:
    def test_radial_inward_calculation(self):
        # Setup a spot at x=100, y=0 (relative to 0,0 for simplicity if using explicit angle)
        # But RootSpot uses absolute coordinates.
        cx, cy = 500, 500
        r = 100
        # Spot at 0 degrees (right)
        spot_x = cx + r
        spot_y = cy
        angle = 0.0
        
        spot = RootSpot(spot_id=1, x=spot_x, y=spot_y)
        spot.anchor_mode = "radial_inward"
        spot.angle = angle
        
        # Plant size
        w, h = 20, 20
        # Expected behavior:
        # Plant is roughly circular with radius = 10.
        # Normal points inward (-1, 0).
        # Plant center = spot + normal * radius = (600, 500) + (-1, 0)*10 = (590, 500).
        # TopLeft = center - (w/2, h/2) = (590 - 10, 500 - 10) = (580, 490).
        
        tx, ty = spot.get_anchor_topleft(w, h)
        
        assert math.isclose(tx, 580, abs_tol=0.1)
        assert math.isclose(ty, 490, abs_tol=0.1)

    def test_radial_inward_calculation_90_degrees(self):
        # Spot at 90 degrees (bottom)
        cx, cy = 500, 500
        r = 100
        angle = math.pi / 2
        spot_x = cx
        spot_y = cy + r # 600
        
        spot = RootSpot(spot_id=2, x=spot_x, y=spot_y)
        spot.anchor_mode = "radial_inward"
        spot.angle = angle
        
        w, h = 30, 30
        # Radius = 15
        # Normal = (0, -1) (pointing UP/Inward from bottom)
        # Center = (500, 600) + (0, -1)*15 = (500, 585)
        # TopLeft = (500 - 15, 585 - 15) = (485, 570)
        
        tx, ty = spot.get_anchor_topleft(w, h)
        
        assert math.isclose(tx, 485, abs_tol=0.1)
        assert math.isclose(ty, 570, abs_tol=0.1)

class TestCircularRootSpotManager:
    def test_initialization_on_perimeter(self):
        # Mock RNG
        import random
        rng = random.Random(42)
        
        manager = CircularRootSpotManager(screen_width=1000, screen_height=1000, spot_count=4, rng=rng)
        
        assert len(manager.spots) == 4
        
        for spot in manager.spots:
            # Check geometry
            dx = spot.x - PETRI_CENTER_X
            dy = spot.y - PETRI_CENTER_Y
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Should be exactly on radius
            assert math.isclose(dist, PETRI_RADIUS, abs_tol=0.1)
            
            # Check anchor mode
            assert spot.anchor_mode == "radial_inward"
            assert spot.angle is not None
            
            # Verify angle matches position
            calc_angle = math.atan2(dy, dx)
            # Normalize angles to 0..2pi or -pi..pi range equivalence?
            # math.atan2 returns -pi to pi. spot.angle might be 0 to 2pi.
            # Compare unit vectors
            assert math.isclose(math.cos(spot.angle), math.cos(calc_angle), abs_tol=0.001)
            assert math.isclose(math.sin(spot.angle), math.sin(calc_angle), abs_tol=0.001)
