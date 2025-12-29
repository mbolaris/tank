"""Quick test to verify the simulation runs without errors."""

from core import entities
from core.simulation.engine import SimulationEngine


def test_simulation():
    """Run simulation for 100 frames to test for errors."""
    print("Starting simulation test...")

    sim = SimulationEngine(headless=True)
    sim.setup()

    # Run for 3000 frames (~100 seconds at 30fps)
    for frame in range(3000):
        sim.update()

        # Print progress every 300 frames (~10 seconds)
        if frame % 300 == 0:
            fish_count = len([e for e in sim.entities_list if isinstance(e, entities.Fish)])
            food_count = len([e for e in sim.entities_list if isinstance(e, entities.Food)])
            if sim.ecosystem:
                stats = sim.ecosystem.get_summary_stats(sim.entities_list)
                print(
                    f"Frame {frame:4d}: {fish_count:2d} fish, {food_count:2d} food | "
                    f"Gen {stats['current_generation']}, "
                    f"Births: {stats['total_births']}, Deaths: {stats['total_deaths']}"
                )

    print("\nTest completed successfully!")

    # Print final stats
    if sim.ecosystem:
        stats = sim.ecosystem.get_summary_stats(sim.entities_list)
        print("\nFinal stats:")
        print(f"  Population: {stats['total_population']}")
        print(f"  Births: {stats['total_births']}")
        print(f"  Deaths: {stats['total_deaths']}")
        print(f"  Death causes: {stats['death_causes']}")


if __name__ == "__main__":
    test_simulation()
