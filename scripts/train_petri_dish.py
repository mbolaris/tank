"""Petri Dish Training Loop.

This script demonstrates a simple training loop for a fish in a minimal environment.
It uses the Pluggable Policy system to control the fish.
"""

import math
import random
import time
from typing import Tuple

from core.entities import Fish, Food
from core.genetics.genome import Genome
from core.movement_strategy import AlgorithmicMovement
from core.policies.behavior_adapter import SimplePolicy
from core.worlds import WorldRegistry
from core.worlds.interfaces import FAST_STEP_ACTION

# Configuration
WIDTH = 600
HEIGHT = 600
MAX_EPISODES = 5
MAX_STEPS_PER_EPISODE = 500


def distance(p1, p2) -> float:
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def heuristic_policy(obs: dict, rng: random.Random) -> Tuple[float, float]:
    """A simple heuristic policy: move towards food info in obs."""
    # Note: real observation building needs to be robust.
    # For this script we might verify what 'build_movement_observation' provides.
    # It usually provides 'nearest_food_vector' if food is visible.

    # But for training, we might want raw access or a specific observation.
    # Let's inspect the observation provided.

    # If no food visible, move randomly
    if "nearest_food_vector" not in obs or not obs["nearest_food_vector"]:
        return (rng.uniform(-1, 1), rng.uniform(-1, 1))

    # Move towards food
    vec = obs["nearest_food_vector"]
    return (vec["x"], vec["y"])


def main():
    print(f"Starting Petri Dish Training (Size: {WIDTH}x{HEIGHT})...")

    # 1. Setup World
    config = {
        "screen_width": WIDTH,
        "screen_height": HEIGHT,
        "auto_food_enabled": False,  # We manually spawn food
        "max_population": 10,  # Allow up to 10 manual fish
        "headless": True,
    }

    adapter = WorldRegistry.create_world("petri", seed=42, **config)

    adapter.reset(seed=42)  # This just resets, return value isn't the Env object

    # Access the real environment to manipulate entities
    real_env = adapter.world.environment

    for episode in range(MAX_EPISODES):
        print(f"\n--- Episode {episode + 1}/{MAX_EPISODES} ---")

        # Reset Episode via adapter (creates fresh empty world with initial population)
        adapter.reset(seed=42 + episode)
        real_env = adapter.world.environment

        # Clear the initial population (auto-spawned due to max_population > 0)
        # We need max_population > 0 to allow us to add our own fish manually.
        for entity in list(adapter.world.entities_list):
            adapter.world.remove_entity(entity)

        rng = random.Random(time.time())

        # Spawn Fish in Center
        fish = Fish(
            environment=real_env,
            movement_strategy=AlgorithmicMovement(),  # Required wrapper for policy
            species="petri_test",
            x=WIDTH / 2,
            y=HEIGHT / 2,
            speed=5.0,
            initial_energy=100.0,
            fish_id=episode + 100,
            ecosystem=adapter.world.ecosystem,
            genome=Genome.random(rng=rng),
        )
        # Environment.agents is managed by the engine via add_entity
        adapter.world.add_entity(fish)  # Use TankWorld method which handles everything

        # Spawn Food at random position
        food_x = rng.uniform(50, WIDTH - 50)
        food_y = rng.uniform(50, HEIGHT - 50)

        food = Food(environment=real_env, x=food_x, y=food_y)
        adapter.world.add_entity(food)

        # Set Policy
        fish.movement_policy = SimplePolicy(heuristic_policy, policy_id="heuristic")

        total_reward = 0.0
        start_dist = distance(fish.pos, food.pos)

        for step in range(MAX_STEPS_PER_EPISODE):
            # Step Simulation
            try:
                adapter.step({FAST_STEP_ACTION: True})
            except Exception as e:
                print(f"Step failed: {e}")
                break

            # Check State
            if food not in real_env.agents and food not in adapter.world.entities_list:
                # Food eaten!
                print(f"Step {step}: Food eaten! Reward +100")
                total_reward += 100
                break

            current_dist = distance(fish.pos, food.pos)

            # Simple dense reward: progress towards goal
            # (In a real RL loop, we'd use (prev_dist - current_dist))

            # But here let's just log
            if step % 50 == 0:
                print(f"Step {step}: Distance={current_dist:.2f}, Energy={fish.energy:.1f}")

            # Check if fish/food exists (safety)
            if fish not in adapter.world.entities_list:
                print("Fish died!")
                if hasattr(fish, "cause_of_death"):
                    print(f"Cause of death: {fish.cause_of_death}")
                print(f"Is Dead: {fish.is_dead()}")
                total_reward -= 50
                break

        print(f"Episode Finish. Total Steps: {step+1}. Start Dist: {start_dist:.1f}")

        # Cleanup for next episode
        adapter.world.remove_entity(fish)
        if food in adapter.world.entities_list:
            adapter.world.remove_entity(food)


if __name__ == "__main__":
    main()
