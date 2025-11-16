"""Energy management behavior algorithms.

This module contains 8 algorithms focused on managing energy expenditure:
- EnergyConserver: Minimize movement to conserve energy
- BurstSwimmer: Alternate between bursts of activity and rest
- OpportunisticRester: Rest when no food or threats nearby
- EnergyBalancer: Balance energy expenditure with reserves
- SustainableCruiser: Maintain steady, sustainable pace
- StarvationPreventer: Prioritize food when energy gets low
- MetabolicOptimizer: Adjust activity based on metabolic efficiency
- AdaptivePacer: Adapt speed based on current energy and environment
"""

import random
import math
import time
from typing import Tuple
from dataclasses import dataclass

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.entities import Food, Crab, Fish as FishClass


@dataclass
class EnergyConserver(BehaviorAlgorithm):
    """Minimize movement to conserve energy."""

    def __init__(self):
        super().__init__(
            algorithm_id="energy_conserver",
            parameters={
                "activity_threshold": random.uniform(0.4, 0.7),
                "rest_speed": random.uniform(0.1, 0.3),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        energy_ratio = fish.energy / fish.max_energy

        # Check for immediate threats
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 100:
            # Must flee even if conserving energy
            direction = (fish.pos - nearest_predator.pos).normalize()
            # Slower flee when low energy (realistic)
            flee_speed = 0.8 + energy_ratio * 0.5
            return direction.x * flee_speed, direction.y * flee_speed

        # Only pursue very close food when in conservation mode
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            # Only move for food if it's very close or energy is critical
            if food_distance < 40 or energy_ratio < 0.25:
                direction = (nearest_food.pos - fish.pos).normalize()
                # Slow approach to conserve energy
                return direction.x * self.parameters["rest_speed"], direction.y * self.parameters["rest_speed"]

        # Rest mode - minimal movement
        return 0, 0


@dataclass
class BurstSwimmer(BehaviorAlgorithm):
    """Alternate between bursts of activity and rest."""

    def __init__(self):
        super().__init__(
            algorithm_id="burst_swimmer",
            parameters={
                "burst_duration": random.uniform(30, 90),
                "rest_duration": random.uniform(60, 120),
                "burst_speed": random.uniform(1.2, 1.6),
            }
        )
        self.cycle_timer = 0
        self.is_bursting = True

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        energy_ratio = fish.energy / fish.max_energy

        # Check environment
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest(fish, Food)

        predator_nearby = nearest_predator and (nearest_predator.pos - fish.pos).length() < 150
        food_nearby = nearest_food and (nearest_food.pos - fish.pos).length() < 100

        self.cycle_timer += 1

        # Interrupt cycle for emergencies
        if predator_nearby and not self.is_bursting:
            # Emergency burst to escape
            self.is_bursting = True
            self.cycle_timer = 0

        # Adjust cycle based on energy
        burst_duration = self.parameters["burst_duration"]
        rest_duration = self.parameters["rest_duration"]

        if energy_ratio < 0.3:
            # Low energy - shorter bursts, longer rest
            burst_duration *= 0.7
            rest_duration *= 1.3
        elif energy_ratio > 0.7:
            # High energy - longer bursts
            burst_duration *= 1.2
            rest_duration *= 0.8

        if self.is_bursting and self.cycle_timer > burst_duration:
            self.is_bursting = False
            self.cycle_timer = 0
        elif not self.is_bursting and self.cycle_timer > rest_duration:
            # Only burst if there's a reason (food, exploration, or good energy)
            if food_nearby or energy_ratio > 0.5:
                self.is_bursting = True
                self.cycle_timer = 0

        if self.is_bursting:
            # Directed burst movement
            if predator_nearby:
                # Burst away from predator
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * self.parameters["burst_speed"], direction.y * self.parameters["burst_speed"]
            elif food_nearby:
                # Burst toward food
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["burst_speed"], direction.y * self.parameters["burst_speed"]
            else:
                # Exploration burst - vary direction
                angle = self.cycle_timer * 0.1
                vx = math.cos(angle) * self.parameters["burst_speed"]
                vy = math.sin(angle) * self.parameters["burst_speed"] * 0.5
                return vx, vy
        else:
            # Resting - minimal drift
            return 0, 0


@dataclass
class OpportunisticRester(BehaviorAlgorithm):
    """Rest when no food or threats nearby."""

    def __init__(self):
        super().__init__(
            algorithm_id="opportunistic_rester",
            parameters={
                "safe_radius": random.uniform(100, 200),
                "active_speed": random.uniform(0.5, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        # Check for nearby stimuli
        foods = fish.environment.get_agents_of_type(Food)
        predators = fish.environment.get_agents_of_type(Crab)

        has_nearby_food = any((f.pos - fish.pos).length() < self.parameters["safe_radius"] for f in foods)
        has_nearby_threat = any((p.pos - fish.pos).length() < self.parameters["safe_radius"] for p in predators)

        if has_nearby_food or has_nearby_threat:
            return self.parameters["active_speed"], 0
        return 0, 0


@dataclass
class EnergyBalancer(BehaviorAlgorithm):
    """Balance energy expenditure with reserves."""

    def __init__(self):
        super().__init__(
            algorithm_id="energy_balancer",
            parameters={
                "min_energy_ratio": random.uniform(0.3, 0.5),
                "max_energy_ratio": random.uniform(0.7, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy

        # Scale activity by energy level
        if energy_ratio < self.parameters["min_energy_ratio"]:
            activity = 0.2
        elif energy_ratio > self.parameters["max_energy_ratio"]:
            activity = 1.0
        else:
            # Linear interpolation
            activity = 0.2 + 0.8 * ((energy_ratio - self.parameters["min_energy_ratio"]) /
                                   (self.parameters["max_energy_ratio"] - self.parameters["min_energy_ratio"]))

        return activity, 0


@dataclass
class SustainableCruiser(BehaviorAlgorithm):
    """Maintain steady, sustainable pace."""

    def __init__(self):
        super().__init__(
            algorithm_id="sustainable_cruiser",
            parameters={
                "cruise_speed": random.uniform(0.4, 0.7),
                "consistency": random.uniform(0.7, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Just maintain steady pace
        return self.parameters["cruise_speed"] * self.parameters["consistency"], 0


@dataclass
class StarvationPreventer(BehaviorAlgorithm):
    """Prioritize food when energy gets low."""

    def __init__(self):
        super().__init__(
            algorithm_id="starvation_preventer",
            parameters={
                "critical_threshold": random.uniform(0.2, 0.4),
                "urgency_multiplier": random.uniform(1.3, 1.8),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        energy_ratio = fish.energy / fish.max_energy
        if energy_ratio < self.parameters["critical_threshold"]:
            # Emergency food seeking
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * self.parameters["urgency_multiplier"], direction.y * self.parameters["urgency_multiplier"]
        return 0, 0


@dataclass
class MetabolicOptimizer(BehaviorAlgorithm):
    """Adjust activity based on metabolic efficiency."""

    def __init__(self):
        super().__init__(
            algorithm_id="metabolic_optimizer",
            parameters={
                "efficiency_threshold": random.uniform(0.5, 0.8),
                "low_efficiency_speed": random.uniform(0.2, 0.4),
                "high_efficiency_speed": random.uniform(0.7, 1.1),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Use genome metabolism as efficiency indicator
        efficiency = 1.0 / fish.genome.metabolism_rate if fish.genome.metabolism_rate > 0 else 1.0

        if efficiency > self.parameters["efficiency_threshold"]:
            speed = self.parameters["high_efficiency_speed"]
        else:
            speed = self.parameters["low_efficiency_speed"]

        return speed, 0


@dataclass
class AdaptivePacer(BehaviorAlgorithm):
    """Adapt speed based on current energy and environment."""

    def __init__(self):
        super().__init__(
            algorithm_id="adaptive_pacer",
            parameters={
                "base_speed": random.uniform(0.5, 0.8),
                "energy_influence": random.uniform(0.3, 0.7),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:

        energy_ratio = fish.energy / fish.max_energy

        # Base speed influenced by energy
        base_speed = self.parameters["base_speed"] * (1 + (energy_ratio - 0.5) * self.parameters["energy_influence"])

        # Check environment for context
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest(fish, Food)

        vx, vy = 0, 0

        # Predator response
        if nearest_predator:
            pred_distance = (nearest_predator.pos - fish.pos).length()
            if pred_distance < 140:
                # Escape with pace proportional to energy and threat
                threat = 1.0 - (pred_distance / 140)
                escape_speed = base_speed * (1.5 + threat * 0.8)
                # Reduce if low energy
                if energy_ratio < 0.3:
                    escape_speed *= 0.7
                direction = (fish.pos - nearest_predator.pos).normalize()
                return direction.x * escape_speed, direction.y * escape_speed

        # Food seeking with adaptive pacing
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            hunger = 1.0 - energy_ratio

            # Only pursue if hungry enough or food is very close
            if hunger > 0.3 or food_distance < 60:
                # Pace based on distance and hunger
                pursuit_speed = base_speed * (0.7 + hunger * 0.6)
                # Speed up as we get closer
                if food_distance < 80:
                    pursuit_speed *= 1.3

                direction = (nearest_food.pos - fish.pos).normalize()
                vx = direction.x * pursuit_speed
                vy = direction.y * pursuit_speed

        # Social pacing - match nearby fish speeds
        if vx == 0 and vy == 0:
            allies = [f for f in fish.environment.get_agents_of_type(FishClass)
                     if f != fish and (f.pos - fish.pos).length() < 100]
            if allies:
                avg_vel = sum((f.vel for f in allies), Vector2()) / len(allies)
                if avg_vel.length() > 0:
                    avg_vel_normalized = avg_vel.normalize()
                    # Match their pace but adjusted by our energy
                    social_pace = base_speed * 0.8
                    vx = avg_vel_normalized.x * social_pace
                    vy = avg_vel_normalized.y * social_pace

        # Default gentle cruising if nothing else to do
        if vx == 0 and vy == 0:
            # Cruise in a gentle pattern
            t = time.time() * 0.3
            vx = math.cos(t) * base_speed * 0.6
            vy = math.sin(t * 0.5) * base_speed * 0.3

        return vx, vy
