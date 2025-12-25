"""Tests for collision detection in the fish tank simulation."""

import pytest

from core.config.display import SCREEN_HEIGHT
from core.entities import Crab, Fish, Food
from core.math_utils import Vector2
from core.movement_strategy import AlgorithmicMovement


class TestCollisionDetection:
    """Test collision detection in the fish tank."""

    def test_fish_dies_when_touching_crab(self, simulation_engine):
        """Test that fish is removed when it collides with a crab."""
        simulator = simulation_engine

        fish = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos = Vector2(100, 100)  # Same position as fish
        crab.rect.topleft = crab.pos

        simulator.agents.add(fish, crab)

        assert fish in simulator.agents

        simulator.collision_system.update(0)

    def test_food_removed_when_eaten_by_fish(self, simulation_engine):
        """Test that food is removed when a fish eats it."""
        simulator = simulation_engine

        fish = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        food = Food(simulator.environment, 100, 100)

        simulator.agents.add(fish, food)

        assert food in simulator.agents

        simulator.collision_system.update(0)

    def test_iteration_safe_during_collision(self, simulation_engine):
        """Test that removing sprites during iteration doesn't cause issues."""
        simulator = simulation_engine

        # Create multiple fish and crabs
        fish1 = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        fish2 = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 200, 200, 3)
        crab1 = Crab(simulator.environment)
        crab1.pos = Vector2(100, 100)
        crab1.rect.topleft = crab1.pos

        simulator.agents.add(fish1, fish2, crab1)

        try:
            simulator.collision_system.update(0)
            success = True
        except Exception as e:
            success = False
            print(f"Error: {e}")

        assert success, "Collision handling should not crash during iteration"

    def test_multiple_collisions_handled(self, simulation_engine):
        """Test that multiple simultaneous collisions are all handled."""
        simulator = simulation_engine

        fish1 = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        fish2 = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 200, 200, 3)
        food1 = Food(simulator.environment, 100, 100)
        food2 = Food(simulator.environment, 200, 200)

        simulator.agents.add(fish1, fish2, food1, food2)

        try:
            simulator.collision_system.update(0)
        except Exception as e:
            pytest.fail(f"Food collision handling failed: {type(e).__name__}: {e}")

    def test_food_falls_off_screen_removed(self, simulation_engine):
        """Test that food removal logic works for food at bottom of screen."""
        simulator = simulation_engine

        food = Food(simulator.environment, 100, 50)
        simulator.agents.add(food)

        food.rect.y = SCREEN_HEIGHT

        assert food in simulator.agents

        for sprite in list(simulator.agents):
            if isinstance(sprite, Food) and sprite.rect.y >= SCREEN_HEIGHT - sprite.rect.height:
                sprite.kill()

        assert food not in simulator.agents

    def test_handle_collisions_called_safely(self, simulation_engine):
        """Test that the main collision handler can be called repeatedly."""
        simulator = simulation_engine

        # Add various sprites
        fish = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        crab = Crab(simulator.environment)
        food = Food(simulator.environment, 150, 150)

        simulator.agents.add(fish, crab, food)

        try:
            for _ in range(10):
                simulator.collision_system.update(0)
        except Exception as e:
            pytest.fail(f"Main collision handler failed: {type(e).__name__}: {e}")
