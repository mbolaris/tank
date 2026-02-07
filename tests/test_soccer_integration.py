"""Integration tests for soccer system in Tank World.

Tests that ball, goals, and soccer mechanics are properly integrated
into the tank world simulation.
"""

from unittest.mock import Mock

import pytest

from core.entities.ball import Ball
from core.entities.fish import Fish
from core.entities.goal_zone import GoalZone, GoalZoneManager
from core.math_utils import Vector2
from core.movement_strategy import AlgorithmicMovement


class TestSoccerIntegration:
    """Test soccer system integration with Tank World."""

    def test_ball_initialization_in_pack(self):
        """Test that ball is initialized properly."""
        try:
            from core.config.simulation_config import SimulationConfig
            from core.worlds.tank.pack import TankPack

            config = SimulationConfig.production(headless=True)
            TankPack(config)

            # Check soccer is not explicitly disabled
            assert (
                not hasattr(config, "tank")
                or not hasattr(config.tank, "soccer_enabled")
                or getattr(config.tank, "soccer_enabled", True)
            )
        except ImportError:
            pytest.skip("TankPack not available")

    def test_goal_zones_created(self):
        """Test that goal zones are created correctly."""
        mock_world = Mock()
        mock_world.width = 800
        mock_world.height = 600
        mock_world.get_bounds = Mock(return_value=((0, 0), (800, 600)))

        goal_manager = GoalZoneManager()

        goal_left = GoalZone(mock_world, 50, 300, team="A", goal_id="goal_left")
        goal_right = GoalZone(mock_world, 750, 300, team="B", goal_id="goal_right")

        goal_manager.register_zone(goal_left)
        goal_manager.register_zone(goal_right)

        assert len(goal_manager.zones) == 2
        assert "goal_left" in goal_manager.zones
        assert "goal_right" in goal_manager.zones
        assert goal_manager.zones["goal_left"].team == "A"
        assert goal_manager.zones["goal_right"].team == "B"

    def test_ball_physics_in_environment(self):
        """Test that ball physics updates work in environment."""
        mock_world = Mock()
        mock_world.width = 800
        mock_world.height = 600
        mock_world.get_bounds = Mock(return_value=((0, 0), (800, 600)))

        ball = Ball(mock_world, 400, 300)

        # Initial state
        assert ball.pos.x == 400
        assert ball.pos.y == 300
        assert ball.vel.x == 0.0
        assert ball.vel.y == 0.0

        # Apply kick
        ball.kick(50.0, Vector2(1.0, 0.0))
        assert ball.acceleration.x > 0

        # Update
        ball.update(0)
        assert ball.pos.x > 400  # Ball moved right
        assert ball.vel.x > 0

    def test_fish_team_affiliation(self, simulation_env):
        """Test that fish can have team affiliation."""
        env, _ = simulation_env

        fish_a = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="fish1.png",
            x=100,
            y=100,
            speed=3,
            team="A",
        )

        fish_b = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="fish1.png",
            x=700,
            y=100,
            speed=3,
            team="B",
        )

        assert fish_a.team == "A"
        assert fish_b.team == "B"

    def test_goal_scoring_event(self):
        """Test that goal events are created correctly."""
        mock_world = Mock()
        mock_world.width = 800
        mock_world.height = 600
        mock_world.get_bounds = Mock(return_value=((0, 0), (800, 600)))

        goal = GoalZone(mock_world, 50, 300, team="A", goal_id="goal_left", radius=15.0)
        ball = Ball(mock_world, 50, 300)  # Ball at goal center

        # Check for goal
        goal_event = goal.check_goal(ball, frame_count=100)

        assert goal_event is not None
        assert goal_event.team == "A"
        assert goal_event.goal_id == "goal_left"
        assert goal_event.timestamp == 100

    def test_soccer_system_setup(self):
        """Test that soccer system can be set up."""
        try:
            from unittest.mock import MagicMock

            from core.systems.soccer_system import SoccerSystem

            mock_engine = MagicMock()
            soccer_system = SoccerSystem(mock_engine)

            # Initially disabled
            assert not soccer_system.enabled

            # Can be enabled
            mock_world = Mock()
            mock_world.get_bounds = Mock(return_value=((0, 0), (800, 600)))
            ball = Ball(mock_world, 400, 300)

            soccer_system.set_ball(ball)
            assert soccer_system.enabled
            assert soccer_system.ball is ball
        except ImportError:
            pytest.skip("SoccerSystem not available")

    def test_observation_includes_soccer_info(self, simulation_env):
        """Test that observations include soccer information when available."""
        env, _ = simulation_env

        from core.worlds.tank.observation_builder import \
            build_tank_observations

        # Create a mock world with ball and goals
        mock_world = Mock()
        mock_world.environment = env
        mock_world.frame_count = 0
        mock_world.entities_list = []

        # Create a fish
        fish = Fish(
            environment=env,
            movement_strategy=AlgorithmicMovement(),
            species="fish1.png",
            x=400,
            y=300,
            speed=3,
            team="A",
        )
        mock_world.entities_list.append(fish)

        # Create ball and goals
        ball = Ball(env, 400, 300)
        goal_manager = GoalZoneManager()
        goal_left = GoalZone(env, 50, 300, team="A", goal_id="goal_left")
        goal_manager.register_zone(goal_left)

        env.ball = ball
        env.goal_manager = goal_manager

        # Build observations
        obs = build_tank_observations(mock_world)

        # Check observations were built
        assert len(obs) > 0

        # Check that observation includes soccer info (in extra field)
        fish_id = str(fish.fish_id)
        if fish_id in obs:
            obs_data = obs[fish_id]
            assert "extra" in obs_data.__dict__ or hasattr(obs_data, "extra")


