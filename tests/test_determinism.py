import json
from core.simulation_engine import SimulationEngine


def test_simulation_seed_determinism():
    """SimulationEngine should produce identical results with same seed."""
    seed = 12345
    engine1 = SimulationEngine(seed=seed)
    stats1 = engine1.run_collect_stats(max_frames=50)

    engine2 = SimulationEngine(seed=seed)
    stats2 = engine2.run_collect_stats(max_frames=50)

    # Compare JSON-serializable parts deterministically
    s1 = json.dumps(stats1, sort_keys=True)
    s2 = json.dumps(stats2, sort_keys=True)

    assert s1 == s2
