import unittest
from unittest.mock import MagicMock, patch

from core.math_utils import Vector2
from core.brains.contracts import BrainAction

Action = BrainAction


class TestMovementActions(unittest.TestCase):
    def setUp(self):
        # Create minimal mocks needed for AlgorithmicMovement
        self.fish = MagicMock()
        self.fish.fish_id = 123
        self.fish.genome = MagicMock()
        self.fish.vel = Vector2(0, 0)
        self.fish.pos = Vector2(0, 0)
        self.fish.speed = 2.0
        self.fish.environment.world_type = "tank"
        self.fish.environment.rng = MagicMock()

        # IMPORTANT: MagicMock will auto-create _entity attribute, confusing the safe-unwrap logic
        # in MovementStrategy. We must explicitly delete it to simulate a raw Fish object.
        del self.fish._entity

        # AlgorithmicMovement instance
        from core.movement_strategy import AlgorithmicMovement

        self.strategy = AlgorithmicMovement()

    @patch("core.movement_strategy.build_movement_observation")
    @patch("core.movement_strategy.translate_action")
    def test_move_uses_action_registry(self, mock_translate, mock_build_obs):
        # Mock observation builder to return empty dict
        mock_build_obs.return_value = {}

        # Setup: Force a specific raw decision via movement_policy override
        desired_raw = (1.0, 0.5)
        self.fish.movement_policy = MagicMock(return_value=desired_raw)

        # Setup: Mock translate_action to return a DIFFERENT action
        # This proves the system is using the translated action, not the raw one
        translated_velocity = (0.0, 1.0)  # Different from raw
        mock_action = Action(entity_id="123", target_velocity=translated_velocity)
        mock_translate.return_value = mock_action

        # Act
        self.strategy.move(self.fish)

        # Assert: Registry was called correctly
        mock_translate.assert_called_once()
        args, _ = mock_translate.call_args
        self.assertEqual(args[0], "tank")  # World type
        self.assertEqual(args[1], "123")  # Fish ID string
        self.assertEqual(args[2], desired_raw)  # Raw decision passed through

        # Assert: Fish velocity reflects the TRANSLATED action
        # Note: AlgorithmicMovement applies smoothing, but target should push velocity towards (0, 1)
        # Initial vel is (0,0), target is (0, 2.0) [0.0*speed, 1.0*speed]
        # Smoothing is 0.1. So new vel should be approx (0, 0.2)
        # vel.y += (2.0 - 0) * 0.1 = 0.2

        self.assertAlmostEqual(self.fish.vel.x, 0.0)
        self.assertAlmostEqual(self.fish.vel.y, 0.2)

    @patch("core.movement_strategy.build_movement_observation")
    @patch("core.movement_strategy.translate_action")
    def test_fallback_on_translation_failure(self, mock_translate, mock_build_obs):
        # Mock observation
        mock_build_obs.return_value = {}

        # Setup: Force raw decision
        desired_raw = (1.0, 0.0)
        self.fish.movement_policy = MagicMock(return_value=desired_raw)

        # Setup: Make translation fail
        mock_translate.side_effect = Exception("Registry error")

        # Act
        self.strategy.move(self.fish)

        # Assert: Should fall back to raw decision
        # target_vx = 1.0 * 2.0 = 2.0
        # vel.x += (2.0 - 0) * 0.1 = 0.2
        self.assertAlmostEqual(self.fish.vel.x, 0.2)
