"""Tests for agent behaviors in the fish tank simulation."""

from core.constants import FOOD_SINK_ACCELERATION
from core.entities import Agent, Castle, Crab, Fish, Food, Plant
from core.math_utils import Vector2
from core.movement_strategy import AlgorithmicMovement


class TestAgent:
    """Test the Agent base class."""

    def test_agent_initialization(self, simulation_env):
        """Test that an agent initializes with correct properties."""
        env, _ = simulation_env
        agent = Agent(env, ["george1.png"], 100, 200, 3)
        assert agent.speed == 3
        assert agent.pos == Vector2(100, 200)
        assert agent.vel.length() == 3
        assert agent.environment == env

    def test_agent_avoid_single_sprite(self, simulation_env):
        """Test that avoidance works with a single nearby sprite."""
        env, _ = simulation_env
        agent1 = Agent(env, ["george1.png"], 100, 100, 3)
        agent2 = Agent(env, ["crab1.png"], 110, 100, 2)

        initial_avoidance = agent1.avoidance_velocity.copy()
        agent1.avoid([agent2], min_distance=50)

        # Avoidance velocity should have changed
        assert agent1.avoidance_velocity != initial_avoidance

    def test_agent_avoid_resets_when_far(self, simulation_env):
        """Test that avoidance resets when all sprites are far away."""
        env, _ = simulation_env
        agent1 = Agent(env, ["george1.png"], 100, 100, 3)
        agent2 = Agent(env, ["crab1.png"], 500, 500, 2)

        # Set some initial avoidance
        agent1.avoidance_velocity = Vector2(5, 5)
        agent1.avoid([agent2], min_distance=50)

        # Avoidance should be reset since agent2 is far away
        assert agent1.avoidance_velocity == Vector2(0, 0)

    def test_agent_avoid_multiple_close_sprites(self, simulation_env):
        """Test that avoidance accumulates for multiple close sprites."""
        env, _ = simulation_env
        agent1 = Agent(env, ["george1.png"], 100, 100, 3)
        agent2 = Agent(env, ["crab1.png"], 110, 100, 2)
        agent3 = Agent(env, ["crab2.png"], 100, 110, 2)

        agent1.avoid([agent2, agent3], min_distance=50)

        # Avoidance velocity should be non-zero
        assert agent1.avoidance_velocity.length() > 0

    def test_agent_avoid_zero_distance_safe(self, simulation_env):
        """Test that avoidance handles zero-length vectors safely."""
        env, _ = simulation_env
        agent1 = Agent(env, ["george1.png"], 100, 100, 3)
        agent2 = Agent(env, ["crab1.png"], 100, 100, 2)  # Same position

        # Should not crash (this was a bug we fixed)
        try:
            agent1.avoid([agent2], min_distance=50)
            success = True
        except Exception:
            success = False

        assert success, "Avoidance should handle zero-length vectors safely"

    def test_agent_update_position(self, simulation_env):
        """Test that agent position updates correctly."""
        env, _ = simulation_env
        agent = Agent(env, ["george1.png"], 100, 100, 3)
        initial_pos = agent.pos.copy()

        agent.update_position()

        # Position should have changed
        assert agent.pos != initial_pos

    def test_agent_screen_edge_bounce(self, simulation_env):
        """Test that agents bounce off screen edges."""
        env, _ = simulation_env
        agent = Agent(env, ["george1.png"], -10, 100, 3)
        initial_vel_x = agent.vel.x

        agent.handle_screen_edges()

        # Velocity should be positive (bouncing right) when hitting left edge
        assert agent.vel.x == abs(initial_vel_x)

    def test_agent_align_near(self, simulation_env):
        """Test that agents align with nearby sprites."""
        env, _ = simulation_env
        agent1 = Agent(env, ["george1.png"], 100, 100, 3)
        agent2 = Agent(env, ["george2.png"], 120, 100, 3)

        agent1.vel.copy()
        agent1.align_near([agent2], min_distance=50)

        # Velocity should have been adjusted
        # (The exact behavior depends on alignment logic)


