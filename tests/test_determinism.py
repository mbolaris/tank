import json

import pytest

from core.simulation_engine import SimulationEngine


# Fields that depend on wall-clock time or other non-deterministic factors
NON_DETERMINISTIC_FIELDS = {
    "elapsed_real_time",
    "simulation_speed",
}


def remove_non_deterministic_fields(stats: dict) -> dict:
    """Remove fields that are inherently non-deterministic (timing, etc.)."""
    return {k: v for k, v in stats.items() if k not in NON_DETERMINISTIC_FIELDS}


@pytest.mark.xfail(
    reason="Simulation has non-deterministic behavior - tracked for Phase 1 RNG cleanup"
)
def test_simulation_seed_determinism():
    """SimulationEngine should produce identical results with same seed.

    This test is currently expected to fail due to non-determinism sources.
    
    ROOT CAUSES (Remaining cleanup targets):
    1. Remaining global `random.*` calls in core modules (approx 70 calls remaining).
    
    2. Some components still initialize with default RNG if not explicitly passed:
       - `core/poker/betting/decision.py` (Fixed but requires caller updates)
       - `core/entities/fish.py` (Fixed random offsets)
    
    3. `core/algorithms/food_seeking.py`:
       - Uses `random.uniform()` for exploration angle
    
    FIX: Continue threading `world.rng` through all call paths.
    """
    seed = 12345
    engine1 = SimulationEngine(seed=seed)
    stats1 = engine1.run_collect_stats(max_frames=50)

    engine2 = SimulationEngine(seed=seed)
    stats2 = engine2.run_collect_stats(max_frames=50)

    # Remove non-deterministic fields before comparison
    stats1_clean = remove_non_deterministic_fields(stats1)
    stats2_clean = remove_non_deterministic_fields(stats2)

    # Compare JSON-serializable parts deterministically
    s1 = json.dumps(stats1_clean, sort_keys=True)
    s2 = json.dumps(stats2_clean, sort_keys=True)

    assert s1 == s2, f"Stats differ between seeded runs:\n{s1[:500]}...\nvs\n{s2[:500]}..."
