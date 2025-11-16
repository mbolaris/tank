"""Poker interaction behavior algorithms.

This module contains algorithms focused on poker-based fish interactions:
- PokerChallenger: Actively seeks out other fish for poker games
- PokerDodger: Avoids other fish to prevent poker games
- PokerGambler: Seeks poker aggressively when high energy
- SelectivePoker: Only engages in poker when conditions are favorable
- PokerOpportunist: Balances food seeking with poker opportunities
"""

import random
import math
from typing import Tuple
from dataclasses import dataclass

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.entities import Fish as FishClass, Food, Crab


@dataclass
class PokerChallenger(BehaviorAlgorithm):
    """Actively seeks out other fish for poker games."""

    def __init__(self):
        super().__init__(
            algorithm_id="poker_challenger",
            parameters={
                "challenge_radius": random.uniform(100.0, 250.0),
                "challenge_speed": random.uniform(0.8, 1.3),
                "min_energy_to_challenge": random.uniform(15.0, 30.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # First check for predators - survival comes first
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            # Flee from predator
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2

        # Only seek poker if we have enough energy
        if fish.energy < self.parameters["min_energy_to_challenge"]:
            # Low energy - seek food instead
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food:
                direction = (nearest_food.pos - fish.pos).normalize()
                return direction.x * 0.8, direction.y * 0.8
            return 0, 0

        # Find nearest other fish within challenge radius
        all_fish = fish.environment.get_agents_of_type(FishClass)
        other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

        if other_fish:
            # Find closest fish
            nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
            distance = (nearest_fish.pos - fish.pos).length()

            if distance < self.parameters["challenge_radius"]:
                # Move toward the fish for poker
                direction = (nearest_fish.pos - fish.pos).normalize()
                speed = self.parameters["challenge_speed"]
                return direction.x * speed, direction.y * speed

        # No fish nearby - wander
        return random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)


@dataclass
class PokerDodger(BehaviorAlgorithm):
    """Avoids other fish to prevent poker games."""

    def __init__(self):
        super().__init__(
            algorithm_id="poker_dodger",
            parameters={
                "avoidance_radius": random.uniform(80.0, 150.0),
                "avoidance_speed": random.uniform(0.7, 1.1),
                "food_priority": random.uniform(0.6, 1.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # First check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2

        # Check for nearby fish to avoid
        all_fish = fish.environment.get_agents_of_type(FishClass)
        other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

        # Calculate avoidance vector
        avoidance_vector = Vector2(0, 0)
        fish_nearby = 0

        for other in other_fish:
            distance = (other.pos - fish.pos).length()
            if distance < self.parameters["avoidance_radius"] and distance > 0:
                # Avoid this fish
                avoid_dir = (fish.pos - other.pos).normalize()
                # Stronger avoidance for closer fish
                strength = (self.parameters["avoidance_radius"] - distance) / self.parameters["avoidance_radius"]
                avoidance_vector = avoidance_vector + (avoid_dir * strength)
                fish_nearby += 1

        # If fish are nearby, move away from them
        if fish_nearby > 0:
            avoidance_vector = avoidance_vector.normalize()
            speed = self.parameters["avoidance_speed"]

            # Still seek food while avoiding
            nearest_food = self._find_nearest(fish, Food)
            if nearest_food and (nearest_food.pos - fish.pos).length() < 200:
                food_dir = (nearest_food.pos - fish.pos).normalize()
                # Blend avoidance with food seeking
                final_dir = (avoidance_vector * 0.7 + food_dir * 0.3).normalize()
                return final_dir.x * speed, final_dir.y * speed

            return avoidance_vector.x * speed, avoidance_vector.y * speed

        # No fish nearby - focus on food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * self.parameters["food_priority"], direction.y * self.parameters["food_priority"]

        return 0, 0


@dataclass
class PokerGambler(BehaviorAlgorithm):
    """Seeks poker aggressively when high energy."""

    def __init__(self):
        super().__init__(
            algorithm_id="poker_gambler",
            parameters={
                "high_energy_threshold": random.uniform(0.6, 0.9),
                "challenge_speed": random.uniform(1.0, 1.5),
                "risk_tolerance": random.uniform(0.3, 0.8),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2

        energy_ratio = fish.energy / fish.max_energy

        # If energy is high, gamble!
        if energy_ratio > self.parameters["high_energy_threshold"]:
            # Find all fish and challenge the nearest
            all_fish = fish.environment.get_agents_of_type(FishClass)
            other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

            if other_fish:
                nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
                direction = (nearest_fish.pos - fish.pos).normalize()
                speed = self.parameters["challenge_speed"]
                return direction.x * speed, direction.y * speed

        # If energy is medium, balance poker with food
        elif energy_ratio > 0.3:
            # 50/50 chance between seeking fish or food
            if random.random() < 0.5:
                all_fish = fish.environment.get_agents_of_type(FishClass)
                other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]
                if other_fish:
                    nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
                    direction = (nearest_fish.pos - fish.pos).normalize()
                    return direction.x * 0.8, direction.y * 0.8

        # Low energy - focus on food
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x, direction.y

        return 0, 0


@dataclass
class SelectivePoker(BehaviorAlgorithm):
    """Only engages in poker when conditions are favorable."""

    def __init__(self):
        super().__init__(
            algorithm_id="selective_poker",
            parameters={
                "min_energy_ratio": random.uniform(0.4, 0.7),
                "max_energy_ratio": random.uniform(0.7, 0.95),
                "challenge_speed": random.uniform(0.6, 1.0),
                "selectivity": random.uniform(0.5, 0.9),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2

        energy_ratio = fish.energy / fish.max_energy

        # Only seek poker in the "sweet spot" energy range
        if (self.parameters["min_energy_ratio"] < energy_ratio <
            self.parameters["max_energy_ratio"]):

            # Be selective - only challenge sometimes
            if random.random() < self.parameters["selectivity"]:
                all_fish = fish.environment.get_agents_of_type(FishClass)
                other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

                if other_fish:
                    # Find nearest fish
                    nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
                    distance = (nearest_fish.pos - fish.pos).length()

                    # Only challenge if reasonably close
                    if distance < 150:
                        direction = (nearest_fish.pos - fish.pos).normalize()
                        speed = self.parameters["challenge_speed"]
                        return direction.x * speed, direction.y * speed

        # Default to food seeking
        nearest_food = self._find_nearest(fish, Food)
        if nearest_food:
            direction = (nearest_food.pos - fish.pos).normalize()
            return direction.x * 0.9, direction.y * 0.9

        return 0, 0


@dataclass
class PokerOpportunist(BehaviorAlgorithm):
    """Balances food seeking with poker opportunities."""

    def __init__(self):
        super().__init__(
            algorithm_id="poker_opportunist",
            parameters={
                "poker_weight": random.uniform(0.3, 0.7),
                "food_weight": random.uniform(0.3, 0.7),
                "opportunity_radius": random.uniform(80.0, 150.0),
            }
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: 'Fish') -> Tuple[float, float]:
        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = (fish.pos - nearest_predator.pos).normalize()
            return direction.x * 1.2, direction.y * 1.2

        # Look for both food and fish opportunities
        nearest_food = self._find_nearest(fish, Food)
        all_fish = fish.environment.get_agents_of_type(FishClass)
        other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

        food_vector = Vector2(0, 0)
        poker_vector = Vector2(0, 0)

        # Calculate food attraction
        if nearest_food:
            food_dist = (nearest_food.pos - fish.pos).length()
            if food_dist > 0:
                food_vector = (nearest_food.pos - fish.pos).normalize()

        # Calculate poker attraction (nearest fish)
        if other_fish:
            nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
            poker_dist = (nearest_fish.pos - fish.pos).length()
            if poker_dist < self.parameters["opportunity_radius"] and poker_dist > 0:
                poker_vector = (nearest_fish.pos - fish.pos).normalize()

        # Blend the two behaviors based on weights and energy
        energy_ratio = fish.energy / fish.max_energy

        # Adjust weights based on energy
        if energy_ratio < 0.3:
            # Low energy - prioritize food
            food_weight = 0.8
            poker_weight = 0.2
        else:
            food_weight = self.parameters["food_weight"]
            poker_weight = self.parameters["poker_weight"]

        # Combine vectors
        final_vector = (food_vector * food_weight + poker_vector * poker_weight)
        if final_vector.length() > 0:
            final_vector = final_vector.normalize()
            return final_vector.x, final_vector.y

        return 0, 0
