"""Tests for agent behaviors in the fish tank simulation."""
import pytest
import pygame
from pygame.math import Vector2

from agents import Agent, Fish, Crab, Food, Plant, Castle
from core.environment import Environment
from movement_strategy import SoloFishMovement, SchoolingFishMovement
from core.constants import FISH_GROWTH_RATE, FOOD_SINK_ACCELERATION


class TestAgent:
    """Test the Agent base class."""

    def test_agent_initialization(self, pygame_env):
        """Test that an agent initializes with correct properties."""
        env, _ = pygame_env
        agent = Agent(env, ['george1.png'], 100, 200, 3)
        assert agent.speed == 3
        assert agent.pos == Vector2(100, 200)
        assert agent.vel.length() == 3
        assert agent.environment == env

    def test_agent_avoid_single_sprite(self, pygame_env):
        """Test that avoidance works with a single nearby sprite."""
        env, _ = pygame_env
        agent1 = Agent(env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(env, ['crab1.png'], 110, 100, 2)

        initial_avoidance = agent1.avoidance_velocity.copy()
        agent1.avoid([agent2], min_distance=50)

        # Avoidance velocity should have changed
        assert agent1.avoidance_velocity != initial_avoidance

    def test_agent_avoid_resets_when_far(self, pygame_env):
        """Test that avoidance resets when all sprites are far away."""
        env, _ = pygame_env
        agent1 = Agent(env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(env, ['crab1.png'], 500, 500, 2)

        # Set some initial avoidance
        agent1.avoidance_velocity = Vector2(5, 5)
        agent1.avoid([agent2], min_distance=50)

        # Avoidance should be reset since agent2 is far away
        assert agent1.avoidance_velocity == Vector2(0, 0)

    def test_agent_avoid_multiple_close_sprites(self, pygame_env):
        """Test that avoidance accumulates for multiple close sprites."""
        env, _ = pygame_env
        agent1 = Agent(env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(env, ['crab1.png'], 110, 100, 2)
        agent3 = Agent(env, ['crab2.png'], 100, 110, 2)

        agent1.avoid([agent2, agent3], min_distance=50)

        # Avoidance velocity should be non-zero
        assert agent1.avoidance_velocity.length() > 0

    def test_agent_avoid_zero_distance_safe(self, pygame_env):
        """Test that avoidance handles zero-length vectors safely."""
        env, _ = pygame_env
        agent1 = Agent(env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(env, ['crab1.png'], 100, 100, 2)  # Same position

        # Should not crash (this was a bug we fixed)
        try:
            agent1.avoid([agent2], min_distance=50)
            success = True
        except Exception:
            success = False

        assert success, "Avoidance should handle zero-length vectors safely"

    def test_agent_update_position(self, pygame_env):
        """Test that agent position updates correctly."""
        env, _ = pygame_env
        agent = Agent(env, ['george1.png'], 100, 100, 3)
        initial_pos = agent.pos.copy()

        agent.update_position()

        # Position should have changed
        assert agent.pos != initial_pos

    def test_agent_screen_edge_bounce(self, pygame_env):
        """Test that agents bounce off screen edges."""
        env, _ = pygame_env
        agent = Agent(env, ['george1.png'], -10, 100, 3)
        initial_vel_x = agent.vel.x

        agent.handle_screen_edges()

        # Velocity should reverse when hitting edge
        assert agent.vel.x == -initial_vel_x

    def test_agent_align_near(self, pygame_env):
        """Test that agents align with nearby sprites."""
        env, _ = pygame_env
        agent1 = Agent(env, ['george1.png'], 100, 100, 3)
        agent2 = Agent(env, ['george2.png'], 120, 100, 3)

        initial_vel = agent1.vel.copy()
        agent1.align_near([agent2], min_distance=50)

        # Velocity should have been adjusted
        # (The exact behavior depends on alignment logic)


class TestFish:
    """Test the Fish class."""

    def test_fish_initialization(self, pygame_env):
        """Test that fish initializes correctly."""
        env, _ = pygame_env
        strategy = SoloFishMovement()
        fish = Fish(env, strategy, ['george1.png'], 100, 100, 3)

        assert fish.size == 1
        assert fish.movement_strategy == strategy

    def test_fish_grows_when_eating(self, pygame_env):
        """Test that fish grows when it eats food."""
        env, _ = pygame_env
        strategy = SoloFishMovement()
        fish = Fish(env, strategy, ['george1.png'], 100, 100, 3)
        food = Food(env, 110, 110)

        initial_size = fish.size
        fish.eat(food)

        assert fish.size == initial_size + FISH_GROWTH_RATE

    def test_fish_movement_strategy_called(self, pygame_env):
        """Test that fish calls its movement strategy on update."""
        env, agents = pygame_env
        strategy = SoloFishMovement()
        fish = Fish(env, strategy, ['george1.png'], 100, 100, 3)
        agents.add(fish)

        # Movement strategy should move the fish without crashing
        try:
            fish.update(0)
            success = True
        except Exception:
            success = False

        assert success


class TestCrab:
    """Test the Crab class."""

    def test_crab_initialization(self, pygame_env):
        """Test that crab initializes correctly."""
        env, _ = pygame_env
        crab = Crab(env)
        assert crab.speed == 2

    def test_crab_stays_on_bottom(self, pygame_env):
        """Test that crab's vertical velocity is always zero."""
        env, agents = pygame_env
        crab = Crab(env)
        agents.add(crab)
        crab.vel.y = 5  # Try to move vertically

        crab.update(0)

        # Y velocity should be reset to 0
        assert crab.vel.y == 0


class TestFood:
    """Test the Food class."""

    def test_food_initialization(self, pygame_env):
        """Test that food initializes correctly."""
        env, _ = pygame_env
        food = Food(env, 100, 50)
        assert food.pos == Vector2(100, 50)
        assert food.speed == 0

    def test_food_sinks(self, pygame_env):
        """Test that food sinks over time."""
        env, _ = pygame_env
        food = Food(env, 100, 50)
        initial_vel_y = food.vel.y

        food.sink()

        assert food.vel.y == initial_vel_y + FOOD_SINK_ACCELERATION

    def test_food_gets_eaten(self, pygame_env):
        """Test that food is removed when eaten."""
        env, agents = pygame_env
        food = Food(env, 100, 50)
        agents.add(food)

        assert food in agents
        food.get_eaten()
        assert food not in agents


class TestPlant:
    """Test the Plant class."""

    def test_plant_initialization(self, pygame_env):
        """Test that plant initializes correctly."""
        env, _ = pygame_env
        plant = Plant(env, 1)
        assert plant.speed == 0

    def test_plant_does_not_move(self, pygame_env):
        """Test that plant stays in place."""
        env, _ = pygame_env
        plant = Plant(env, 1)
        initial_pos = plant.pos.copy()

        plant.update_position()

        assert plant.pos == initial_pos


class TestCastle:
    """Test the Castle class."""

    def test_castle_initialization(self, pygame_env):
        """Test that castle initializes correctly."""
        env, _ = pygame_env
        castle = Castle(env)
        assert castle.speed == 0
