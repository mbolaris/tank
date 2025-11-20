"""Pytest configuration and fixtures for fish tank tests."""

import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def simulation_env():
    """Provide a clean simulation environment for each test."""
    from core.constants import SCREEN_HEIGHT, SCREEN_WIDTH
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
