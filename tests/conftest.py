"""Pytest configuration and fixtures for fish tank tests."""

import random

import pytest


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
