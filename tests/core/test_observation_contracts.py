
import unittest
from unittest.mock import MagicMock, patch
from core.policies.interfaces import build_movement_observation
from core.policies.observation_registry import register_observation_builder, clear_registry

class TestObservationContracts(unittest.TestCase):
    def setUp(self):
        clear_registry()
        self.fish = MagicMock()
        self.fish.fish_id = "123"
        self.fish.environment.world_type = "test_world"

    def tearDown(self):
        clear_registry()

    def test_build_observation_delegates_to_registry(self):
        # Setup: Register a mock builder
        mock_builder = MagicMock()
        mock_builder.build.return_value = {"test": "data"}
        register_observation_builder("test_world", "movement", mock_builder)

        # Act
        obs = build_movement_observation(self.fish)

        # Assert
        mock_builder.build.assert_called_once_with(self.fish, self.fish.environment)
        self.assertEqual(obs, {"test": "data"})

    def test_build_observation_fails_without_registration(self):
        # Act & Assert
        with self.assertRaises(ValueError) as cm:
            build_movement_observation(self.fish)
        
        self.assertIn("No observation builder registered", str(cm.exception))

    def test_default_world_type(self):
        # Setup
        del self.fish.environment.world_type
        mock_builder = MagicMock()
        mock_builder.build.return_value = {"default": "tank"}
        register_observation_builder("tank", "movement", mock_builder)

        # Act
        obs = build_movement_observation(self.fish)

        # Assert
        mock_builder.build.assert_called_once()
        self.assertEqual(obs, {"default": "tank"})
