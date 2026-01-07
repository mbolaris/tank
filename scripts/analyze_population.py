"""Population Dynamics Analysis Script

Analyzes why fish population might not be reaching max capacity.
Checks reproduction rates, death rates, energy levels, and bottlenecks.
"""

import os
import sys

sys.path.insert(0, os.getcwd())

# Initialize logging
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from core.entities import Fish
from core.entities.base import LifeStage
from core.tank_world import TankWorld, TankWorldConfig


def analyze_population(tank: TankWorld, frames: int = 3000):
    """Run simulation and analyze population dynamics."""

    print("\n" + "=" * 70)
    print("POPULATION DYNAMICS ANALYSIS")
    print("=" * 70)

    # Tracking variables
    max_pop_reached = 0
    frames_at_max = 0

    # Per-frame samples for analysis
    samples = []

    for frame in range(frames):
        tank.update()

        # Get current fish list
        fish_list = [e for e in tank.engine.get_all_entities() if isinstance(e, Fish)]
        fish_count = len(fish_list)

        # Track max population
        if fish_count > max_pop_reached:
            max_pop_reached = fish_count

        if fish_count >= tank.config.max_population - 5:
            frames_at_max += 1

        # Sample every 100 frames
        if frame % 100 == 0 and fish_list:
            adults = [f for f in fish_list if f.life_stage == LifeStage.ADULT]
            babies = [f for f in fish_list if f.life_stage == LifeStage.BABY]
            juveniles = [f for f in fish_list if f.life_stage == LifeStage.JUVENILE]
            elders = [f for f in fish_list if f.life_stage == LifeStage.ELDER]

            # Energy analysis
            avg_energy = sum(f.energy for f in fish_list) / len(fish_list)
            max_energy_avg = sum(f.max_energy for f in fish_list) / len(fish_list)
            energy_ratio = avg_energy / max_energy_avg if max_energy_avg > 0 else 0

            # Reproduction readiness
            ready_to_reproduce = sum(1 for f in fish_list if f.can_reproduce())
            off_cooldown = sum(1 for f in fish_list if f.reproduction_cooldown <= 0)
            full_energy = sum(1 for f in fish_list if f.energy >= f.max_energy * 0.9)
            at_max_energy = sum(1 for f in fish_list if f.energy >= f.max_energy)

            # Asexual reproduction chance
            asexual_chances = [
                f.genome.behavioral.asexual_reproduction_chance.value for f in fish_list
            ]
            avg_asexual_chance = (
                sum(asexual_chances) / len(asexual_chances) if asexual_chances else 0
            )

            sample = {
                "frame": frame,
                "pop": fish_count,
                "adults": len(adults),
                "babies": len(babies),
                "juveniles": len(juveniles),
                "elders": len(elders),
                "avg_energy_ratio": energy_ratio,
                "ready_to_reproduce": ready_to_reproduce,
                "off_cooldown": off_cooldown,
                "full_energy_90pct": full_energy,
                "at_max_energy": at_max_energy,
                "avg_asexual_chance": avg_asexual_chance,
            }
            samples.append(sample)

            # Print progress
            if frame % 500 == 0:
                print(
                    f"Frame {frame}: Pop={fish_count}, Adults={len(adults)}, "
                    f"ReadyRepro={ready_to_reproduce}, FullEnergy={at_max_energy}, "
                    f"AvgEnergy={energy_ratio:.1%}"
                )

    # Final analysis
    ecosystem = tank.ecosystem

    print("\n" + "-" * 70)
    print("FINAL STATISTICS")
    print("-" * 70)

    print("\nPopulation:")
    print(f"  Max capacity: {tank.config.max_population}")
    print(
        f"  Final population: {len([e for e in tank.engine.get_all_entities() if isinstance(e, Fish)])}"
    )
    print(f"  Peak population reached: {max_pop_reached}")
    print(f"  Frames near max (>={tank.config.max_population - 5}): {frames_at_max}")

    print("\nBirths & Deaths:")
    print(f"  Total births: {ecosystem.total_births}")
    print(f"  Total deaths: {ecosystem.total_deaths}")
    print(f"  Net population change: {ecosystem.total_births - ecosystem.total_deaths}")

    print("\nDeath Causes:")
    for cause, count in sorted(ecosystem.death_causes.items(), key=lambda x: -x[1]):
        print(f"  {cause}: {count}")

    print("\nReproduction Stats:")
    repro_summary = ecosystem.get_reproduction_summary()
    for key, value in repro_summary.items():
        print(f"  {key}: {value}")

    # Calculate bottlenecks
    print("\n" + "-" * 70)
    print("BOTTLENECK ANALYSIS")
    print("-" * 70)

    if samples:
        avg_pop = sum(s["pop"] for s in samples) / len(samples)
        avg_adults = sum(s["adults"] for s in samples) / len(samples)
        avg_ready = sum(s["ready_to_reproduce"] for s in samples) / len(samples)
        avg_full_energy = sum(s["at_max_energy"] for s in samples) / len(samples)
        avg_off_cooldown = sum(s["off_cooldown"] for s in samples) / len(samples)
        avg_energy_ratio = sum(s["avg_energy_ratio"] for s in samples) / len(samples)
        avg_asexual = sum(s["avg_asexual_chance"] for s in samples) / len(samples)

        print("\nAverage across simulation:")
        print(f"  Population: {avg_pop:.1f}")
        print(f"  Adults: {avg_adults:.1f} ({avg_adults/avg_pop*100:.1f}% of population)")
        print(f"  Ready to reproduce (all conditions): {avg_ready:.1f}")
        print(f"  At max energy: {avg_full_energy:.1f}")
        print(f"  Off cooldown: {avg_off_cooldown:.1f}")
        print(f"  Average energy ratio: {avg_energy_ratio:.1%}")
        print(f"  Average asexual reproduction chance: {avg_asexual:.1%}")

        # Identify bottlenecks
        print("\n>>> IDENTIFIED BOTTLENECKS <<<")

        if avg_adults / avg_pop < 0.3:
            print("  [!] LOW ADULT RATIO: Most fish aren't reaching adulthood")
            print(
                f"      Only {avg_adults/avg_pop*100:.1f}% are adults. May be dying before maturity."
            )

        if avg_full_energy < avg_adults * 0.5:
            print("  [!] LOW ENERGY LEVELS: Adults aren't reaching max energy")
            print(f"      Only {avg_full_energy:.1f} fish at max energy vs {avg_adults:.1f} adults")
            print("      This limits asexual reproduction (requires 100% energy).")

        if avg_off_cooldown < avg_adults * 0.8:
            print("  [!] COOLDOWN BOTTLENECK: Many adults on reproduction cooldown")
            print(f"      Only {avg_off_cooldown:.1f} fish off cooldown vs {avg_adults:.1f} adults")

        if avg_asexual < 0.1:
            print("  [!] LOW ASEXUAL CHANCE: Genetic trait is low")
            print(f"      Average asexual reproduction chance is only {avg_asexual:.1%}")
            print("      Even eligible fish have low probability of reproducing each frame.")

        if avg_ready < 1:
            print("  [!] VERY FEW FISH READY: Almost no fish meet all reproduction conditions")
            print("      Requirements: Adult + 100% energy + off cooldown")

        # Calculate theoretical reproduction rate
        expected_repro_per_frame = avg_ready * avg_asexual
        expected_repro_per_second = expected_repro_per_frame * 30
        print(f"\n  Theoretical reproduction rate: {expected_repro_per_second:.2f} births/second")
        print(f"  Actual rate: {ecosystem.total_births / (frames/30):.2f} births/second")

        death_rate = ecosystem.total_deaths / (frames / 30)
        print(f"  Death rate: {death_rate:.2f} deaths/second")

        if death_rate > expected_repro_per_second:
            print("\n  [!] DEATHS OUTPACING BIRTHS: Population cannot sustain itself")


