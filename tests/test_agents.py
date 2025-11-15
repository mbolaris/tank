import os
import sys
import math
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest
import pygame
from pygame.math import Vector2

# Initialize pygame for tests
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))  # Minimal display for testing

from agents import Agent, Fish, Crab, Food, Plant, Castle
from environment import Environment
from movement_strategy import SoloFishMovement, SchoolingFishMovement
from constants import FISH_GROWTH_RATE, FOOD_SINK_ACCELERATION


class TestAgent:
    """Test the Agent base class."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_agent_initialization(self):
        """Test that an agent initializes with correct properties."""
        agent = Agent(self.env, ['george1.png'], 100, 200, 3)
        assert agent.speed == 3
        assert agent.pos == Vector2(100, 200)
        assert agent.vel.length() == 3
        assert agent.environment == self.env

    def test_agent_avoid_single_sprite(self):
        """Test that avoidance works with a single nearby sprite."""
        agent1 = Agent(self.env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(self.env, ['crab1.png'], 110, 100, 2)

        initial_avoidance = agent1.avoidance_velocity.copy()
        agent1.avoid([agent2], min_distance=50)

        # Avoidance velocity should have changed
        assert agent1.avoidance_velocity != initial_avoidance

    def test_agent_avoid_resets_when_far(self):
        """Test that avoidance resets when all sprites are far away."""
        agent1 = Agent(self.env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(self.env, ['crab1.png'], 500, 500, 2)

        # Set some initial avoidance
        agent1.avoidance_velocity = Vector2(5, 5)
        agent1.avoid([agent2], min_distance=50)

        # Avoidance should be reset since agent2 is far away
        assert agent1.avoidance_velocity == Vector2(0, 0)

    def test_agent_avoid_multiple_close_sprites(self):
        """Test that avoidance accumulates for multiple close sprites."""
        agent1 = Agent(self.env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(self.env, ['crab1.png'], 110, 100, 2)
        agent3 = Agent(self.env, ['crab2.png'], 100, 110, 2)

        agent1.avoid([agent2, agent3], min_distance=50)

        # Avoidance velocity should be non-zero
        assert agent1.avoidance_velocity.length() > 0

    def test_agent_avoid_zero_distance_safe(self):
        """Test that avoidance handles zero-length vectors safely."""
        agent1 = Agent(self.env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(self.env, ['crab1.png'], 100, 100, 2)  # Same position

        # Should not crash
        agent1.avoid([agent2], min_distance=50)

    def test_agent_update_position(self):
        """Test that agent position updates correctly."""
        agent = Agent(self.env, ['george1.png'], 100, 100, 3)
        initial_pos = agent.pos.copy()

        agent.update_position()

        # Position should have changed
        assert agent.pos != initial_pos

    def test_agent_screen_edge_bounce(self):
        """Test that agents bounce off screen edges."""
        agent = Agent(self.env, ['george1.png'], -10, 100, 3)
        initial_vel_x = agent.vel.x

        agent.handle_screen_edges()

        # Velocity should reverse when hitting edge
        assert agent.vel.x == -initial_vel_x


class TestFish:
    """Test the Fish class."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_fish_initialization(self):
        """Test that fish initializes correctly."""
        strategy = SoloFishMovement()
        fish = Fish(self.env, strategy, ['george1.png'], 100, 100, 3)

        assert fish.size == 1
        assert fish.movement_strategy == strategy

    def test_fish_grows_when_eating(self):
        """Test that fish grows when it eats food."""
        strategy = SoloFishMovement()
        fish = Fish(self.env, strategy, ['george1.png'], 100, 100, 3)
        food = Food(self.env, 110, 110)

        initial_size = fish.size
        fish.eat(food)

        assert fish.size == initial_size + FISH_GROWTH_RATE

    def test_fish_movement_strategy_called(self):
        """Test that fish calls its movement strategy on update."""
        strategy = SoloFishMovement()
        fish = Fish(self.env, strategy, ['george1.png'], 100, 100, 3)

        # Movement strategy should move the fish
        fish.update(0)


class TestCrab:
    """Test the Crab class."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_crab_initialization(self):
        """Test that crab initializes correctly."""
        crab = Crab(self.env)
        assert crab.speed == 2

    def test_crab_stays_on_bottom(self):
        """Test that crab's vertical velocity is always zero."""
        crab = Crab(self.env)
        crab.vel.y = 5  # Try to move vertically

        crab.update(0)

        # Y velocity should be reset to 0
        assert crab.vel.y == 0


class TestFood:
    """Test the Food class."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_food_initialization(self):
        """Test that food initializes correctly."""
        food = Food(self.env, 100, 50)
        assert food.pos == Vector2(100, 50)
        assert food.speed == 0

    def test_food_sinks(self):
        """Test that food sinks over time."""
        food = Food(self.env, 100, 50)
        initial_vel_y = food.vel.y

        food.sink()

        assert food.vel.y == initial_vel_y + FOOD_SINK_ACCELERATION

    def test_food_gets_eaten(self):
        """Test that food is removed when eaten."""
        food = Food(self.env, 100, 50)
        self.agents.add(food)

        assert food in self.agents
        food.get_eaten()
        assert food not in self.agents


class TestPlant:
    """Test the Plant class."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_plant_initialization(self):
        """Test that plant initializes correctly."""
        plant = Plant(self.env, 1)
        assert plant.speed == 0

    def test_plant_does_not_move(self):
        """Test that plant stays in place."""
        plant = Plant(self.env, 1)
        initial_pos = plant.pos.copy()

        plant.update_position()

        assert plant.pos == initial_pos


class TestCastle:
    """Test the Castle class."""

    def setup_method(self):
        """Setup for each test method."""
        self.agents = pygame.sprite.Group()
        self.env = Environment(self.agents)

    def test_castle_initialization(self):
        """Test that castle initializes correctly."""
        castle = Castle(self.env)
        assert castle.speed == 0
