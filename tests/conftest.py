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
    """Patch DATA_DIR to use a temporary directory for all tests.

    This prevents tests from polluting the real data/tanks directory.
    """
    import backend.tank_persistence

    # Store original value
    original_data_dir = backend.tank_persistence.DATA_DIR

    # Patch with tmp_path
    backend.tank_persistence.DATA_DIR = tmp_path / "data" / "tanks"
    backend.tank_persistence.DATA_DIR.mkdir(parents=True, exist_ok=True)

    yield backend.tank_persistence.DATA_DIR

    # Restore original value
    backend.tank_persistence.DATA_DIR = original_data_dir


@pytest.fixture
def simulation_env(seeded_rng):
    """Provide a clean simulation environment for each test."""
    from core.agents_wrapper import AgentsWrapper
    from core.config.display import (
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
    )
    from core.environment import Environment

    entities_list = []
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