def main():
    print("Initializing simulation...")

    config = TankWorldConfig(
        max_population=100,
        auto_food_enabled=True,
    )

    tank = TankWorld(config=config)

    # Initialize the simulation first
    tank.setup()

    # Check if ecosystem and environment are ready
    if tank.engine.ecosystem is None:
        print("ERROR: Ecosystem not initialized!")
        return
    if tank.engine.environment is None:
        print("ERROR: Environment not initialized!")
        return

    print(f"Ecosystem: {tank.engine.ecosystem}")
    print(f"Environment: {tank.engine.environment}")

    # Spawn initial population
    initial_spawn = 20
    for _ in range(initial_spawn):
        tank.engine.spawn_emergency_fish()

    fish_count = len([e for e in tank.engine.get_all_entities() if isinstance(e, Fish)])
    print(f"Starting with {fish_count} fish")

    if fish_count == 0:
        print("WARNING: No fish spawned! Check spawn_emergency_fish implementation.")
        return

    print(f"Max population: {config.max_population}")
    print("\nRunning 100 seconds of simulation (3000 frames at 30fps)...")

    analyze_population(tank, frames=3000)

    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print(
        """
Based on analysis, consider:
1. If energy is the bottleneck: Increase food spawn rate or reduce metabolism
2. If adults are rare: Reduce death rate (check starvation) or speed up maturation
3. If asexual chance is low: Increase default genetic trait value
4. If cooldown is bottleneck: Reduce REPRODUCTION_COOLDOWN constant
5. If deaths > births: Address primary death cause (starvation = more food needed)
"""
    )


if __name__ == "__main__":
    main()
