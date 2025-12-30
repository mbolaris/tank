import json
from typing import Tuple

from core.simulation.engine import SimulationEngine

NON_DETERMINISTIC_FIELDS = {
    "elapsed_real_time",
    "simulation_speed",
}


def _clean_stats(stats: dict) -> dict:
    return {key: value for key, value in stats.items() if key not in NON_DETERMINISTIC_FIELDS}


def _stats_fingerprint(stats: dict) -> str:
    return json.dumps(_clean_stats(stats), sort_keys=True)


def _get_stable_entity_id(entity) -> str:
    """Get a stable identifier for an entity, avoiding Python's id()."""
    # Try type-specific IDs first
    for id_attr in ("fish_id", "plant_id", "food_id", "crab_id"):
        if hasattr(entity, id_attr):
            return f"{type(entity).__name__}_{getattr(entity, id_attr)}"
    # Fallback: use type + rounded position as identifier
    return f"{type(entity).__name__}_{round(entity.pos.x, 2)}_{round(entity.pos.y, 2)}"


def _world_snapshot_hash(engine: SimulationEngine) -> int:
    """Compute a stable hash of entity positions and energies.

    This catches divergence in world state that stats might miss.
    Uses stable identifiers to ensure deterministic hashing.
    """
    tuples = sorted(
        (
            _get_stable_entity_id(e),
            round(e.pos.x, 6),
            round(e.pos.y, 6),
            round(getattr(e, "energy", 0), 6),
        )
        for e in engine.entities_list
    )
    return hash(tuple(tuples))


def _run_solo(seed: int, frames: int) -> Tuple[SimulationEngine, str]:
    """Run engine solo and return (engine, stats_fingerprint)."""
    engine = SimulationEngine(seed=seed)
    engine.setup()
    for _ in range(frames):
        engine.update()
    return engine, _stats_fingerprint(engine.get_stats())


def _run_interleaved(
    seed_a: int, seed_b: int, frames_each: int
) -> Tuple[SimulationEngine, str, SimulationEngine, str]:
    """Run two engines interleaved, return (engine_a, fp_a, engine_b, fp_b)."""
    engine_a = SimulationEngine(seed=seed_a)
    engine_b = SimulationEngine(seed=seed_b)

    engine_a.setup()
    engine_b.setup()

    for _ in range(frames_each):
        engine_a.update()
        engine_b.update()

    return (
        engine_a,
        _stats_fingerprint(engine_a.get_stats()),
        engine_b,
        _stats_fingerprint(engine_b.get_stats()),
    )


def test_multi_engine_isolation_interleaved_vs_solo():
    """Verify two engines produce identical results whether run solo or interleaved."""
    frames = 200
    seed_a = 12345
    seed_b = 54321

    # Run each engine solo
    engine_solo_a, solo_stats_a = _run_solo(seed_a, frames)
    engine_solo_b, solo_stats_b = _run_solo(seed_b, frames)

    # Run both engines interleaved
    engine_inter_a, inter_stats_a, engine_inter_b, inter_stats_b = _run_interleaved(
        seed_a, seed_b, frames
    )

    # Compare stats fingerprints
    assert solo_stats_a == inter_stats_a, "Engine A stats differ when interleaved"
    assert solo_stats_b == inter_stats_b, "Engine B stats differ when interleaved"

    # Compare world snapshot hashes (catches state divergence that stats miss)
    solo_world_a = _world_snapshot_hash(engine_solo_a)
    solo_world_b = _world_snapshot_hash(engine_solo_b)
    inter_world_a = _world_snapshot_hash(engine_inter_a)
    inter_world_b = _world_snapshot_hash(engine_inter_b)

    assert (
        solo_world_a == inter_world_a
    ), "Engine A world state diverged when interleaved (stats matched but world differed)"
    assert (
        solo_world_b == inter_world_b
    ), "Engine B world state diverged when interleaved (stats matched but world differed)"