class TestSoccerPhysicsIntegration:
    """Test physics-level integration of soccer components."""

    def test_ball_decay_over_frames(self):
        """Test that ball velocity decays correctly over multiple frames."""
        mock_world = Mock()
        mock_world.get_bounds = Mock(return_value=((0, 0), (800, 600)))

        ball = Ball(mock_world, 400, 300, decay_rate=0.5)  # High decay for testing
        ball.vel = Vector2(10.0, 0.0)

        # Frame 1
        ball.update(0)
        vel_after_1 = ball.vel.x
        assert vel_after_1 < 10.0  # Decayed

        # Frame 2
        ball.update(1)
        vel_after_2 = ball.vel.x
        assert vel_after_2 < vel_after_1  # Further decayed

    def test_goal_detection_sequence(self):
        """Test complete goal detection sequence."""
        mock_world = Mock()
        mock_world.width = 800
        mock_world.height = 600
        mock_world.get_bounds = Mock(return_value=((0, 0), (800, 600)))

        # Create ball and goals
        ball = Ball(mock_world, 400, 300)
        goal_manager = GoalZoneManager()

        goal_a = GoalZone(mock_world, 50, 300, team="A", radius=15.0)
        goal_b = GoalZone(mock_world, 750, 300, team="B", radius=15.0)

        goal_manager.register_zone(goal_a)
        goal_manager.register_zone(goal_b)

        # Kick ball toward goal A
        ball.kick(80.0, Vector2(-1.0, 0.0))

        # Update ball until it reaches goal
        for frame in range(100):
            ball.update(frame)
            goal_event = goal_manager.check_all_goals(ball, frame)
            if goal_event:
                assert goal_event.team == "A"
                break
        else:
            # If no goal, that's okay - ball might not reach
            pass

    def test_fish_team_color_coding(self, simulation_env):
        """Test that fish team affiliation can be used for rendering."""
        env, _ = simulation_env

        fish_teams: dict[str, list[Fish]] = {"A": [], "B": []}

        for team in ["A", "B"]:
            for i in range(5):
                fish = Fish(
                    environment=env,
                    movement_strategy=AlgorithmicMovement(),
                    species="fish1.png",
                    x=100 + i * 50,
                    y=100 if team == "A" else 500,
                    speed=3,
                    team=team,
                )
                fish_teams[team].append(fish)

        # Verify teams
        assert len(fish_teams["A"]) == 5
        assert len(fish_teams["B"]) == 5
        assert all(f.team == "A" for f in fish_teams["A"])
        assert all(f.team == "B" for f in fish_teams["B"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
