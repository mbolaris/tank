"""Pytest configuration and fixtures for fish tank tests."""
import os
import sys
import pygame
from unittest.mock import Mock, patch
import pytest

# Set up pygame with dummy display before any imports
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def mock_image_loader():
    """Mock the ImageLoader to return dummy surfaces instead of loading files."""
    with patch('image_loader.ImageLoader.load_image') as mock_load:
        # Cache surfaces by filename like the real ImageLoader
        surface_cache = {}

        def create_dummy_surface(filename):
            """Create a minimal surface for testing, cached by filename."""
            if filename not in surface_cache:
                surface = pygame.Surface((20, 20), pygame.SRCALPHA)
                surface.fill((255, 255, 255, 255))
                surface_cache[filename] = surface
            return surface_cache[filename]

        mock_load.side_effect = create_dummy_surface
        yield mock_load


@pytest.fixture
def pygame_env():
    """Provide a clean pygame environment for each test."""
    from core.environment import Environment

    agents = pygame.sprite.Group()
    env = Environment(agents)
    return env, agents


@pytest.fixture
def fish_tank_setup():
    """Setup a fish tank simulator without display."""
    from fishtank import FishTankSimulator
    from core.environment import Environment

    simulator = FishTankSimulator()
    simulator.agents = pygame.sprite.Group()
    simulator.environment = Environment(simulator.agents)

    return simulator
