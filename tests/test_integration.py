"""Integration tests for the full fish tank simulation."""

import pytest

from core.entities import Castle, Crab, Fish, Food


@pytest.mark.slow
class TestFullSimulation:
    """Integration tests that run the complete simulation."""

    def test_simulation_runs_without_crashing(self, simulation_engine):
        """Test that the simulation can run for multiple frames without errors."""
        simulator = simulation_engine

        # Setup the environment with all agents
        simulator.environment.agents = simulator.agents

        # Verify initial setup (fixture already called setup() which creates entities)
        assert (
            len([s for s in simulator.agents if isinstance(s, Fish)]) == 10
        )  # 10 algorithmic fish
        assert len([s for s in simulator.agents if isinstance(s, Crab)]) == 1
        # PNG plants removed - only fractal plants are used now
        assert len([s for s in simulator.agents if isinstance(s, Castle)]) == 1

        # Run simulation for 100 frames
        try:
            for frame in range(100):
                simulator.update()
            success = True
        except Exception as e:
            success = False
            print(f"Simulation crashed at frame {frame}: {e}")

        assert success, "Simulation should run for 100 frames without crashing"

    def test_simulation_with_food_drops(self, simulation_engine):
        """Test that the simulation handles food drops correctly."""
        simulator = simulation_engine
        simulator.environment.agents = simulator.agents

        initial_agent_count = len(simulator.agents)

        # Add some food
        for i in range(5):
            food = Food(simulator.environment, 100 + i * 50, 100)
            simulator.agents.add(food)

        assert len(simulator.agents) == initial_agent_count + 5

        # Run simulation - food should sink and might be eaten or fall off screen
        try:
            for _ in range(200):
                simulator.update()
        except Exception as e:
            pytest.fail(f"Simulation with food crashed: {type(e).__name__}: {e}")

    def test_simulation_handles_fish_crab_interactions(self, simulation_engine):
        """Test that fish-crab collision handling works over time."""
        simulator = simulation_engine
        simulator.environment.agents = simulator.agents

        # Create a simple scenario with one fish and one crab
        from core.movement_strategy import AlgorithmicMovement

        fish = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos.x = 500  # Far from fish initially
        crab.pos.y = 500

        simulator.agents.add(fish, crab)

        # Run simulation
        try:
            for _ in range(100):
                simulator.collision_system.update(0)
                for sprite in list(simulator.agents):
                    sprite.update(0)
        except Exception as e:
            pytest.fail(f"Fish-crab interactions failed: {type(e).__name__}: {e}")

    def test_simulation_state_consistency(self, simulation_engine):
        """Test that simulation maintains consistent state over time."""
        simulator = simulation_engine
        simulator.environment.agents = simulator.agents

        len([s for s in simulator.agents if not isinstance(s, Food)])

        # Run simulation
        for _ in range(50):
            simulator.update()

        # Castle and crabs should still be there (they don't move/die)
        # PNG plants removed - only fractal plants are used now
        castles = [s for s in simulator.agents if isinstance(s, Castle)]
        crabs = [s for s in simulator.agents if isinstance(s, Crab)]
        assert len(castles) == 1, "Castle should remain in the simulation"
        assert len(crabs) == 1, "Crab should remain in the simulation"

    def test_simulation_with_rapid_updates(self, simulation_engine):
        """Test simulation stability with rapid updates."""
        simulator = simulation_engine
        simulator.environment.agents = simulator.agents

        # Run many updates in quick succession
        try:
            for _ in range(500):
                simulator.update()
        except Exception as e:
            pytest.fail(f"Simulation failed during rapid updates: {type(e).__name__}: {e}")

    def test_bug_fixes_verified(self, simulation_engine):
        """Verify that our critical bug fixes are working."""
        simulator = simulation_engine
        simulator.environment.agents = simulator.agents

        from core.movement_strategy import AlgorithmicMovement

        # Test 1: Fish avoidance bug fix - fish should maintain avoidance when crab stays close
        fish = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos.x = 110  # Close to fish
        crab.pos.y = 100

        simulator.agents.add(fish, crab)

        # Call avoid method multiple times - avoidance should persist when crab stays close
        for _ in range(10):
            fish.avoid([crab], min_distance=50)

        # Avoidance should still be active (not reset to zero)
        # because crab is still close
        assert (
            fish.avoidance_velocity.length() > 0
        ), "Avoidance should persist when crab stays close"

        # Test 2: Safe iteration during collision - should not crash
        simulator.agents.empty()
        fish1 = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        fish2 = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 200, 200, 3)
        crab = Crab(simulator.environment)

        simulator.agents.add(fish1, fish2, crab)

        try:
            # This tests our fix for safe iteration when removing sprites
            for _ in range(20):
                simulator.collision_system.update(0)
        except Exception as e:
            pytest.fail(f"Collision handling failed during sprite removal: {type(e).__name__}: {e}")

        # Test 3: Zero-length vector safety - should not crash
        simulator.agents.empty()
        fish = Fish(simulator.environment, AlgorithmicMovement(), "george1.png", 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos = fish.pos  # Same position - zero-length vector!

        simulator.agents.add(fish, crab)

        try:
            # This tests our zero-length vector safety checks
            fish.avoid([crab], 50)
        except Exception as e:
            pytest.fail(f"Zero-length vector handling crashed: {type(e).__name__}: {e}")
