"""Test simulation determinism with seeded random."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import pytest

from simulation_engine import SimulationEngine
from core import entities


@pytest.mark.xfail(reason="Simulation has non-deterministic behavior that needs investigation")
def test_simulation_determinism():
    """Verify two runs with the same seed produce identical results."""
    print("=" * 80)
    print("TESTING: Simulation Determinism")
    print("=" * 80)

    SEED = 42
    NUM_FRAMES = 1000

    # Run simulation #1
    print("\n1. Running simulation #1...")
    print("-" * 40)
    random.seed(SEED)
    sim1 = SimulationEngine(headless=True)
    sim1.setup()

    for frame in range(NUM_FRAMES):
        sim1.update()
        if frame % 200 == 0:
            fish_count = len([e for e in sim1.entities_list if isinstance(e, entities.Fish)])
            print(f"  Frame {frame:4d}: {fish_count:2d} fish")

    # Get stats from simulation #1
    stats1 = sim1.ecosystem.get_summary_stats(sim1.entities_list)
    print(f"\nSimulation #1 Results:")
    print(f"  Population: {stats1['total_population']}")
    print(f"  Generation: {stats1['current_generation']}")
    print(f"  Births: {stats1['total_births']}")
    print(f"  Deaths: {stats1['total_deaths']}")
    print(f"  Death causes: {stats1['death_causes']}")

    # Run simulation #2 with same seed
    print("\n2. Running simulation #2 (same seed)...")
    print("-" * 40)
    random.seed(SEED)
    sim2 = SimulationEngine(headless=True)
    sim2.setup()

    for frame in range(NUM_FRAMES):
        sim2.update()
        if frame % 200 == 0:
            fish_count = len([e for e in sim2.entities_list if isinstance(e, entities.Fish)])
            print(f"  Frame {frame:4d}: {fish_count:2d} fish")

    # Get stats from simulation #2
    stats2 = sim2.ecosystem.get_summary_stats(sim2.entities_list)
    print(f"\nSimulation #2 Results:")
    print(f"  Population: {stats2['total_population']}")
    print(f"  Generation: {stats2['current_generation']}")
    print(f"  Births: {stats2['total_births']}")
    print(f"  Deaths: {stats2['total_deaths']}")
    print(f"  Death causes: {stats2['death_causes']}")

    # Compare results
    print("\n3. Comparing Results...")
    print("-" * 40)

    differences = []

    # Compare population
    if stats1["total_population"] != stats2["total_population"]:
        differences.append(
            f"Population: {stats1['total_population']} vs {stats2['total_population']}"
        )

    # Compare generation
    if stats1["current_generation"] != stats2["current_generation"]:
        differences.append(
            f"Generation: {stats1['current_generation']} vs {stats2['current_generation']}"
        )

    # Compare births
    if stats1["total_births"] != stats2["total_births"]:
        differences.append(f"Births: {stats1['total_births']} vs {stats2['total_births']}")

    # Compare deaths
    if stats1["total_deaths"] != stats2["total_deaths"]:
        differences.append(f"Deaths: {stats1['total_deaths']} vs {stats2['total_deaths']}")

    # Compare death causes
    causes1 = stats1["death_causes"]
    causes2 = stats2["death_causes"]

    all_causes = set(causes1.keys()) | set(causes2.keys())
    for cause in all_causes:
        count1 = causes1.get(cause, 0)
        count2 = causes2.get(cause, 0)
        if count1 != count2:
            differences.append(f"Death cause '{cause}': {count1} vs {count2}")

    # Print results
    print("\n" + "=" * 80)
    if differences:
        print("DETERMINISM TEST FAILED")
        print("=" * 80)
        print("\nDifferences found:")
        for diff in differences:
            print(f"  - {diff}")
        print("\nThe simulation should be deterministic with a fixed seed!")
        print("=" * 80)
        assert False, "Simulation is not deterministic!"
    else:
        print("DETERMINISM TEST PASSED")
        print("=" * 80)
        print("\nBoth runs with seed={} produced identical results!".format(SEED))
        print("  ✓ Same population")
        print("  ✓ Same generation")
        print("  ✓ Same number of births")
        print("  ✓ Same number of deaths")
        print("  ✓ Same death causes")
        print("=" * 80)


if __name__ == "__main__":
    test_simulation_determinism()
