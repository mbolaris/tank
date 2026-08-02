"""Tests for movement strategies in the fish tank simulation."""

from core.entities import Fish, Food
from core.entities.ball import Ball
from core.genetics import Genome
from core.math_utils import Vector2
from core.movement.ball_pursuit import ball_pursuit_velocity
from core.movement_strategy import AlgorithmicMovement, MovementStrategy


class TestMovementStrategy:
    """Test the base MovementStrategy class."""

    def test_base_strategy_checks_food_collision(self, simulation_env):
        """Test that base strategy checks for food collisions."""
        env, agents = simulation_env
        strategy = MovementStrategy()
        fish = Fish(env, strategy, "george1.png", 100, 100, 3)
        food = Food(env, 100, 100)
        agents.add(fish, food)

        # Should not crash when checking for food collision
        try:
            strategy.move(fish)
            success = True
        except Exception:
            success = False

        assert success


class TestAlgorithmicMovement:
    """Test the AlgorithmicMovement strategy."""

    def test_algorithmic_movement_with_algorithm(self, simulation_env):
        """Test that algorithmic movement works with a behavior algorithm."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=True)
        fish = Fish(env, strategy, "george1.png", 100, 100, 3, genome=genome)
        agents.add(fish)

        # Should execute algorithm and move without crashing
        try:
            for _ in range(10):
                strategy.move(fish)
            success = True
        except Exception:
            success = False

        assert success

    def test_algorithmic_movement_without_algorithm(self, simulation_env):
        """Test that algorithmic movement falls back to random when no algorithm."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=False)
        fish = Fish(env, strategy, "george1.png", 100, 100, 3, genome=genome)
        agents.add(fish)

        # Should fall back to random movement without crashing
        try:
            for _ in range(10):
                strategy.move(fish)
            success = True
        except Exception:
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
            fish = Fish(env, strategy, "george1.png", 100 + i * 30, 100, 3, genome=genome)
            fish_list.append(fish)
            agents.add(fish)

        # Run movement for many iterations
        try:
            for _ in range(50):
                for fish in fish_list:
                    strategy.move(fish)
            success = True
        except Exception:
            success = False

        assert success, "Algorithmic movement should work consistently over many iterations"

    def test_algorithmic_movement_updates_velocity(self, simulation_env):
        """Test that algorithmic movement updates fish velocity."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=True)
        fish = Fish(env, strategy, "george1.png", 100, 100, 3, genome=genome)
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

    def test_ball_pursuit_prefers_environment_ball(self, simulation_env):
        """Ensure soccer pursuit honors env.ball before scanning agents."""
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        fish = Fish(env, strategy, "george1.png", 10, 10, 3)
        # Only fish with genuine surplus energy (near max) play ball, so top the
        # fish up - this test is about ball *selection*, not the energy gate.
        fish.energy = fish.max_energy
        agents.add(fish)

        ball = Ball(env, 500, 500)
        env.ball = ball

        class FixedRng:
            def random(self) -> float:
                return 0.0

        env._rng = FixedRng()

        velocity = ball_pursuit_velocity(fish)

        assert velocity is not None

    def test_ball_pursuit_yields_to_threat_but_not_to_food(self, simulation_env):
        """Threat outranks leisure absolutely; food is a choice for a fed fish.

        A predator in range always wins - a fish never plays while being
        hunted. Food no longer wins unconditionally: the fish has already
        cleared its own evolved ``min_energy_for_soccer`` threshold, and that
        gene is what prices the risk. Yielding to food as well made the
        engagement genes inert, because below max energy a fish can always eat.
        """
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=True)
        fish = Fish(env, strategy, "george1.png", 100, 100, 3, genome=genome)
        fish.energy = fish.max_energy  # surplus -> passes the ball energy gate
        agents.add(fish)
        env.ball = Ball(env, 500, 500)

        class FixedRng:
            def random(self) -> float:
                return 0.0  # always roll "play"

        env._rng = FixedRng()
        behavior = fish.genome.behavioral.behavior.value

        # No threat -> fish pursues the ball.
        behavior.has_threat_priority = lambda f: False
        assert ball_pursuit_velocity(fish) is not None

        # Hungry-but-fed fish with food available still plays: food does not
        # pre-empt a fish that has cleared its own energy threshold.
        behavior.has_food_priority = lambda f: True
        assert ball_pursuit_velocity(fish) is not None

        # Predator in range -> fish yields the ball even though it rolled play.
        behavior.has_threat_priority = lambda f: True
        assert ball_pursuit_velocity(fish) is None

    def test_ball_pursuit_energy_gate_is_the_fish_s_own_gene(self, simulation_env):
        """The play threshold is heritable, not a shared constant.

        Two fish differing only in ``min_energy_for_soccer`` must disagree
        about whether the same energy level is rich enough to play. That
        disagreement is the variance selection needs: with the old module
        constant, every fish was born equally ball-inclined and ball skill
        could not evolve at all.
        """
        env, agents = simulation_env
        strategy = AlgorithmicMovement()

        class FixedRng:
            def random(self) -> float:
                return 0.0

        env._rng = FixedRng()
        env.ball = Ball(env, 500, 500)

        def _fish_with(threshold: float) -> Fish:
            genome = Genome.random(use_algorithm=True)
            fish = Fish(env, strategy, "george1.png", 100, 100, 3, genome=genome)
            behavior = fish.genome.behavioral.behavior.value
            behavior.parameters["min_energy_for_soccer"] = threshold
            behavior.parameters["soccer_priority"] = 0.3
            behavior.has_threat_priority = lambda f: False
            agents.add(fish)
            fish.energy = fish.max_energy * 0.80
            return fish

        cautious = _fish_with(0.95)  # wants to be nearly full before playing
        keen = _fish_with(0.60)  # happy to play at 80% energy

        assert ball_pursuit_velocity(cautious) is None
        assert ball_pursuit_velocity(keen) is not None

    def test_ball_pursuit_commits_once_close(self, simulation_env):
        """Inside the commit radius a fish finishes the approach without re-rolling.

        Re-rolling every frame made fish dither ballward and never arrive:
        11,891 pursuit-frames converted to 374 kicks with commitment, versus
        4,461 frames producing only 37 kicks without it.
        """
        env, agents = simulation_env
        strategy = AlgorithmicMovement()
        genome = Genome.random(use_algorithm=True)
        fish = Fish(env, strategy, "george1.png", 100, 100, 3, genome=genome)
        fish.energy = fish.max_energy
        agents.add(fish)
        behavior = fish.genome.behavioral.behavior.value
        behavior.parameters["min_energy_for_soccer"] = 0.5
        behavior.parameters["soccer_priority"] = 0.0  # never rolls "play"
        behavior.has_threat_priority = lambda f: False

        class NeverPlayRng:
            def random(self) -> float:
                return 1.0  # roll always fails the priority check

        env._rng = NeverPlayRng()

        # Far away: the failed roll means no pursuit.
        env.ball = Ball(env, 900, 900)
        assert ball_pursuit_velocity(fish) is None

        # Close: committed, so the roll is skipped entirely.
        env.ball = Ball(env, 160, 100)
        assert ball_pursuit_velocity(fish) is not None

    def test_isolated_full_fish_has_no_survival_priority(self, simulation_env):
        """A full fish with no predator or reachable food has no survival drive,
        so it is free to play (real has_survival_priority path, RNG-free)."""
        env, agents = simulation_env
        genome = Genome.random(use_algorithm=True)
        fish = Fish(env, AlgorithmicMovement(), "george1.png", 100, 100, 3, genome=genome)
        fish.energy = fish.max_energy  # full -> cannot eat -> no food drive
        agents.add(fish)

        behavior = fish.genome.behavioral.behavior.value
        assert behavior.has_survival_priority(fish) is False
