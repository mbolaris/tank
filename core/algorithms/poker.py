"""Poker interaction behavior algorithms.

This module contains algorithms focused on poker-based fish interactions:
- PokerChallenger: Actively seeks out other fish for poker games
- PokerDodger: Avoids other fish to prevent poker games
- PokerGambler: Seeks poker aggressively when high energy
- SelectivePoker: Only engages in poker when conditions are favorable
- PokerOpportunist: Balances food seeking with poker opportunities
- PokerStrategist: Uses opponent modeling and position awareness
- PokerBluffer: Varies behavior unpredictably to confuse opponents
- PokerConservative: Risk-averse, plays only when highly favorable
"""

import random
from dataclasses import dataclass
from typing import Tuple

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.entities import Crab
from core.entities import Fish as FishClass


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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # First check for predators - survival comes first
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            # Flee from predator
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.2, direction.y * 1.2

        # Only seek poker if we have enough energy
        if fish.energy < self.parameters["min_energy_to_challenge"]:
            # Low energy - seek food instead
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
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
                direction = self._safe_normalize(nearest_fish.pos - fish.pos)
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # First check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
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
                avoid_dir = self._safe_normalize(fish.pos - other.pos)
                # Stronger avoidance for closer fish
                strength = (self.parameters["avoidance_radius"] - distance) / self.parameters[
                    "avoidance_radius"
                ]
                avoidance_vector = avoidance_vector + (avoid_dir * strength)
                fish_nearby += 1

        # If fish are nearby, move away from them
        if fish_nearby > 0:
            avoidance_vector = self._safe_normalize(avoidance_vector)
            speed = self.parameters["avoidance_speed"]

            # Still seek food while avoiding
            nearest_food = self._find_nearest_food(fish)
            if nearest_food and (nearest_food.pos - fish.pos).length() < 200:
                food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
                # Blend avoidance with food seeking
                final_dir = self._safe_normalize(avoidance_vector * 0.7 + food_dir * 0.3)
                return final_dir.x * speed, final_dir.y * speed

            return avoidance_vector.x * speed, avoidance_vector.y * speed

        # No fish nearby - focus on food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return (
                direction.x * self.parameters["food_priority"],
                direction.y * self.parameters["food_priority"],
            )

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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.2, direction.y * 1.2

        energy_ratio = fish.energy / fish.max_energy

        # If energy is high, gamble!
        if energy_ratio > self.parameters["high_energy_threshold"]:
            # Find all fish and challenge the nearest
            all_fish = fish.environment.get_agents_of_type(FishClass)
            other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

            if other_fish:
                nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
                direction = self._safe_normalize(nearest_fish.pos - fish.pos)
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
                    direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                    return direction.x * 0.8, direction.y * 0.8

        # Low energy - focus on food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.2, direction.y * 1.2

        energy_ratio = fish.energy / fish.max_energy

        # Only seek poker in the "sweet spot" energy range
        if self.parameters["min_energy_ratio"] < energy_ratio < self.parameters["max_energy_ratio"]:

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
                        direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                        speed = self.parameters["challenge_speed"]
                        return direction.x * speed, direction.y * speed

        # Default to food seeking
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
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
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.2, direction.y * 1.2

        # Look for both food and fish opportunities
        nearest_food = self._find_nearest_food(fish)
        all_fish = fish.environment.get_agents_of_type(FishClass)
        other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

        food_vector = Vector2(0, 0)
        poker_vector = Vector2(0, 0)

        # Calculate food attraction
        if nearest_food:
            food_dist = (nearest_food.pos - fish.pos).length()
            if food_dist > 0:
                food_vector = self._safe_normalize(nearest_food.pos - fish.pos)

        # Calculate poker attraction (nearest fish)
        if other_fish:
            nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
            poker_dist = (nearest_fish.pos - fish.pos).length()
            if poker_dist < self.parameters["opportunity_radius"] and poker_dist > 0:
                poker_vector = self._safe_normalize(nearest_fish.pos - fish.pos)

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
        final_vector = food_vector * food_weight + poker_vector * poker_weight
        if final_vector.length() > 0:
            final_vector = self._safe_normalize(final_vector)
            return final_vector.x, final_vector.y

        return 0, 0


