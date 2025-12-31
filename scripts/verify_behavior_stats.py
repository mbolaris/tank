
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.services.stats_calculator import StatsCalculator
from core.simulation.engine import SimulationEngine


def verify():
    print("Initializing engine...")
    engine = SimulationEngine()
    engine.setup()

    print("Engine setup complete (population initialized).")

    print("Calculating stats...")
    calculator = StatsCalculator(engine)
    stats = calculator.get_stats()

    behavioral_dists = stats.get("gene_distributions", {}).get("behavioral", [])

    print(f"Found {len(behavioral_dists)} behavioral distributions.")

    expected_keys = [
        "threat_response", "food_approach", "energy_style",
        "social_mode", "poker_engagement",
        "flee_speed", "flee_threshold", "social_distance" # check a few params
    ]

    found_keys = [d["key"] for d in behavioral_dists]

    missing = [k for k in expected_keys if k not in found_keys]

    if missing:
        print(f"FAILURE: Missing keys: {missing}")
        print(f"Found keys: {found_keys}")
        sys.exit(1)

    print("SUCCESS: All expected keys found.")

    # Check threat_response specifically
    threat = next(d for d in behavioral_dists if d["key"] == "threat_response")
    print("Threat Response Stats:")
    print(f"  Discrete: {threat['discrete']}")
    print(f"  Allowed Range: {threat['allowed_min']} - {threat['allowed_max']}")
    print(f"  Observed Range: {threat['min']} - {threat['max']}")
    print(f"  Bins: {threat['bins']}")

    if not threat['discrete']:
        print("FAILURE: Threat response should be discrete")
        sys.exit(1)

    print("Verification Passed!")

if __name__ == "__main__":
    verify()
