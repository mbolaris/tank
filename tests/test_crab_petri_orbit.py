"""Test crab Petri dish perimeter orbit behavior.

Verifies that in Petri mode, crabs orbit the dish perimeter instead of
bouncing on a non-existent bottom edge.
"""

from __future__ import annotations

import math

from core.entities.predators import Crab
from core.worlds.petri.dish import PetriDish


class MockPetriEnvironment:
    """Minimal mock environment for testing Petri orbit behavior."""

    def __init__(self, dish: PetriDish, rng) -> None:
        self.dish = dish
        self.rng = rng
        self.world_type = "petri"
        self.screen_width = 800
        self.screen_height = 600

    def get_bounds(self):
        """Return screen bounds for Agent base class."""
        return ((0, 0), (self.screen_width, self.screen_height))


class MockTankEnvironment:
    """Minimal mock environment for tank mode testing."""

    def __init__(self, rng) -> None:
        self.rng = rng
        self.world_type = "tank"
        self.dish = None
        self.screen_width = 800
        self.screen_height = 600

    def get_bounds(self):
        """Return screen bounds for Agent base class."""
        return ((0, 0), (self.screen_width, self.screen_height))


def test_crab_orbits_petri_perimeter() -> None:
    """Test that crab stays on perimeter and moves in Petri mode."""
    import random

    rng = random.Random(42)
    dish = PetriDish(cx=400, cy=300, r=280)
    env = MockPetriEnvironment(dish, rng)

    # Create crab near perimeter
    crab = Crab(environment=env, x=400 + 250, y=300)

    # Record initial position
    initial_positions = []
    for _ in range(10):
        crab.update(frame_count=0, time_modifier=1.0)
        cx = crab.pos.x + crab.width / 2
        cy = crab.pos.y + crab.height / 2
        initial_positions.append((cx, cy))

    # Crab should be near perimeter
    for cx, cy in initial_positions:
        dist_from_center = math.hypot(cx - dish.cx, cy - dish.cy)
        expected_orbit_radius = dish.r - crab.width / 2 - 2.0
        # Allow some tolerance for the orbit
        assert abs(dist_from_center - expected_orbit_radius) < 10, (
            f"Crab should be near perimeter, got dist={dist_from_center}, "
            f"expected ~{expected_orbit_radius}"
        )

    # Crab should have moved (not stationary)
    first = initial_positions[0]
    last = initial_positions[-1]
    moved = math.hypot(last[0] - first[0], last[1] - first[1])
    assert moved > 0.5, f"Crab should move along perimeter, moved {moved}"


def test_crab_uses_tank_patrol_without_dish() -> None:
    """Test that crab uses bottom patrol when no dish is present (tank mode)."""
    import random

    rng = random.Random(43)
    env = MockTankEnvironment(rng)

    crab = Crab(environment=env, x=400, y=550)

    # Run a few updates
    for i in range(5):
        crab.update(frame_count=i, time_modifier=1.0)

    # In tank mode, vertical velocity should be 0 (bottom patrol)
    assert crab.vel.y == 0, "Tank mode crab should stay on bottom"
    # Horizontal velocity should be non-zero (patrolling)
    assert abs(crab.vel.x) > 0, "Tank mode crab should patrol horizontally"


def test_crab_orbit_state_preserved() -> None:
    """Test that orbit theta and direction are maintained across updates."""
    import random

    rng = random.Random(44)
    dish = PetriDish(cx=400, cy=300, r=280)
    env = MockPetriEnvironment(dish, rng)

    crab = Crab(environment=env, x=400 + 250, y=300)

    # First update initializes theta
    crab.update(frame_count=0, time_modifier=1.0)
    initial_theta = crab._orbit_theta
    initial_dir = crab._orbit_dir

    assert initial_theta is not None, "Theta should be initialized"
    assert initial_dir in (-1, 1), "Dir should be +1 or -1"

    # Subsequent updates should change theta
    for i in range(10):
        crab.update(frame_count=i + 1, time_modifier=1.0)

    assert crab._orbit_theta != initial_theta, "Theta should change during orbit"
    assert crab._orbit_dir == initial_dir, "Direction should stay consistent"
