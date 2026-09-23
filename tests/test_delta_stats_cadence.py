"""Delta frames carry the stats block at a readable cadence, not every frame.

Recomputing and resending every stats figure on each 15 Hz delta was ~45% of
building one. The publisher now attaches stats to a delta only once
``delta_stats_interval`` frames have passed (full syncs always carry them), and
the client keeps its last block in between - see ``applyDelta`` in
``frontend/src/hooks/useWebSocket.ts``.
"""

from __future__ import annotations

from itertools import pairwise

from backend.simulation_runner import SimulationRunner
from backend.state_payloads import DeltaStatePayload, FullStatePayload
from core.worlds.interfaces import FAST_STEP_ACTION


def _runner() -> SimulationRunner:
    runner = SimulationRunner(seed=42, world_id="delta-stats-cadence")
    runner.running = True
    for _ in range(20):
        runner.world.step({FAST_STEP_ACTION: True})
    return runner


def test_deltas_carry_stats_every_interval_and_full_syncs_always() -> None:
    runner = _runner()
    publisher = runner.state_publisher
    interval = publisher.delta_stats_interval
    assert interval > 1

    full = publisher.get_state(runner, force_full=True, allow_delta=False)
    assert isinstance(full, FullStatePayload)
    assert full.stats is not None

    frames_with_stats = []
    for _ in range(3 * interval):
        runner.world.step({FAST_STEP_ACTION: True})
        state = publisher.get_state(runner, force_full=False, allow_delta=True)
        assert isinstance(state, DeltaStatePayload)
        if state.stats is not None:
            frames_with_stats.append(state.frame)
        else:
            assert "stats" not in state.to_dict()["snapshot"]

    assert len(frames_with_stats) == 3
    gaps = {b - a for a, b in pairwise(frames_with_stats)}
    assert gaps == {interval}


def test_invalidate_restarts_the_stats_cadence() -> None:
    runner = _runner()
    publisher = runner.state_publisher
    publisher.get_state(runner, force_full=True, allow_delta=False)
    runner.world.step({FAST_STEP_ACTION: True})
    publisher.get_state(runner, force_full=False, allow_delta=True)

    publisher.invalidate_cache()
    runner.world.step({FAST_STEP_ACTION: True})
    state = publisher.get_state(runner, force_full=False, allow_delta=True)
    assert state.stats is not None
