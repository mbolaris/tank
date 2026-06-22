import unittest
from unittest.mock import MagicMock, patch

from core.math_utils import Vector2


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
    def test_move_applies_desired_velocity(self, mock_build_obs):
        # The internal movement path uses the arbiter's desired velocity directly
        # (scaled by speed, then smoothed) - no external-brain action round-trip.
        mock_build_obs.return_value = {}

        # Force a specific desired decision via the movement_policy override drive.
        self.fish.movement_policy = MagicMock(return_value=(1.0, 0.5))

        self.strategy.move(self.fish)

        # target = (1.0*speed, 0.5*speed) = (2.0, 1.0); smoothing 0.1 from vel (0,0):
        # vel.x += (2.0 - 0) * 0.1 = 0.2; vel.y += (1.0 - 0) * 0.1 = 0.1
        self.assertAlmostEqual(self.fish.vel.x, 0.2)
        self.assertAlmostEqual(self.fish.vel.y, 0.1)

    @patch("core.movement_strategy.build_movement_observation")
    def test_move_clamps_desired_velocity_to_action_bound(self, mock_build_obs):
        # A desired component beyond MAX_ACTION_VELOCITY (5.0) is clamped inline
        # before being scaled by speed - the clamp the action translator used to
        # apply, now applied directly without allocating an Action per frame.
        mock_build_obs.return_value = {}

        self.fish.movement_policy = MagicMock(return_value=(10.0, 0.0))

        self.strategy.move(self.fish)

        # Clamp 10.0 -> 5.0; target_vx = 5.0 * 2.0 = 10.0; vel.x += 10.0 * 0.1 = 1.0
        # (Unclamped this would be 2.0, so the assertion distinguishes the clamp.)
        self.assertAlmostEqual(self.fish.vel.x, 1.0)
        self.assertAlmostEqual(self.fish.vel.y, 0.0)