@dataclass
class PokerStrategist(BehaviorAlgorithm):
    """Uses opponent modeling and strategic positioning for poker."""

    def __init__(self):
        super().__init__(
            algorithm_id="poker_strategist",
            parameters={
                "aggression_variance": random.uniform(0.1, 0.4),
                "position_awareness": random.uniform(0.5, 1.0),
                "opponent_tracking": random.uniform(0.3, 0.8),
                "min_energy_ratio": random.uniform(0.3, 0.6),
                "challenge_speed": random.uniform(0.7, 1.2),
            },
        )
        # Track recent poker encounters for opponent modeling
        self.recent_encounters = []
        self.max_memory = 5

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # Check for predators first
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.2, direction.y * 1.2

        energy_ratio = fish.energy / fish.max_energy

        # Only seek poker if energy is above minimum
        if energy_ratio < self.parameters["min_energy_ratio"]:
            # Low energy - seek food
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.9, direction.y * 0.9
            return 0, 0

        # Find potential poker opponents
        all_fish = fish.environment.get_agents_of_type(FishClass)
        other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

        if not other_fish:
            # No opponents - seek food
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.7, direction.y * 0.7
            return 0, 0

        # Strategic target selection based on position and energy
        best_target = None
        best_score = -float("inf")

        for target in other_fish:
            distance = (target.pos - fish.pos).length()
            if distance > 200:  # Too far
                continue

            # Calculate strategic score
            score = 0

            # Prefer closer targets (but not too close)
            optimal_distance = 100
            distance_score = 1.0 - abs(distance - optimal_distance) / 150.0
            score += distance_score * self.parameters["position_awareness"]

            # Prefer targets with similar or lower energy
            if hasattr(target, "energy") and target.energy is not None:
                energy_diff = fish.energy - target.energy
                if energy_diff > 0:  # We have more energy
                    score += 0.5 * self.parameters["opponent_tracking"]
                else:  # They have more energy - risky
                    score -= 0.3 * self.parameters["opponent_tracking"]

            # Add some randomness based on aggression variance
            score += random.uniform(
                -self.parameters["aggression_variance"], self.parameters["aggression_variance"]
            )

            if score > best_score:
                best_score = score
                best_target = target

        # If we found a good target, pursue it
        if best_target and best_score > 0:
            direction = self._safe_normalize(best_target.pos - fish.pos)
            speed = self.parameters["challenge_speed"]
            return direction.x * speed, direction.y * speed

        # No good targets - balance food and exploration
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * 0.8, direction.y * 0.8

        return random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)


@dataclass
class PokerBluffer(BehaviorAlgorithm):
    """Varies behavior unpredictably to confuse opponents."""

    def __init__(self):
        super().__init__(
            algorithm_id="poker_bluffer",
            parameters={
                "bluff_frequency": random.uniform(0.2, 0.6),
                "aggression_swing": random.uniform(0.4, 1.0),
                "unpredictability": random.uniform(0.3, 0.7),
                "min_energy_to_bluff": random.uniform(20.0, 40.0),
            },
        )
        # Track behavior state
        self.current_mode = "normal"  # 'normal', 'aggressive', 'passive'
        self.mode_timer = 0
        self.mode_duration = random.randint(50, 150)

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # Check for predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 120:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.2, direction.y * 1.2

        # Update behavior mode timer
        self.mode_timer += 1
        if self.mode_timer >= self.mode_duration:
            # Switch modes randomly
            if random.random() < self.parameters["bluff_frequency"]:
                modes = ["normal", "aggressive", "passive"]
                self.current_mode = random.choice(modes)
                self.mode_duration = random.randint(30, 100)
                self.mode_timer = 0

        # Don't bluff if energy is too low
        if fish.energy < self.parameters["min_energy_to_bluff"]:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x, direction.y
            return 0, 0

        # Find nearest fish
        all_fish = fish.environment.get_agents_of_type(FishClass)
        other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

        # Behavior based on current mode
        if self.current_mode == "aggressive":
            # Aggressively seek poker
            if other_fish:
                nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
                direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                speed = 1.0 + self.parameters["aggression_swing"]
                return direction.x * speed, direction.y * speed

        elif self.current_mode == "passive":
            # Avoid fish, focus on food
            nearest_food = self._find_nearest_food(fish)
            avoidance = Vector2(0, 0)

            # Calculate avoidance from nearby fish
            for other in other_fish:
                distance = (other.pos - fish.pos).length()
                if distance < 100 and distance > 0:
                    avoid_dir = self._safe_normalize(fish.pos - other.pos)
                    avoidance = avoidance + avoid_dir

            # Blend avoidance with food seeking
            if nearest_food and avoidance.length() > 0:
                food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
                avoidance = self._safe_normalize(avoidance)
                final_dir = self._safe_normalize(avoidance * 0.6 + food_dir * 0.4)
                return final_dir.x * 0.8, final_dir.y * 0.8
            elif nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.7, direction.y * 0.7

        else:  # normal mode
            # Balanced approach with unpredictability
            if other_fish and random.random() < 0.6:
                nearest_fish = min(other_fish, key=lambda f: (f.pos - fish.pos).length())
                distance = (nearest_fish.pos - fish.pos).length()

                if distance < 150:
                    direction = self._safe_normalize(nearest_fish.pos - fish.pos)
                    # Add unpredictable speed variation
                    speed = 0.8 + random.uniform(0, self.parameters["unpredictability"])
                    return direction.x * speed, direction.y * speed

            # Default to food seeking
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.8, direction.y * 0.8

        return random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4)


