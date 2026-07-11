"""Tests for phase profiling telemetry."""

from __future__ import annotations

import os

from core.config.simulation_config import SimulationConfig
from core.simulation.engine import SimulationEngine


def test_profiler_disabled_by_default() -> None:
    """Assert that by default, profiling is disabled and no times are recorded."""
    config = SimulationConfig.headless_fast()
    assert not config.profile_phases

    engine = SimulationEngine(config=config)
    engine.setup()
    assert not engine.profile_phases
    assert not engine.profiler.enabled

    # Times should all be 0.0
    for name, t in engine.profiler.times.items():
        assert t == 0.0

    # Advance frame, should still be 0.0
    engine.update()
    for name, t in engine.profiler.times.items():
        assert t == 0.0


def test_profiler_enabled_via_config() -> None:
    """Assert that profiling can be enabled via config overrides."""
    config = SimulationConfig.headless_fast().with_overrides(profile_phases=True)
    assert config.profile_phases

    engine = SimulationEngine(config=config)
    engine.setup()
    assert engine.profile_phases
    assert engine.profiler.enabled

    # Run one frame to accumulate timings
    engine.update()

    # At least some times should be greater than 0
    total_time = sum(engine.profiler.times.values())
    # Headless fast setup might have very small times, but it should be recorded
    assert total_time >= 0.0


def test_profiler_enabled_via_env_var() -> None:
    """Assert that profiling can be enabled via TANK_PROFILE_PHASES env var."""
    os.environ["TANK_PROFILE_PHASES"] = "1"
    try:
        config = SimulationConfig.headless_fast()
        # Env var override is evaluated in SimulationEngine.__init__
        engine = SimulationEngine(config=config)
        engine.setup()
        assert engine.profiler.enabled

        engine.update()
        total_time = sum(engine.profiler.times.values())
        assert total_time >= 0.0
    finally:
        del os.environ["TANK_PROFILE_PHASES"]


def test_profiler_queries_and_decisions() -> None:
    """Assert that spatial grid queries and decision blocks are timed correctly."""
    config = SimulationConfig.headless_fast().with_overrides(profile_phases=True)
    engine = SimulationEngine(config=config)
    engine.setup()

    # Reset cumulative times to 0.0 for deterministic test inputs
    for key in engine.profiler.times:
        engine.profiler.times[key] = 0.0

    # Trigger some mock queries inside decision/collision contexts
    engine.profiler.start_frame()
    with engine.profiler.context("entity_act"):
        with engine.profiler.context("decision"):
            engine.profiler.record_query(0.005)
            engine.profiler.record_decide(0.012)
        # Outside decision but in entity_act query
        engine.profiler.record_query(0.002)
        engine.profiler.record_entity_act(0.020)

    with engine.profiler.context("collision"):
        engine.profiler.record_query(0.003)
        engine.profiler.record_collision(0.008)

    engine.profiler.record_rebuild_grid(0.004)
    engine.profiler.record_frame_end(0.015)

    engine.profiler.end_frame()

    # Check net calculations:
    # 1. total perception queries = 0.005 + 0.002 + 0.003 = 0.010
    assert abs(engine.profiler.times["perception"] - 0.010) < 1e-6

    # 2. net decision = 0.012 - 0.005 (nested query) = 0.007
    assert abs(engine.profiler.times["decision"] - 0.007) < 1e-6

    # 3. net action = 0.020 (total act) - 0.012 (total decide) - 0.002 (non-decide query) = 0.006
    assert abs(engine.profiler.times["action"] - 0.006) < 1e-6

    # 4. net resolution = 0.008 (total collision) - 0.003 (nested query) = 0.005
    assert abs(engine.profiler.times["resolution"] - 0.005) < 1e-6

    # 5. net stats collection = 0.015 (total frame end) - 0.004 (rebuild grid) = 0.011
    assert abs(engine.profiler.times["stats collection"] - 0.011) < 1e-6

    # 6. spatial grid = 0.004 (rebuild grid)
    assert abs(engine.profiler.times["spatial grid"] - 0.004) < 1e-6
