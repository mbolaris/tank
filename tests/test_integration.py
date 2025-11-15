"""Integration tests for the full fish tank simulation."""
import pytest
import pygame

from fishtank import FishTankSimulator
from agents import Fish, Crab, Food, Plant, Castle
from constants import NUM_SCHOOLING_FISH


class TestFullSimulation:
    """Integration tests that run the complete simulation."""

    def test_simulation_runs_without_crashing(self, fish_tank_setup):
        """Test that the simulation can run for multiple frames without errors."""
        simulator = fish_tank_setup

        # Setup the environment with all agents
        simulator.environment.agents = simulator.agents
        simulator.create_initial_agents()

        # Verify initial setup
        assert len([s for s in simulator.agents if isinstance(s, Fish)]) == NUM_SCHOOLING_FISH + 1  # +1 for solo fish
        assert len([s for s in simulator.agents if isinstance(s, Crab)]) == 1
        assert len([s for s in simulator.agents if isinstance(s, Plant)]) == 2
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

    def test_simulation_with_food_drops(self, fish_tank_setup):
        """Test that the simulation handles food drops correctly."""
        simulator = fish_tank_setup
        simulator.environment.agents = simulator.agents
        simulator.create_initial_agents()

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
            success = True
        except Exception:
            success = False

        assert success, "Simulation with food should run without crashing"

    def test_simulation_handles_fish_crab_interactions(self, fish_tank_setup):
        """Test that fish-crab collision handling works over time."""
        simulator = fish_tank_setup
        simulator.environment.agents = simulator.agents

        # Create a simple scenario with one fish and one crab
        from movement_strategy import SoloFishMovement
        fish = Fish(simulator.environment, SoloFishMovement(), ['george1.png'], 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos.x = 500  # Far from fish initially
        crab.pos.y = 500

        simulator.agents.add(fish, crab)

        # Run simulation
        try:
            for _ in range(100):
                simulator.handle_collisions()
                for sprite in list(simulator.agents):
                    sprite.update(0)
            success = True
        except Exception:
            success = False

        assert success, "Fish-crab interactions should work without errors"

    def test_simulation_state_consistency(self, fish_tank_setup):
        """Test that simulation maintains consistent state over time."""
        simulator = fish_tank_setup
        simulator.environment.agents = simulator.agents
        simulator.create_initial_agents()

        initial_non_food_count = len([s for s in simulator.agents if not isinstance(s, Food)])

        # Run simulation
        for _ in range(50):
            simulator.update()

        # Plants, castle, and crabs should still be there (they don't move/die)
        plants = [s for s in simulator.agents if isinstance(s, Plant)]
        castles = [s for s in simulator.agents if isinstance(s, Castle)]
        crabs = [s for s in simulator.agents if isinstance(s, Crab)]

        assert len(plants) == 2, "Plants should remain in the simulation"
        assert len(castles) == 1, "Castle should remain in the simulation"
        assert len(crabs) == 1, "Crab should remain in the simulation"

    def test_simulation_with_rapid_updates(self, fish_tank_setup):
        """Test simulation stability with rapid updates."""
        simulator = fish_tank_setup
        simulator.environment.agents = simulator.agents
        simulator.create_initial_agents()

        # Run many updates in quick succession
        try:
            for _ in range(500):
                simulator.update()
            success = True
        except Exception:
            success = False

        assert success, "Simulation should handle rapid updates without issues"

    def test_bug_fixes_verified(self, fish_tank_setup):
        """Verify that our critical bug fixes are working."""
        simulator = fish_tank_setup
        simulator.environment.agents = simulator.agents

        from movement_strategy import SoloFishMovement, SchoolingFishMovement

        # Test 1: Fish avoidance bug fix - fish should maintain avoidance when crab stays close
        fish = Fish(simulator.environment, SoloFishMovement(), ['george1.png'], 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos.x = 110  # Close to fish
        crab.pos.y = 100

        simulator.agents.add(fish, crab)

        # Move several times - avoidance should persist
        for _ in range(10):
            fish.movement_strategy.move(fish)

        # Avoidance should still be active (not reset to zero)
        # because crab is still close
        assert fish.avoidance_velocity.length() > 0, "Avoidance should persist when crab stays close"

        # Test 2: Safe iteration during collision - should not crash
        simulator.agents.empty()
        fish1 = Fish(simulator.environment, SoloFishMovement(), ['george1.png'], 100, 100, 3)
        fish2 = Fish(simulator.environment, SoloFishMovement(), ['george1.png'], 200, 200, 3)
        crab = Crab(simulator.environment)

        simulator.agents.add(fish1, fish2, crab)

        try:
            # This tests our fix for safe iteration when removing sprites
            for _ in range(20):
                simulator.handle_collisions()
            success = True
        except Exception:
            success = False

        assert success, "Collision handling should safely iterate when removing sprites"

        # Test 3: Zero-length vector safety - should not crash
        simulator.agents.empty()
        fish = Fish(simulator.environment, SoloFishMovement(), ['george1.png'], 100, 100, 3)
        crab = Crab(simulator.environment)
        crab.pos = fish.pos  # Same position - zero-length vector!

        simulator.agents.add(fish, crab)

        try:
            # This tests our zero-length vector safety checks
            fish.avoid([crab], 50)
            success = True
        except Exception:
            success = False

        assert success, "Zero-length vector handling should not crash"
