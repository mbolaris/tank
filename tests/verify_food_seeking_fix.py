import sys
import unittest

# Add project root to path
sys.path.append(".")

from core.algorithms.base import Vector2
from core.predictive_movement import predict_falling_intercept, predict_intercept_point


class TestFoodPrediction(unittest.TestCase):
    def test_linear_interception(self):
        """Test basic linear interception (for swimming food)."""
        fish_pos = Vector2(0, 0)
        fish_speed = 20.0  # FAST fish

        target_pos = Vector2(20, 0)
        target_vel = Vector2(0, 10.0)  # Moving down fast

        # Intercept should be possible quickly
        intercept, time = predict_intercept_point(fish_pos, fish_speed, target_pos, target_vel)

        print(f"Linear Intercept: {intercept} in {time:.2f}s")

        self.assertIsNotNone(intercept)
        self.assertLess(time, 2.0, "Should be able to intercept within 2s")

        # Verification
        fish_time = (intercept - fish_pos).length() / fish_speed
        (intercept - target_pos).length() / target_vel.length()

        # Times should match
        self.assertAlmostEqual(fish_time, time, places=1)

    def test_falling_interception(self):
        """Test acceleration-aware interception (for falling food)."""
        fish_pos = Vector2(0, 0)
        fish_speed = 2.0

        target_pos = Vector2(100, 0)
        target_vel = Vector2(0, 0)  # Starts stationary
        acceleration = 0.01  # Standard gravity

        # Predict
        intercept, time = predict_falling_intercept(
            fish_pos, fish_speed, target_pos, target_vel, acceleration
        )

        print(f"Falling Intercept: {intercept} in {time:.2f}s")

        # Calculate actual target position at that time
        target_y = target_pos.y + target_vel.y * time + 0.5 * acceleration * time * time
        target_x = target_pos.x + target_vel.x * time

        actual_target_pos = Vector2(target_x, target_y)

        # Distance between predicted intercept and actual target position should be small
        error = (intercept - actual_target_pos).length()
        print(f"Prediction Error: {error:.4f}px")

        self.assertLess(error, 1.0, "Prediction should be accurate within 1px")

        # Compare with naive linear prediction
        naive_intercept, naive_time = predict_intercept_point(
            fish_pos, fish_speed, target_pos, target_vel
        )

        print(f"Naive Intercept: {naive_intercept}")

        # Naive prediction for stationary/slow start object is basically current position
        # Naive predicts (100, 0) + velocity*time. Velocity is 0. So (100, 0).
        # New model predicts (100, 12.7).
        # Difference should be substantial.

        improvement = (intercept - naive_intercept).length()
        print(f"Improvement over naive: {improvement:.2f}px")

        self.assertGreater(
            improvement, 5.0, "New prediction should be significantly different (better) than naive"
        )


if __name__ == "__main__":
    unittest.main()
