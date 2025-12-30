import difflib
import json

from core.simulation.engine import SimulationEngine
from tests.test_determinism import remove_non_deterministic_fields


def debug_determinism_diff():
    seed = 12345
    print("Run 1...")
    engine1 = SimulationEngine(seed=seed)
    stats1 = engine1.run_collect_stats(max_frames=50)

    print("Run 2...")
    engine2 = SimulationEngine(seed=seed)
    stats2 = engine2.run_collect_stats(max_frames=50)

    stats1_clean = remove_non_deterministic_fields(stats1)
    stats2_clean = remove_non_deterministic_fields(stats2)

    s1 = json.dumps(stats1_clean, sort_keys=True, indent=2)
    s2 = json.dumps(stats2_clean, sort_keys=True, indent=2)

    if s1 == s2:
        print("SUCCESS: JSONs are identical.")
    else:
        print("FAILURE: JSONs differ.")

        diff = difflib.unified_diff(
            s1.splitlines(),
            s2.splitlines(),
            fromfile="stats1.json",
            tofile="stats2.json",
            lineterm="",
        )
        print("\n".join(list(diff)[:50]))


if __name__ == "__main__":
    debug_determinism_diff()
