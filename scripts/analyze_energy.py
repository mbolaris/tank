"""Energy Economy Analysis Script

Analyzes whether fish are efficiently gathering energy from:
1. Food (dropped food, nectar, live food)
2. Plant poker games

This helps identify if the issue is energy availability vs energy gathering efficiency.
"""

import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.getcwd())

import logging

logging.basicConfig(level=logging.WARNING)

from core.entities import Fish, Food
from core.entities.plant import Plant, PlantNectar
from core.worlds import WorldRegistry
from core.worlds.tank.backend import TankWorldBackendAdapter


def analyze_energy_economy(tank: TankWorldBackendAdapter, frames: int = 3000) -> None:
    """Analyze energy sources and consumption."""

    print("\n" + "=" * 70)
    print("ENERGY ECONOMY ANALYSIS")
    print("=" * 70)

    # Tracking

    # Track per-frame stats
    samples = []

    initial_births = tank.ecosystem.total_births if tank.ecosystem else 0
    initial_deaths = tank.ecosystem.total_deaths if tank.ecosystem else 0

    for frame in range(frames):
        # Snapshot before update
        entities = tank.engine.get_all_entities()
        fish_list = [e for e in entities if isinstance(e, Fish)]
        [e for e in entities if isinstance(e, (Food, PlantNectar))]
        [e for e in entities if isinstance(e, Plant)]

        # Track energy before update
        sum(f.energy for f in fish_list)

        tank.update()

        # Track energy after update
        entities_after = tank.engine.get_all_entities()
        fish_list_after = [e for e in entities_after if isinstance(e, Fish)]
        sum(f.energy for f in fish_list_after)

        # Sample every 300 frames
        if frame % 300 == 0:
            food_count = len([e for e in entities_after if isinstance(e, Food)])
            nectar_count = len([e for e in entities_after if isinstance(e, PlantNectar)])
            plant_count = len([e for e in entities_after if isinstance(e, Plant)])

            # Average fish energy
            avg_energy = 0.0
            avg_energy_pct = 0.0
            if fish_list_after:
                avg_energy = sum(f.energy for f in fish_list_after) / len(fish_list_after)
                avg_energy_pct = (
                    sum(f.energy / f.max_energy for f in fish_list_after)
                    / len(fish_list_after)
                    * 100
                )

            sample = {
                "frame": frame,
                "fish": len(fish_list_after),
                "food": food_count,
                "nectar": nectar_count,
                "plants": plant_count,
                "avg_energy": avg_energy,
                "avg_energy_pct": avg_energy_pct,
            }
            samples.append(sample)

            print(
                f"Frame {frame:4d}: Fish={len(fish_list_after):2d}, Food={food_count:2d}, "
                f"Nectar={nectar_count:2d}, Plants={plant_count:2d}, "
                f"AvgEnergy={avg_energy_pct:.0f}%"
            )

    # Final stats
    ecosystem = tank.ecosystem

    print("\n" + "-" * 70)
    print("ECOSYSTEM ENERGY STATS")
    print("-" * 70)

    if ecosystem:
        energy_summary = ecosystem.get_energy_source_summary()
        print("\nEnergy Sources (lifetime):")
        for source, amount in energy_summary.items():
            print(f"  {source}: {amount:.1f}")

        print("\nPoker Stats:")
        print(f"  Fish vs Fish games: {ecosystem.total_fish_poker_games}")
        poker_summary = ecosystem.get_poker_stats_summary()
        for key, value in poker_summary.items():
            if "plant" in key.lower() or "mixed" in key.lower():
                print(f"  {key}: {value}")

        final_births = ecosystem.total_births
        final_deaths = ecosystem.total_deaths

        print("\nPopulation Changes:")
        print(f"  Births during analysis: {final_births - initial_births}")
        print(f"  Deaths during analysis: {final_deaths - initial_deaths}")
        print(f"  Death causes: {dict(ecosystem.death_causes)}")

    # Calculate averages
    if samples:
        print("\n" + "-" * 70)
        print("AVERAGES OVER SIMULATION")
        print("-" * 70)

        avg_fish = sum(s["fish"] for s in samples) / len(samples)
        avg_food = sum(s["food"] for s in samples) / len(samples)
        avg_nectar = sum(s["nectar"] for s in samples) / len(samples)
        avg_plants = sum(s["plants"] for s in samples) / len(samples)
        avg_energy_pct = sum(s["avg_energy_pct"] for s in samples) / len(samples)

        print(f"  Average fish count: {avg_fish:.1f}")
        print(f"  Average food available: {avg_food:.1f}")
        print(f"  Average nectar available: {avg_nectar:.1f}")
        print(f"  Average plants: {avg_plants:.1f}")
        print(f"  Average fish energy: {avg_energy_pct:.1f}%")

        # Food-to-fish ratio
        food_per_fish = (avg_food + avg_nectar) / avg_fish if avg_fish > 0 else 0
        print(f"\n  Food items per fish: {food_per_fish:.2f}")

        if food_per_fish > 1:
            print("  [OK] Plenty of food available - fish may not be catching it efficiently")
        elif food_per_fish > 0.5:
            print("  [!] Moderate food availability - could be competition")
        else:
            print("  [!] Low food availability - need more food spawning")


def main():
    print("Initializing simulation for energy analysis...")

    config: Dict[str, Any] = {
        "max_population": 100,
        "auto_food_enabled": True,
    }

    world = WorldRegistry.create_world("tank", seed=42, config=config)
    assert isinstance(world, TankWorldBackendAdapter)
    world.reset(seed=42)

    # Spawn initial population
    from core.simulation.engine import SimulationEngine

    engine = world.engine
    assert isinstance(engine, SimulationEngine)
    assert engine.reproduction_service is not None
    for _ in range(20):
        engine.reproduction_service._spawn_emergency_fish()

    fish_count = len([e for e in world.entities_list if isinstance(e, Fish)])
    print(f"Starting with {fish_count} fish")
    print("\nRunning 100 seconds of simulation...")

    analyze_energy_economy(world, frames=3000)


if __name__ == "__main__":
    main()
