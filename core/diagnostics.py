"""Diagnostics module for tracking simulation metrics."""

from typing import Dict, List, Tuple
from core.math_utils import Vector2

class VelocityTracker:
    """Singleton for tracking fish velocity and acceleration statistics."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VelocityTracker, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance
    
    def reset(self):
        """Reset all statistics."""
        self.max_speed = 0.0
        self.max_acceleration = 0.0
        self.fastest_fish_id = -1
        self.highest_accel_fish_id = -1
        self.speed_samples = 0
        self.total_speed = 0.0
        self.high_speed_count = 0  # Count of fish exceeding threshold
        
    def record_movement(self, fish_id: int, velocity: Vector2, acceleration: float):
        """Record movement stats for a single frame."""
        speed = velocity.length()
        
        # Track max speed
        if speed > self.max_speed:
            self.max_speed = speed
            self.fastest_fish_id = fish_id
            
        # Track max acceleration
        if acceleration > self.max_acceleration:
            self.max_acceleration = acceleration
            self.highest_accel_fish_id = fish_id
            
        # Track average
        self.total_speed += speed
        self.speed_samples += 1
        
        # Track high speed outliers (e.g. > 2.0 which is > base speed 1.5)
        if speed > 2.0:
            self.high_speed_count += 1
            
    def get_stats(self) -> Dict:
        """Get current statistics."""
        avg_speed = self.total_speed / self.speed_samples if self.speed_samples > 0 else 0.0
        return {
            "max_speed": self.max_speed,
            "max_acceleration": self.max_acceleration,
            "fastest_fish_id": self.fastest_fish_id,
            "highest_accel_fish_id": self.highest_accel_fish_id,
            "avg_speed": avg_speed,
            "high_speed_count": self.high_speed_count,
            "samples": self.speed_samples
        }
