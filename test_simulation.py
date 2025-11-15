"""Quick test to verify the simulation runs without errors."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()

from fishtank import FishTankSimulator
import agents

def test_simulation():
    """Run simulation for 100 frames to test for errors."""
    print("Starting simulation test...")

    sim = FishTankSimulator()
    sim.setup_game()

    # Run for 3000 frames (~100 seconds at 30fps)
    for frame in range(3000):
        if not sim.handle_events():
            break
        sim.update()

        # Print progress every 300 frames (~10 seconds)
        if frame % 300 == 0:
            fish_count = len([a for a in sim.agents if isinstance(a, agents.Fish)])
            food_count = len([a for a in sim.agents if isinstance(a, agents.Food)])
            if sim.ecosystem:
                stats = sim.ecosystem.get_summary_stats()
                print(f"Frame {frame:4d}: {fish_count:2d} fish, {food_count:2d} food | "
                      f"Gen {stats['current_generation']}, "
                      f"Births: {stats['total_births']}, Deaths: {stats['total_deaths']}")

    print("\nTest completed successfully!")

    # Print final stats
    if sim.ecosystem:
        stats = sim.ecosystem.get_summary_stats()
        print(f"\nFinal stats:")
        print(f"  Population: {stats['total_population']}")
        print(f"  Births: {stats['total_births']}")
        print(f"  Deaths: {stats['total_deaths']}")
        print(f"  Death causes: {stats['death_causes']}")

if __name__ == "__main__":
    test_simulation()
