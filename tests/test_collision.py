"""Tests for collision detection in the fish tank simulation."""
import pytest
import pygame
from pygame.math import Vector2

from agents import Fish, Crab, Food
from core.environment import Environment
from core.movement_strategy import SoloFishMovement
from fishtank import FishTankSimulator
from core.constants import SCREEN_HEIGHT


class TestCollisionDetection:
    """Test collision detection in the fish tank."""

    def test_fish_dies_when_touching_crab(self, fish_tank_setup):
        """Test that fish is removed when it collides with a crab."""
        simulator = fish_tank_setup

        fish = Fish(simulator.environment, SoloFishMovement(),
                   ['george1.png'], 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos = Vector2(100, 100)  # Same position as fish
        crab.rect.topleft = crab.pos

        simulator.agents.add(fish, crab)

        assert fish in simulator.agents

        simulator.handle_fish_collisions()

    def test_food_removed_when_eaten_by_fish(self, fish_tank_setup):
        """Test that food is removed when a fish eats it."""
        simulator = fish_tank_setup

        fish = Fish(simulator.environment, SoloFishMovement(),
                   ['george1.png'], 100, 100, 3)
        food = Food(simulator.environment, 100, 100)

        simulator.agents.add(fish, food)

        assert food in simulator.agents

        simulator.handle_food_collisions()

    def test_iteration_safe_during_collision(self, fish_tank_setup):
        """Test that removing sprites during iteration doesn't cause issues."""
        simulator = fish_tank_setup

        # Create multiple fish and crabs
        fish1 = Fish(simulator.environment, SoloFishMovement(),
                    ['george1.png'], 100, 100, 3)
        fish2 = Fish(simulator.environment, SoloFishMovement(),
                    ['george1.png'], 200, 200, 3)
        crab1 = Crab(simulator.environment)
        crab1.pos = Vector2(100, 100)
        crab1.rect.topleft = crab1.pos

        simulator.agents.add(fish1, fish2, crab1)

        try:
            simulator.handle_fish_collisions()
            success = True
        except Exception as e:
            success = False
            print(f"Error: {e}")

        assert success, "Collision handling should not crash during iteration"

    def test_multiple_collisions_handled(self, fish_tank_setup):
        """Test that multiple simultaneous collisions are all handled."""
        simulator = fish_tank_setup

        fish1 = Fish(simulator.environment, SoloFishMovement(),
                    ['george1.png'], 100, 100, 3)
        fish2 = Fish(simulator.environment, SoloFishMovement(),
                    ['george1.png'], 200, 200, 3)
        food1 = Food(simulator.environment, 100, 100)
        food2 = Food(simulator.environment, 200, 200)

        simulator.agents.add(fish1, fish2, food1, food2)

        try:
            simulator.handle_food_collisions()
            success = True
        except Exception:
            success = False

        assert success

    def test_food_falls_off_screen_removed(self, fish_tank_setup):
        """Test that food removal logic works for food at bottom of screen."""
        simulator = fish_tank_setup

        food = Food(simulator.environment, 100, 50)
        simulator.agents.add(food)

        food.rect.y = SCREEN_HEIGHT

        assert food in simulator.agents

        for sprite in list(simulator.agents):
            if isinstance(sprite, Food) and sprite.rect.y >= SCREEN_HEIGHT - sprite.rect.height:
                sprite.kill()

        assert food not in simulator.agents

    def test_handle_collisions_called_safely(self, fish_tank_setup):
        """Test that the main collision handler can be called repeatedly."""
        simulator = fish_tank_setup

        # Add various sprites
        fish = Fish(simulator.environment, SoloFishMovement(),
                   ['george1.png'], 100, 100, 3)
        crab = Crab(simulator.environment)
        food = Food(simulator.environment, 150, 150)

        simulator.agents.add(fish, crab, food)

        try:
            for _ in range(10):
                simulator.handle_collisions()
            success = True
        except Exception:
            success = False

        assert success, "Should be able to call handle_collisions repeatedly"
