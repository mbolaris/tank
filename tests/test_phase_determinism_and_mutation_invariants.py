"""Tests for phase order, determinism, and mutation boundary invariants.

These tests enforce:
- Pipeline step order matches canonical Tank order
- Entity list only changes during commit points
- Same seed produces same simulation state
"""

import hashlib
from collections import defaultdict

from core.simulation.engine import SimulationEngine
from core.simulation.pipeline import EnginePipeline, PipelineStep

CANONICAL_TANK_STEP_ORDER = [
    "frame_start",
    "time_update",
    "environment",
    "entity_act",
    "resolve_energy",
    "lifecycle",
    "spawn",
    "collision",
    "interaction",
    "reproduction",
    "frame_end",
]

# Stages where entity mutations are committed in the canonical Tank engine today.
CANONICAL_COMMIT_STAGES = [
    "frame_start",
    "lifecycle",
    "spawn",
    "collision",
    "interaction",
    "reproduction",
]


def _state_fingerprint(engine: SimulationEngine) -> str:
    """
    Deterministic-ish digest of sim state.
    Intentionally ignores run_id / object ids; focuses on sim-relevant state.
    """
    fish = sorted(engine.get_fish_list(), key=lambda f: f.fish_id)
    parts = []
    parts.append(f"frame={engine.frame_count}")
    parts.append(f"fish_count={len(fish)}")
    # Stable per-fish features (round to reduce float noise if any)
    for f in fish:
        pos = getattr(f, "pos", None) or getattr(f, "position", None)
        vel = getattr(f, "vel", None) or getattr(f, "velocity", None)
        x = pos.x if pos else 0.0
        y = pos.y if pos else 0.0
        vx = vel.x if vel else 0.0
        vy = vel.y if vel else 0.0
        energy = float(getattr(f, "energy", 0.0))
        gen = getattr(f, "generation", 0)
        parts.append(
            f"fish:{f.fish_id}:"
            f"{round(x,3)},{round(y,3)}:"
            f"{round(vx,3)},{round(vy,3)}:"
            f"{round(energy,6)}:"
            f"gen={gen}"
        )

    # Optional: include plants/food counts without depending on unstable ordering
    all_entities = engine.entities_list
    type_counts = defaultdict(int)
    for e in all_entities:
        type_counts[e.__class__.__name__] += 1
    for k in sorted(type_counts):
        parts.append(f"type:{k}={type_counts[k]}")

    raw = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def test_default_pipeline_phase_order(simulation_engine):
    """Verify the default pipeline matches the canonical Tank step order."""
    engine = simulation_engine
    assert engine.pipeline is not None
    assert engine.pipeline.step_names == CANONICAL_TANK_STEP_ORDER


def test_entity_list_only_changes_during_commit_points(simulation_engine, monkeypatch):
    """
    Enforces: no mid-frame entity list mutation.
    The ONLY time entity count is allowed to change is inside _apply_entity_mutations().
    Also locks in commit stage order.
    """
    engine = simulation_engine
    assert engine.pipeline is not None

    stage_calls = []
    commit_deltas_by_step = defaultdict(int)
    current_step = {"name": None}

    orig_apply = engine._apply_entity_mutations

    def wrapped_apply(stage: str) -> None:
        stage_calls.append(stage)
        before = len(engine.entities_list)
        orig_apply(stage)
        after = len(engine.entities_list)
        # Attribute the delta to whichever pipeline step is executing
        commit_deltas_by_step[current_step["name"]] += after - before

    monkeypatch.setattr(engine, "_apply_entity_mutations", wrapped_apply)

    # Wrap pipeline steps so we can assert per-step deltas match commit deltas
    wrapped_steps = []

    for step in engine.pipeline.steps:

        def _make_wrapped_step(step_name, step_fn):
            def _wrapped(engine_ref):
                current_step["name"] = step_name
                before = len(engine_ref.entities_list)
                step_fn(engine_ref)
                after = len(engine_ref.entities_list)

                total_delta = after - before
                commit_delta = commit_deltas_by_step[step_name]

                assert total_delta == commit_delta, (
                    f"Entity list changed outside commit during step '{step_name}'. "
                    f"total_delta={total_delta}, commit_delta={commit_delta}"
                )

            return _wrapped

        wrapped_steps.append(PipelineStep(step.name, _make_wrapped_step(step.name, step.fn)))

    engine.pipeline = EnginePipeline(wrapped_steps)

    # Run one frame
    engine.update()

    assert stage_calls == CANONICAL_COMMIT_STAGES


def test_determinism_same_seed_same_fingerprint():
    """
    Two fresh engines with the same seed should evolve identically for N frames.
    This catches accidental use of global random(), time(), unordered iteration, etc.
    """

    def run(seed: int, frames: int) -> str:
        eng = SimulationEngine(headless=True, seed=seed)
        eng.setup()
        for _ in range(frames):
            eng.update()
        return _state_fingerprint(eng)

    fp1 = run(seed=123, frames=25)
    fp2 = run(seed=123, frames=25)

    assert fp1 == fp2
