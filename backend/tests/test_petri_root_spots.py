import math
import random

from core.root_spots import RootSpot
from core.worlds.petri.geometry import PETRI_CENTER_X, PETRI_CENTER_Y, PETRI_RADIUS
from core.worlds.petri.root_spots import CircularRootSpotManager


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
        # Radial inward no longer shifts inward. It centers on the spot.
        # Spot = (600, 500).
        # TopLeft = center - (w/2, h/2) = (600 - 10, 500 - 10) = (590, 490).

        tx, ty = spot.get_anchor_topleft(w, h)

        assert math.isclose(tx, 590, abs_tol=0.1)
        assert math.isclose(ty, 490, abs_tol=0.1)

    def test_radial_inward_calculation_90_degrees(self):
        # Spot at 90 degrees (bottom)
        cx, cy = 500, 500
        r = 100
        angle = math.pi / 2
        spot_x = cx
        spot_y = cy + r  # 600

        spot = RootSpot(spot_id=2, x=spot_x, y=spot_y)
        spot.anchor_mode = "radial_inward"
        spot.angle = angle

        w, h = 30, 30
        # Radius = 15
        # Spot = (500, 600).
        # TopLeft = (500 - 15, 600 - 15) = (485, 585)

        tx, ty = spot.get_anchor_topleft(w, h)

        assert math.isclose(tx, 485, abs_tol=0.1)
        assert math.isclose(ty, 585, abs_tol=0.1)


class MockPetriDish:
    def __init__(self, cx, cy, r):
        self.cx = cx
        self.cy = cy
        self.r = r

    def perimeter_points(self, count):
        points = []
        for i in range(count):
            angle = (2 * math.pi * i) / count
            x = self.cx + self.r * math.cos(angle)
            y = self.cy + self.r * math.sin(angle)
            points.append((x, y, angle))
        return points


class TestCircularRootSpotManager:
    def test_initialization_on_perimeter(self):
        # Mock RNG
        rng = random.Random(42)

        dish = MockPetriDish(PETRI_CENTER_X, PETRI_CENTER_Y, PETRI_RADIUS)

        manager = CircularRootSpotManager(
            dish=dish,
            rng=rng,
        )

        # Manager roughly calculates count based on circumference.
        # Circumference ~ 2 * pi * 500 ~ 3141. Spacing 45. ~70 spots.
        assert len(manager.spots) > 20

        for spot in manager.spots:
            # Check geometry
            dx = spot.x - PETRI_CENTER_X
            dy = spot.y - PETRI_CENTER_Y
            dist = math.sqrt(dx * dx + dy * dy)

            # Should be exactly on radius
            assert math.isclose(dist, PETRI_RADIUS, abs_tol=0.1)

            # Check anchor mode
            assert spot.anchor_mode == "radial_inward"
            assert spot.angle is not None
