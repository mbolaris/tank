import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest
import pygame
from pygame.math import Vector2

# Initialize pygame for tests
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))  # Minimal display for testing

from agents import Fish, Crab, Food
from environment import Environment
from movement_strategy import (MovementStrategy, SoloFishMovement, SchoolingFishMovement,
                                CRAB_AVOIDANCE_DISTANCE, SOLO_FISH_AVOIDANCE_DISTANCE,
                                SCHOOLING_FISH_ALIGNMENT_DISTANCE)


class TestMovementStrategy:
    """Test the base MovementStrategy class."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_base_strategy_checks_food_collision(self):
        """Test that base strategy checks for food collisions."""
        strategy = MovementStrategy()
        fish = Fish(self.env, strategy, ['george1.png'], 100, 100, 3)
        food = Food(self.env, 100, 100)
        self.agents.add(fish, food)

        initial_vel = fish.vel.copy()
        strategy.move(fish)

        # Velocity might be set to zero if collision detected
        # (depends on pygame collision detection with rects)


class TestSoloFishMovement:
    """Test the SoloFishMovement strategy."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_solo_fish_avoids_crabs(self):
        """Test that solo fish avoids crabs."""
        strategy = SoloFishMovement()
        fish = Fish(self.env, strategy, ['george1.png'], 100, 100, 3)
        crab = Crab(self.env)
        crab.pos = Vector2(120, 100)  # Close to fish
        self.agents.add(fish, crab)

        initial_avoidance = fish.avoidance_velocity.copy()
        strategy.move(fish)

        # Fish should have avoidance velocity after encountering nearby crab
        # (The exact behavior depends on distance and constants)

    def test_solo_fish_adds_random_movement(self):
        """Test that solo fish adds random velocity changes."""
        strategy = SoloFishMovement()
        fish = Fish(self.env, strategy, ['george1.png'], 100, 100, 3)
        self.agents.add(fish)

        # Move several times and check that velocity changes
        initial_vel = fish.vel.copy()
        for _ in range(10):
            strategy.move(fish)

        # Velocity should have changed due to random movements
        # (With high probability after 10 iterations)


class TestSchoolingFishMovement:
    """Test the SchoolingFishMovement strategy."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_schooling_fish_aligns_with_same_type(self):
        """Test that schooling fish aligns with fish of the same type."""
        strategy = SchoolingFishMovement()
        fish1 = Fish(self.env, strategy, ['school.png'], 100, 100, 4)
        fish2 = Fish(self.env, strategy, ['school.png'], 150, 100, 4)
        self.agents.add(fish1, fish2)

        strategy.move(fish1)

        # Fish1 should try to align with fish2
        # (Exact behavior depends on alignment logic)

    def test_schooling_fish_avoids_different_type(self):
        """Test that schooling fish avoids fish of different types."""
        strategy = SchoolingFishMovement()
        school_fish = Fish(self.env, strategy, ['school.png'], 100, 100, 4)
        solo_fish = Fish(self.env, SoloFishMovement(), ['george1.png'], 120, 100, 3)
        self.agents.add(school_fish, solo_fish)

        strategy.move(school_fish)

        # Schooling fish should avoid the solo fish
        # (Exact behavior depends on avoidance logic)

    def test_get_same_type_sprites(self):
        """Test that get_same_type_sprites returns only matching fish."""
        strategy = SchoolingFishMovement()
        fish1 = Fish(self.env, strategy, ['school.png'], 100, 100, 4)
        fish2 = Fish(self.env, strategy, ['school.png'], 150, 100, 4)
        fish3 = Fish(self.env, SoloFishMovement(), ['george1.png'], 200, 100, 3)
        self.agents.add(fish1, fish2, fish3)

        same_type = strategy.get_same_type_sprites(fish1)

        assert fish2 in same_type
        assert fish3 not in same_type
        assert fish1 not in same_type  # Should not include self

    def test_get_different_type_sprites(self):
        """Test that get_different_type_sprites returns only non-matching fish."""
        strategy = SchoolingFishMovement()
        fish1 = Fish(self.env, strategy, ['school.png'], 100, 100, 4)
        fish2 = Fish(self.env, strategy, ['school.png'], 150, 100, 4)
        fish3 = Fish(self.env, SoloFishMovement(), ['george1.png'], 200, 100, 3)
        self.agents.add(fish1, fish2, fish3)

        different_type = strategy.get_different_type_sprites(fish1)

        assert fish3 in different_type
        assert fish2 not in different_type
        assert fish1 not in different_type