class TestFish:
    """Test the Fish class."""

    def test_fish_initialization(self, simulation_env):
        """Test that fish initializes correctly."""
        env, _ = simulation_env
        strategy = AlgorithmicMovement()
        # Create a genome with size_modifier=1.0 for deterministic testing
        from core.genetics import Genome

        genome = Genome(size_modifier=1.0)
        fish = Fish(env, strategy, ["george1.png"], 100, 100, 3, genome=genome)

        # Fish start as babies with size 0.5 (when genetic size_modifier is 1.0)
        assert fish.size == 0.5
        assert fish.movement_strategy == strategy

    def test_fish_grows_when_eating(self, simulation_env):
        """Test that fish gains energy when it eats food."""
        env, _ = simulation_env
        strategy = AlgorithmicMovement()
        fish = Fish(env, strategy, ["george1.png"], 100, 100, 3)
        food = Food(env, 110, 110)

        initial_energy = fish.energy
        fish.eat(food)

        # Fish should gain energy from eating (size is based on age, not eating)
        assert fish.energy > initial_energy

    def test_fish_movement_strategy_called(self, simulation_env):
        """Test that fish calls its movement strategy on update."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        fish = Fish(env, strategy, ["george1.png"], 100, 100, 3)
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

    def test_crab_initialization(self, simulation_env):
        """Test that crab initializes correctly."""
        env, _ = simulation_env
        crab = Crab(env)
        # Crab speed is 1.5 * genome.speed_modifier (genome is random, so speed varies)
        # Speed should be around 1.5 with some genetic variation
        assert 0.5 < crab.speed < 3.0

    def test_crab_stays_on_bottom(self, simulation_env):
        """Test that crab's vertical velocity is always zero."""
        env, agents = simulation_env
        crab = Crab(env)
        agents.add(crab)
        crab.vel.y = 5  # Try to move vertically

        crab.update(0)

        # Y velocity should be reset to 0
        assert crab.vel.y == 0


class TestFood:
    """Test the Food class."""

    def test_food_initialization(self, simulation_env):
        """Test that food initializes correctly."""
        env, _ = simulation_env
        food = Food(env, 100, 50)
        assert food.pos == Vector2(100, 50)
        assert food.speed == 0

    def test_food_sinks(self, simulation_env):
        """Test that food sinks over time."""
        env, _ = simulation_env
        food = Food(env, 100, 50, food_type="energy")
        initial_vel_y = food.vel.y

        food.sink()

        assert food.vel.y == initial_vel_y + FOOD_SINK_ACCELERATION

    def test_food_gets_eaten(self, simulation_env):
        """Test that food notifies source plant when eaten."""
        env, agents = simulation_env
        from core.entities import Plant

        plant = Plant(env, 1)
        plant.current_food_count = 5
        food = Food(env, 100, 50, source_plant=plant)
        agents.add(food)

        assert food in agents
        initial_count = plant.current_food_count
        food.get_eaten()
        # Food removal from agents is handled by collision detection, not by get_eaten()
        # get_eaten() only notifies the source plant
        assert plant.current_food_count == initial_count - 1


class TestPlant:
    """Test the Plant class."""

    def test_plant_initialization(self, simulation_env):
        """Test that plant initializes correctly."""
        env, _ = simulation_env
        plant = Plant(env, 1)
        assert plant.speed == 0

    def test_plant_does_not_move(self, simulation_env):
        """Test that plant stays in place."""
        env, _ = simulation_env
        plant = Plant(env, 1)
        initial_pos = plant.pos.copy()

        plant.update_position()

        assert plant.pos == initial_pos


class TestCastle:
    """Test the Castle class."""

    def test_castle_initialization(self, simulation_env):
        """Test that castle initializes correctly."""
        env, _ = simulation_env
        castle = Castle(env)
        assert castle.speed == 0
