"""Pytest configuration and fixtures for fish tank tests."""

import random

import pytest

# =============================================================================
# Contract Registration
# =============================================================================


def register_builtin_contracts_for_tests() -> None:
    """Register all builtin contract implementations for testing.

    This ensures tests that construct Environment directly (bypassing engine/pack
    registration) still have access to required contracts like observation builders.
    """
    # Tank
    from core.worlds.tank.movement_observations import register_tank_movement_observation_builder
    from core.worlds.tank.tank_actions import register_tank_action_translator

    register_tank_action_translator("tank")
    register_tank_movement_observation_builder("tank")

    # Petri (reuses Tank implementations but registers under "petri" world type)
    from core.worlds.petri.movement_observations import register_petri_movement_observation_builder
    from core.worlds.petri.petri_actions import register_petri_action_translator

    register_petri_action_translator("petri")
    register_petri_movement_observation_builder("petri")


@pytest.fixture(autouse=True, scope="session")
def _register_contracts():
    """Session-scoped fixture to register contracts once for all tests."""
    register_builtin_contracts_for_tests()


@pytest.fixture
def seeded_rng():
    """Provide a deterministic RNG for tests."""
    return random.Random(42)


@pytest.fixture(autouse=True)
def mock_data_dir(tmp_path):
    """Keep persistence tests from writing into the real repo."""
    import backend.world_persistence as wp

    original = wp.DATA_DIR
    wp.DATA_DIR = tmp_path / "data" / "worlds"
    wp.DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        yield wp.DATA_DIR
    finally:
        wp.DATA_DIR = original


@pytest.fixture
def simulation_env(seeded_rng):
    """Provide a clean simulation environment for each test."""
    from core.agents_wrapper import AgentsWrapper
    from core.config.display import SCREEN_HEIGHT, SCREEN_WIDTH
    from core.entities import Agent
    from core.environment import Environment

    entities_list: list[Agent] = []
    env = Environment(entities_list, SCREEN_WIDTH, SCREEN_HEIGHT, rng=seeded_rng)
    agents_wrapper = AgentsWrapper(entities_list)
    return env, agents_wrapper


@pytest.fixture
def simulation_engine():
    """Setup a simulation engine for testing with deterministic seed."""
    from core.simulation.engine import SimulationEngine

    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    return engine


@pytest.fixture
def simulation_engine_strict():
    """SimulationEngine with mutation invariants enforced at end of frame."""
    from core.simulation.engine import SimulationEngine

    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()
    engine._phase_debug_enabled = True  # Enable directly
    return engine


@pytest.fixture(autouse=True, scope="session")
def _force_mutation_invariants_in_tests():
    """Force mutation invariant checking for all engine tests.

    This helps catch regression where mutation queue is ignored or bypassed.
    """
    import os

    # We use env var so it propagates to SimulationEngine.__init__ logic
    os.environ["TANK_ENFORCE_MUTATION_INVARIANTS"] = "1"
    yield
    os.environ.pop("TANK_ENFORCE_MUTATION_INVARIANTS", None)
