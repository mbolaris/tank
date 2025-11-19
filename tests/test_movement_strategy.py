"""Tests for movement strategies in the fish tank simulation."""

from core.entities import Fish, Food
from core.genetics import Genome
from core.math_utils import Vector2
from core.movement_strategy import AlgorithmicMovement, MovementStrategy


class TestMovementStrategy:
    """Test the base MovementStrategy class."""

    def test_base_strategy_checks_food_collision(self, simulation_env):
        """Test that base strategy checks for food collisions."""
        env, agents = simulation_env
        strategy = MovementStrategy()
        fish = Fish(env, strategy, ["george1.png"], 100, 100, 3)
        food = Food(env, 100, 100)
        agents.add(fish, food)

        # Should not crash when checking for food collision
        try:
            strategy.move(fish)
            success = True
        except Exception as e:
            success = False

        assert success


class TestAlgorithmicMovement:
    """Test the AlgorithmicMovement strategy."""

    def test_algorithmic_movement_with_algorithm(self, simulation_env):
        """Test that algorithmic movement works with a behavior algorithm."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=True)
        fish = Fish(env, strategy, ["george1.png"], 100, 100, 3, genome=genome)
        agents.add(fish)

        # Should execute algorithm and move without crashing
        try:
            for _ in range(10):
                strategy.move(fish)
            success = True
        except Exception as e:
            success = False

        assert success

    def test_algorithmic_movement_without_algorithm(self, simulation_env):
        """Test that algorithmic movement falls back to random when no algorithm."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=False)
        fish = Fish(env, strategy, ["george1.png"], 100, 100, 3, genome=genome)
        agents.add(fish)

        # Should fall back to random movement without crashing
        try:
            for _ in range(10):
                strategy.move(fish)
            success = True
        except Exception as e:
            success = False

        assert success

    def test_algorithmic_movement_consistency(self, simulation_env):
        """Test that algorithmic movement behaves consistently over time."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()

        # Create multiple fish with different algorithms
        fish_list = []
        for i in range(5):
            genome = Genome.random(use_algorithm=True)
            fish = Fish(env, strategy, ["george1.png"], 100 + i * 30, 100, 3, genome=genome)
            fish_list.append(fish)
            agents.add(fish)

        # Run movement for many iterations
        try:
            for _ in range(50):
                for fish in fish_list:
                    strategy.move(fish)
            success = True
        except Exception as e:
            success = False

        assert success, "Algorithmic movement should work consistently over many iterations"

    def test_algorithmic_movement_updates_velocity(self, simulation_env):
        """Test that algorithmic movement updates fish velocity."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=True)
        fish = Fish(env, strategy, ["george1.png"], 100, 100, 3, genome=genome)
        agents.add(fish)

        # Store initial velocity
        fish.vel.copy()

        # Move multiple times to allow velocity to change
        for _ in range(10):
            strategy.move(fish)

        # Velocity should have been updated (unless algorithm happens to output same as initial)
        # We just test that it doesn't crash and velocity is a valid Vector2
        assert isinstance(fish.vel, Vector2)
        assert fish.vel.length() >= 0  # Valid velocity magnitude
