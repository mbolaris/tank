"""Quick runtime check for SimulationEngine import and minimal API.

This script is intended for local developer checks and CI smoke tests.
"""
from core.simulation.engine import SimulationEngine


def main() -> None:
    print("Creating SimulationEngine(max_frames=5, seed=1)")
    eng = SimulationEngine(seed=1)
    print("Has run_collect_stats:", hasattr(eng, "run_collect_stats"))
    if hasattr(eng, "run_collect_stats"):
        stats = eng.run_collect_stats(max_frames=5)
        print("Stats type:", type(stats))


if __name__ == "__main__":
    main()
