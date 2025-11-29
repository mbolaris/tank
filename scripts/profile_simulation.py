
import cProfile
import os
import pstats
import sys
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.simulation_engine import SimulationEngine


def run_simulation():
    print("Initializing simulation...")
    sim = SimulationEngine(headless=True)
    sim.setup()

    # Warmup
    print("Warming up...")
    for _ in range(100):
        sim.update()

    # Stress test with more entities
    print("Running profiled simulation (500 frames) with high load...")

    # Force higher population for stress testing (reduced to avoid deck exhaustion)
    for _ in range(50):
        sim.spawn_emergency_fish()

    start_time = time.time()

    profiler = cProfile.Profile()
    profiler.enable()

    try:
        for i in range(500):
            sim.update()
            if i % 100 == 0:
                print(f"Frame {i}/500")
    except Exception as e:
        print(f"Simulation crashed at frame {i}: {e}")
    finally:
        profiler.disable()
        end_time = time.time()

    print(f"Simulation took {end_time - start_time:.4f} seconds")
    print(f"FPS: {500 / (end_time - start_time):.2f}")
    print(f"Final entity count: {len(sim.get_all_entities())}")

    with open("profile_stats.txt", "w") as f:
        stats = pstats.Stats(profiler, stream=f).sort_stats('cumtime')
        stats.print_stats(50)

        f.write("\nTop functions by self time (CPU intensive):\n")
        stats.sort_stats('tottime').print_stats(30)

    print("Stats saved to profile_stats.txt")

if __name__ == "__main__":
    run_simulation()
