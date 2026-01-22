from __future__ import annotations

from unittest.mock import MagicMock

from backend.snapshots.tank_snapshot_builder import TankSnapshotBuilder
from core.entities.ball import Ball
from core.entities.base import Castle
from core.entities.fish import Fish

# Import GoalZone dynamically or mock it if needed
# (GoalZone is in core.entities.goal_zone)
from core.entities.goal_zone import GoalZone
from core.entities.plant import Plant, PlantNectar
from core.entities.predators import Crab
from core.entities.resources import Food
from core.worlds.shared.identity import TankLikeEntityIdentityProvider


# Mock necessary dependencies for Entity creation
class MockGenome:
    def to_dict(self):
        return {"mock": "genome"}

    class Physical:
        def __init__(self):
            self.color_hue = MagicMock(value=0.5)

    physical = Physical()

    class Behavioral:
        pass

    behavioral = Behavioral()


class MockWorld:
    def __init__(self):
        self.rng = MagicMock()
        self.rng.uniform.return_value = 0.5


def test_snapshot_builder_regression_all_types():
    """Verify snapshot builder correctly identifies and enriches all entity types."""
    provider = TankLikeEntityIdentityProvider()
    builder = TankSnapshotBuilder(identity_provider=provider)

    # Create dummy entities
    # Fish
    fish = MagicMock(spec=Fish)
    fish.pos = MagicMock(x=10, y=10)
    fish.width = 10
    fish.height = 10
    fish.vel = MagicMock(x=1, y=1)
    fish.energy = 100
    fish.generation = 1
    fish.species = "test_species"
    # Create a mock for lifecycle component
    lifecycle = MagicMock()
    lifecycle.age = 50
    fish._lifecycle_component = lifecycle
    fish.genome = MockGenome()
    # Mocking snapshot_type if the class doesn't have it, but strict mocks might fail
    # if we don't spec correctly.
    # However, EntityIdentityProvider uses protocol checks or class name.
    # We should ensure the Mock behaves like the real class for identity provider.
    fish.snapshot_type = "fish"  # Explicitly set for mock

    # Plant
    plant = MagicMock(spec=Plant)
    plant.pos = MagicMock(x=20, y=20)
    plant.width = 20
    plant.height = 20
    plant.energy = 50
    plant.max_energy = 100
    plant.genome = MockGenome()
    plant.snapshot_type = "plant"
    plant.get_fractal_iterations.return_value = 2

    # Food
    food = MagicMock(spec=Food)
    food.pos = MagicMock(x=30, y=30)
    food.width = 5
    food.height = 5
    food.snapshot_type = "food"
    food.energy = 10

    # Nectar
    nectar = MagicMock(spec=PlantNectar)
    nectar.pos = MagicMock(x=40, y=40)
    nectar.width = 3
    nectar.height = 3
    nectar.snapshot_type = "plant_nectar"
    nectar.energy = 5
    nectar.source_plant = None

    # Crab
    crab = MagicMock(spec=Crab)
    crab.pos = MagicMock(x=50, y=50)
    crab.width = 15
    crab.height = 15
    crab.vel = MagicMock(x=0, y=0)
    crab.vel.length_squared.return_value = 0.0
    crab.snapshot_type = "crab"  # Provider might fallback to class name if missing
    crab.energy = 80
    crab.can_hunt = True

    # Castle
    castle = MagicMock(spec=Castle)
    castle.pos = MagicMock(x=60, y=60)
    castle.width = 40
    castle.height = 40
    # Castle usually uses class name "castle"
    # But mock spec might not be enough for class name check if we don't name the mock class
    # So we'll set snapshot_type or configure __class__.__name__
    castle.__class__.__name__ = "Castle"

    # Ball
    ball = MagicMock(spec=Ball)
    ball.pos = MagicMock(x=70, y=70)
    ball.width = 8
    ball.height = 8
    ball.__class__.__name__ = "Ball"

    # GoalZone
    goal = MagicMock(spec=GoalZone)
    goal.pos = MagicMock(x=80, y=80)
    goal.width = 30
    goal.height = 60
    goal.__class__.__name__ = "GoalZone"
    goal.radius = 15
    goal.team = "A"
    goal.goal_id = "goal_left"

    # Test each entity

    # Fish
    snap_fish = builder.to_snapshot(fish)
    assert snap_fish.type == "fish"
    assert snap_fish.render_hint["style"] == "pixel"
    assert snap_fish.render_hint["sprite"] == "fish"

    # Plant
    snap_plant = builder.to_snapshot(plant)
    assert snap_plant.type == "plant"
    assert snap_plant.render_hint["style"] == "fractal"

    # Food
    snap_food = builder.to_snapshot(food)
    assert snap_food.type == "food"

    # Nectar
    snap_nectar = builder.to_snapshot(nectar)
    assert snap_nectar.type == "plant_nectar"

    # Crab
    snap_crab = builder.to_snapshot(crab)
    assert snap_crab.type == "crab"
    assert snap_crab.render_hint["sprite"] == "crab"

    # Castle
    snap_castle = builder.to_snapshot(castle)
    # Check what calling code produces.
    # If mock doesn't have snapshot_type, provider uses lower(class name).
    # Since we set castle.__class__.__name__ = "Castle", it should be "castle".
    assert snap_castle.type == "castle"

    # Ball
    snap_ball = builder.to_snapshot(ball)
    assert snap_ball.type == "ball"
    assert snap_ball.render_hint["style"] == "soccer_ball"

    # GoalZone
    snap_goal = builder.to_snapshot(goal)
    assert snap_goal.type == "goalzone"
    assert snap_goal.render_hint["style"] == "goal_zone"
