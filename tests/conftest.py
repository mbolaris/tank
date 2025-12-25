"""Pytest configuration and fixtures for fish tank tests."""

import pytest


@pytest.fixture
def simulation_env():
    """Provide a clean simulation environment for each test."""
    from core.config.display import (
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
    )
    from core.environment import Environment
    from core.simulation_engine import AgentsWrapper

    entities_list = []
    env = Environment(entities_list, SCREEN_WIDTH, SCREEN_HEIGHT)
    agents_wrapper = AgentsWrapper(entities_list)
    return env, agents_wrapper


@pytest.fixture
def simulation_engine():
    """Setup a simulation engine for testing."""
    from core.simulation_engine import SimulationEngine

    engine = SimulationEngine(headless=True)
    engine.setup()

    return engine
