import json

from core.simulation.engine import SimulationEngine


NON_DETERMINISTIC_FIELDS = {
    "elapsed_real_time",
    "simulation_speed",
}


def _clean_stats(stats: dict) -> dict:
    return {key: value for key, value in stats.items() if key not in NON_DETERMINISTIC_FIELDS}


def _stats_fingerprint(stats: dict) -> str:
    return json.dumps(_clean_stats(stats), sort_keys=True)


def _run_solo(seed: int, frames: int) -> str:
    engine = SimulationEngine(seed=seed)
    engine.setup()
    for _ in range(frames):
        engine.update()
    return _stats_fingerprint(engine.get_stats())


def _run_interleaved(seed_a: int, seed_b: int, frames_each: int) -> tuple[str, str]:
    engine_a = SimulationEngine(seed=seed_a)
    engine_b = SimulationEngine(seed=seed_b)

    engine_a.setup()
    engine_b.setup()

    for _ in range(frames_each):
        engine_a.update()
        engine_b.update()

    return _stats_fingerprint(engine_a.get_stats()), _stats_fingerprint(engine_b.get_stats())


def test_multi_engine_isolation_interleaved_vs_solo():
    frames = 200
    seed_a = 12345
    seed_b = 54321

    solo_a = _run_solo(seed_a, frames)
    solo_b = _run_solo(seed_b, frames)

    inter_a, inter_b = _run_interleaved(seed_a, seed_b, frames)

    assert solo_a == inter_a, "Engine A differs when interleaved with another engine"
    assert solo_b == inter_b, "Engine B differs when interleaved with another engine"
