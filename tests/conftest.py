"""Pytest configuration and fixtures for fish tank tests."""

import random

import pytest


@pytest.fixture
def seeded_rng():
    """Provide a deterministic RNG for tests."""
    return random.Random(42)


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