@dataclass
class PokerConservative(BehaviorAlgorithm):
    """Risk-averse poker player that only engages in highly favorable conditions."""

    def __init__(self):
        super().__init__(
            algorithm_id="poker_conservative",
            parameters={
                "min_energy_ratio": random.uniform(0.6, 0.85),
                "max_risk_tolerance": random.uniform(0.1, 0.3),
                "safety_distance": random.uniform(100.0, 180.0),
                "challenge_speed": random.uniform(0.5, 0.9),
                "energy_advantage_required": random.uniform(10.0, 30.0),
            },
        )

    @classmethod
    def random_instance(cls):
        return cls()

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # Always flee from predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < 150:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.3, direction.y * 1.3

        energy_ratio = fish.energy / fish.max_energy

        # Very conservative - only play poker when energy is high
        if energy_ratio < self.parameters["min_energy_ratio"]:
            # Focus entirely on food
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x, direction.y
            return 0, 0

        # Even with high energy, be very selective
        all_fish = fish.environment.get_agents_of_type(FishClass)
        other_fish = [f for f in all_fish if f.fish_id != fish.fish_id]

        best_target = None
        best_advantage = 0

        for other in other_fish:
            distance = (other.pos - fish.pos).length()

            # Only consider fish within safety distance
            if distance > self.parameters["safety_distance"]:
                continue

            # Check if we have energy advantage
            if hasattr(other, "energy") and other.energy is not None:
                energy_advantage = fish.energy - other.energy

                # Only challenge if we have significant energy advantage
                if energy_advantage > self.parameters["energy_advantage_required"]:
                    if energy_advantage > best_advantage:
                        best_advantage = energy_advantage
                        best_target = other

        # Only engage if we found a favorable matchup
        if best_target and random.random() > self.parameters["max_risk_tolerance"]:
            direction = self._safe_normalize(best_target.pos - fish.pos)
            speed = self.parameters["challenge_speed"]
            return direction.x * speed, direction.y * speed

        # Default to safe food seeking
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            # Check if any fish are too close while seeking food
            close_fish = [f for f in other_fish if (f.pos - fish.pos).length() < 80]
            if close_fish:
                # Avoid close fish while seeking food
                avoidance = Vector2(0, 0)
                for f in close_fish:
                    avoid_dir = self._safe_normalize(fish.pos - f.pos)
                    avoidance = avoidance + avoid_dir

                food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
                avoidance = self._safe_normalize(avoidance)
                final_dir = self._safe_normalize(avoidance * 0.5 + food_dir * 0.5)
                return final_dir.x * 0.8, final_dir.y * 0.8
            else:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return direction.x * 0.9, direction.y * 0.9

        return 0, 0
