"""Food-seeking behavior algorithms.

This module contains 12 algorithms focused on finding and pursuing food:
- GreedyFoodSeeker: Always move directly toward nearest food
- EnergyAwareFoodSeeker: Seek food more aggressively when energy is low
- OpportunisticFeeder: Only pursue food if it's close enough
- FoodQualityOptimizer: Prefer high-value food types
- AmbushFeeder: Wait in one spot for food to come close
- PatrolFeeder: Patrol in a pattern looking for food
- SurfaceSkimmer: Stay near surface to catch falling food
- BottomFeeder: Stay near bottom to catch sinking food
- ZigZagForager: Move in zigzag pattern to maximize food discovery
- CircularHunter: Circle around food before striking
- FoodMemorySeeker: Remember where food was found before
- CooperativeForager: Follow other fish to food sources
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

from core.algorithms.base import BehaviorAlgorithm, Vector2
from core.constants import (
    CHASE_DISTANCE_CRITICAL,
    CHASE_DISTANCE_LOW,
    CHASE_DISTANCE_SAFE_BASE,
    DANGER_WEIGHT_CRITICAL,
    DANGER_WEIGHT_LOW,
    DANGER_WEIGHT_NORMAL,
    FOOD_CIRCLING_APPROACH_DISTANCE,
    FOOD_MEMORY_RECORD_DISTANCE,
    FOOD_PURSUIT_RANGE_CLOSE,
    FOOD_PURSUIT_RANGE_DESPERATE,
    FOOD_PURSUIT_RANGE_EXTENDED,
    FOOD_PURSUIT_RANGE_NORMAL,
    FOOD_SAFETY_BONUS,
    FOOD_SAFETY_DISTANCE_RATIO,
    FOOD_SCORE_THRESHOLD_CRITICAL,
    FOOD_SCORE_THRESHOLD_LOW,
    FOOD_SCORE_THRESHOLD_NORMAL,
    FOOD_SPEED_BOOST_DISTANCE,
    FOOD_STRIKE_DISTANCE,
    FOOD_VELOCITY_THRESHOLD,
    PREDATOR_DANGER_ZONE_DIVISOR,
    PREDATOR_DANGER_ZONE_RADIUS,
    PREDATOR_DEFAULT_FAR_DISTANCE,
    PREDATOR_FLEE_DISTANCE_CAUTIOUS,
    PREDATOR_FLEE_DISTANCE_CONSERVATIVE,
    PREDATOR_FLEE_DISTANCE_DESPERATE,
    PREDATOR_FLEE_DISTANCE_NORMAL,
    PREDATOR_FLEE_DISTANCE_SAFE,
    PREDATOR_GUARDING_FOOD_DISTANCE,
    PREDATOR_PROXIMITY_THRESHOLD,
    PROXIMITY_BOOST_DIVISOR,
    PROXIMITY_BOOST_MULTIPLIER,
    SCREEN_HEIGHT,
    SOCIAL_FOLLOW_MAX_DISTANCE,
    SOCIAL_FOOD_PROXIMITY_THRESHOLD,
    SOCIAL_SIGNAL_DETECTION_RANGE,
    URGENCY_BOOST_CRITICAL,
    URGENCY_BOOST_LOW,
)
from core.entities import Crab, Food
from core.predictive_movement import predict_intercept_point, predict_falling_intercept
from core.world import World


@dataclass
class GreedyFoodSeeker(BehaviorAlgorithm):
    """Always move directly toward nearest food.

    Uses genetic hunting traits to affect behavior:
    - pursuit_aggression: How fast to chase moving food
    - prediction_skill: How well to predict food movement
    - hunting_stamina: How long to sustain high-speed pursuit
    """

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="greedy_food_seeker",
            parameters={
                "speed_multiplier": rng.uniform(0.7, 1.3),
                "detection_range": rng.uniform(0.5, 1.0),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Use helper to check energy state (consolidates 3 method calls)
        is_critical, is_low, energy_ratio = self._get_energy_state(fish)

        # Use helper to check for predators and flee if necessary
        should_flee, flee_x, flee_y = self._should_flee_predator(fish)
        if should_flee:
            return flee_x, flee_y

        # Get hunting traits from genome (with defaults if not present)
        pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
        prediction_skill = fish.genome.behavioral.prediction_skill.value

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()

            # IMPROVEMENT: Smarter chase distance calculation
            # Higher pursuit_aggression = willing to chase farther
            base_chase = CHASE_DISTANCE_SAFE_BASE * (1.0 + pursuit_aggression * 0.5)
            if is_critical:
                max_chase_distance = CHASE_DISTANCE_CRITICAL
            elif is_low:
                max_chase_distance = CHASE_DISTANCE_LOW
            else:
                max_chase_distance = base_chase + (energy_ratio * base_chase * 0.5)

            if distance < max_chase_distance:
                # Use predictive interception for moving food
                # Better prediction_skill = more accurate interception
                target_pos = nearest_food.pos
                
                # Check for moving food (falling or swimming)
                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0.01:
                    is_accelerating = False
                    acceleration = 0.0
                    
                    # Check for acceleration (falling food)
                    if hasattr(nearest_food, "food_properties"):
                        from core.constants import FOOD_SINK_ACCELERATION
                        sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                        acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                        if acceleration > 0 and nearest_food.vel.y >= 0:
                            is_accelerating = True
                    
                    # Calculate optimal intercept point
                    intercept_point = None
                    if is_accelerating:
                        intercept_point, _ = predict_falling_intercept(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                        )
                    else:
                        intercept_point, _ = predict_intercept_point(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                        )
                    
                    if intercept_point and prediction_skill > 0.3:
                        # Blend toward optimal intercept based on skill
                        # FIX: Changed blending logic to favor intercept more strongly
                        # Even moderate skill should commit to the prediction
                        skill_factor = 0.2 + (prediction_skill * 0.8) # 0.3 -> 0.44, 0.9 -> 0.92
                        
                        target_pos = Vector2(
                            nearest_food.pos.x * (1 - skill_factor) + intercept_point.x * skill_factor,
                            nearest_food.pos.y * (1 - skill_factor) + intercept_point.y * skill_factor,
                        )
                else:
                    target_pos = nearest_food.pos

                direction = self._safe_normalize(target_pos - fish.pos)

                # Speed based on urgency, distance, and HUNTING TRAITS
                base_speed = self.parameters["speed_multiplier"]

                # Speed up when closer to food
                proximity_boost = (
                    1.0 - min(distance / PROXIMITY_BOOST_DIVISOR, 1.0)
                ) * PROXIMITY_BOOST_MULTIPLIER

                # Urgency boost when low/critical energy
                urgency_boost = (
                    URGENCY_BOOST_CRITICAL if is_critical else (URGENCY_BOOST_LOW if is_low else 0)
                )

                # NEW: Hunting traits affect speed
                # pursuit_aggression adds speed when chasing
                # hunting_stamina affects whether we maintain speed (simplified for now)
                pursuit_boost = pursuit_aggression * 0.3  # Up to 30% speed boost

                speed = base_speed * (1.0 + proximity_boost + urgency_boost + pursuit_boost)

                # Remember successful food locations
                if hasattr(fish, "memory_system") and distance < FOOD_MEMORY_RECORD_DISTANCE:
                    from core.fish_memory import MemoryType

                    fish.memory_system.add_memory(
                        MemoryType.FOOD_LOCATION, nearest_food.pos, strength=0.8
                    )

                return direction.x * speed, direction.y * speed

        # Use enhanced memory system if no food found
        if (is_critical or is_low) and hasattr(fish, "memory_system"):
            from core.fish_memory import MemoryType

            best_food_memory = fish.memory_system.get_best_memory(MemoryType.FOOD_LOCATION)
            if best_food_memory:
                direction = self._safe_normalize(best_food_memory.location - fish.pos)
                return direction.x * 0.9, direction.y * 0.9

        return 0, 0


@dataclass
class EnergyAwareFoodSeeker(BehaviorAlgorithm):
    """Seek food more aggressively when energy is low."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="energy_aware_food_seeker",
            parameters={
                "urgency_threshold": rng.uniform(0.3, 0.7),
                "calm_speed": rng.uniform(0.3, 0.6),
                "urgent_speed": rng.uniform(0.8, 1.2),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # IMPROVEMENT: Use new critical energy methods
        is_critical = fish.is_critical_energy()
        energy_ratio = fish.get_energy_ratio()

        # Get hunting traits
        pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
        hunting_stamina = fish.genome.behavioral.hunting_stamina.value

        # Check for predators - even urgent fish should avoid immediate danger
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (
            (nearest_predator.pos - fish.pos).length()
            if nearest_predator
            else PREDATOR_DEFAULT_FAR_DISTANCE
        )
        predator_nearby = predator_distance < PREDATOR_PROXIMITY_THRESHOLD

        # IMPROVEMENT: Critical energy mode - must find food NOW
        if is_critical:
            # Desperate - must eat even with some predator risk
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                # If predator is blocking food, try to path around it
                if predator_nearby:
                    predator_to_food = (nearest_food.pos - nearest_predator.pos).length()
                    if predator_to_food < PREDATOR_GUARDING_FOOD_DISTANCE:
                        # Try perpendicular approach
                        to_food = (nearest_food.pos - fish.pos).normalize()
                        perp_x, perp_y = -to_food.y, to_food.x
                        return perp_x * 0.8, perp_y * 0.8
                direction = self._safe_normalize(nearest_food.pos - fish.pos)

                # Hunting traits boost speed
                trait_boost = pursuit_aggression * 0.4 + hunting_stamina * 0.2
                speed = self.parameters["urgent_speed"] * (1.0 + trait_boost)

                return (
                    direction.x * speed,
                    direction.y * speed,
                )

        # Flee if predator too close
        if predator_nearby:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            # Graduated urgency based on energy level
            if energy_ratio < self.parameters["urgency_threshold"]:
                speed = self.parameters["urgent_speed"]
            else:
                # Scale speed based on energy - conserve when high energy
                speed = self.parameters["calm_speed"] + (1.0 - energy_ratio) * 0.3

            # Apply hunting stamina bonus - maintain higher speed longer
            if hunting_stamina > 0.6:
                speed *= (1.0 + (hunting_stamina - 0.6) * 0.5)

            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * speed, direction.y * speed
        return 0, 0


@dataclass
class OpportunisticFeeder(BehaviorAlgorithm):
    """Only pursue food if it's close enough - IMPROVED to avoid starvation."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="opportunistic_feeder",
            parameters={
                "max_pursuit_distance": rng.uniform(150, 300),  # INCREASED from 50-200
                "speed": rng.uniform(0.9, 1.3),  # INCREASED from 0.6-1.0
                "exploration_speed": rng.uniform(0.5, 0.8),  # NEW: explore when idle
            },
        )
        self.exploration_angle = rng.uniform(0, 2 * math.pi)
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy state
        is_critical = fish.energy / fish.max_energy < 0.3
        is_low = fish.energy / fish.max_energy < 0.5

        # IMPROVEMENT: Flee from predators
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            flee_threshold = (
                PREDATOR_FLEE_DISTANCE_DESPERATE
                if is_critical
                else PREDATOR_FLEE_DISTANCE_CONSERVATIVE
            )
            if pred_dist < flee_threshold:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            # IMPROVEMENT: Expand pursuit when hungry
            max_dist = self.parameters["max_pursuit_distance"]
            if is_critical:
                max_dist *= 2  # Desperate: chase much further
            elif is_low:
                max_dist *= 1.5

            if distance < max_dist:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                # IMPROVEMENT: Speed up when close and when hungry
                speed = self.parameters["speed"]

                # Hunting traits
                pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
                speed *= (1.0 + pursuit_aggression * 0.3)

                if distance < FOOD_SPEED_BOOST_DISTANCE:
                    speed *= 1.3
                if is_critical:
                    speed *= 1.2
                return direction.x * speed, direction.y * speed

        # IMPROVEMENT: Don't just idle - explore!
        if is_critical or is_low:
            self.exploration_angle += random.uniform(-0.4, 0.4)
            ex_speed = self.parameters["exploration_speed"] * (1.5 if is_critical else 1.0)
            return (
                math.cos(self.exploration_angle) * ex_speed,
                math.sin(self.exploration_angle) * ex_speed,
            )

        return 0, 0


@dataclass
class FoodQualityOptimizer(BehaviorAlgorithm):
    """Prefer high-value food types."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="food_quality_optimizer",
            parameters={
                "quality_weight": rng.uniform(0.5, 1.0),
                "distance_weight": rng.uniform(0.3, 0.7),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # IMPROVEMENT: Use new critical energy methods for smarter decisions
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        fish.get_energy_ratio()

        # Check predators first - but be less cautious when critically low energy
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (
            (nearest_predator.pos - fish.pos).length()
            if nearest_predator
            else PREDATOR_DEFAULT_FAR_DISTANCE
        )

        # In critical energy, only flee if predator is very close
        flee_threshold = (
            PREDATOR_FLEE_DISTANCE_DESPERATE
            if is_critical
            else (PREDATOR_FLEE_DISTANCE_CAUTIOUS if is_low else PREDATOR_FLEE_DISTANCE_CONSERVATIVE)
        )
        if nearest_predator and predator_distance < flee_threshold:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            flee_speed = 1.2 if is_critical else 1.4  # Conserve energy even when fleeing
            return direction.x * flee_speed, direction.y * flee_speed

        # Use World Protocol
        env: World = fish.environment
        foods = env.get_agents_of_type(Food)
        best_food = None
        best_score = -float("inf")

        # IMPROVEMENT: Also consider remembered food locations if no food visible
        remembered_locations = (
            fish.get_remembered_food_locations()
            if hasattr(fish, "get_remembered_food_locations")
            else []
        )

        for food in foods:
            distance = (food.pos - fish.pos).length()
            quality = food.get_energy_value()

            # Check if predator is near this food (danger score)
            danger_score = 0
            if nearest_predator:
                predator_food_dist = (nearest_predator.pos - food.pos).length()
                if predator_food_dist < PREDATOR_DANGER_ZONE_RADIUS:
                    danger_score = (
                        PREDATOR_DANGER_ZONE_RADIUS - predator_food_dist
                    ) / PREDATOR_DANGER_ZONE_DIVISOR

            # IMPROVEMENT: Smarter danger weighting based on energy state
            # Critical energy: mostly ignore danger
            # Low energy: some caution
            # Normal energy: high caution
            if is_critical:
                danger_weight = DANGER_WEIGHT_CRITICAL
            elif is_low:
                danger_weight = DANGER_WEIGHT_LOW
            else:
                danger_weight = DANGER_WEIGHT_NORMAL

            # IMPROVEMENT: Increase quality weight when low energy
            quality_weight = self.parameters["quality_weight"] * (1.5 if is_low else 1.0)
            distance_weight = self.parameters["distance_weight"] * (1.3 if is_critical else 1.0)

            # Calculate value: high quality, close distance, low danger
            score = (
                quality * quality_weight - distance * distance_weight - danger_score * danger_weight
            )

            # IMPROVEMENT: Bonus for food that's closer than predator
            if nearest_predator and distance < predator_distance * FOOD_SAFETY_DISTANCE_RATIO:
                score += FOOD_SAFETY_BONUS

            if score > best_score:
                best_score = score
                best_food = food

        # IMPROVEMENT: Lower threshold for pursuing food when critically low
        min_score_threshold = (
            FOOD_SCORE_THRESHOLD_CRITICAL
            if is_critical
            else (FOOD_SCORE_THRESHOLD_LOW if is_low else FOOD_SCORE_THRESHOLD_NORMAL)
        )

        if best_food and best_score > min_score_threshold:
            distance_to_food = (best_food.pos - fish.pos).length()

            # Use prediction for moving food
            prediction_skill = fish.genome.behavioral.prediction_skill.value
            target_pos = best_food.pos

            target_pos = best_food.pos

            if hasattr(best_food, "vel") and best_food.vel.length() > 0.01:
                # Check for acceleration
                is_accelerating = False
                acceleration = 0.0
                if hasattr(best_food, "food_properties"):
                     from core.constants import FOOD_SINK_ACCELERATION
                     sink_multiplier = best_food.food_properties.get("sink_multiplier", 1.0)
                     acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                     if acceleration > 0 and best_food.vel.y >= 0:
                         is_accelerating = True

                intercept_point = None
                if is_accelerating:
                    intercept_point, _ = predict_falling_intercept(
                        fish.pos, fish.speed, best_food.pos, best_food.vel, acceleration
                    )
                else:
                    intercept_point, _ = predict_intercept_point(
                        fish.pos, fish.speed, best_food.pos, best_food.vel
                    )

                if intercept_point and prediction_skill > 0.3:
                     # Stronger commitment to prediction
                     skill_factor = 0.2 + (prediction_skill * 0.8)
                     target_pos = Vector2(
                        best_food.pos.x * (1 - skill_factor) + intercept_point.x * skill_factor,
                        best_food.pos.y * (1 - skill_factor) + intercept_point.y * skill_factor,
                    )

            direction = self._safe_normalize(target_pos - fish.pos)
            # IMPROVEMENT: Speed based on urgency and distance
            base_speed = 1.1 if is_critical else 0.9
            speed = base_speed + min(50 / max(distance_to_food, 1), 0.5)

            # Hunting traits boost
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed *= (1.0 + pursuit_aggression * 0.2)

            return direction.x * speed, direction.y * speed

        # IMPROVEMENT: If no good food found but have memories and critically low, go to memory
        if is_critical and remembered_locations:
            closest_memory = min(remembered_locations, key=lambda pos: (pos - fish.pos).length())
            direction = self._safe_normalize(closest_memory - fish.pos)
            return direction.x * 0.8, direction.y * 0.8

        return 0, 0


@dataclass
class AmbushFeeder(BehaviorAlgorithm):
    """Wait in one spot for food to come close."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="ambush_feeder",
            parameters={
                "strike_distance": rng.uniform(30, 80),
                "strike_speed": rng.uniform(1.0, 1.5),
                "patience": rng.uniform(0.5, 1.0),
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            if distance < self.parameters["strike_distance"]:
                # Prediction skill helps aim the strike
                prediction_skill = fish.genome.behavioral.prediction_skill.value
                target_pos = nearest_food.pos

                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0.01:
                     is_accelerating = False
                     acceleration = 0.0
                     if hasattr(nearest_food, "food_properties"):
                         from core.constants import FOOD_SINK_ACCELERATION
                         sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                         acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                         if acceleration > 0 and nearest_food.vel.y >= 0:
                             is_accelerating = True

                     if is_accelerating:
                         target_pos, _ = predict_falling_intercept(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                         )
                     else:
                         # Simple lead - now using intercept point properly
                         intercept_point, _ = predict_intercept_point(
                             fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                         )
                         if intercept_point:
                            # Blend based on skill - ambushers need good timing
                            skill_factor = 0.4 + (prediction_skill * 0.6)
                            target_pos = Vector2(
                                nearest_food.pos.x * (1 - skill_factor) + intercept_point.x * skill_factor,
                                nearest_food.pos.y * (1 - skill_factor) + intercept_point.y * skill_factor,
                            )

                direction = self._safe_normalize(target_pos - fish.pos)

                # Aggression boosts strike speed
                pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
                strike_speed = self.parameters["strike_speed"] * (1.0 + pursuit_aggression * 0.4)

                return (
                    direction.x * strike_speed,
                    direction.y * strike_speed,
                )
        return 0, 0


@dataclass
class PatrolFeeder(BehaviorAlgorithm):
    """Patrol in a pattern looking for food - IMPROVED with better detection."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="patrol_feeder",
            parameters={
                "patrol_radius": rng.uniform(100, 200),  # INCREASED from 50-150
                "patrol_speed": rng.uniform(0.8, 1.2),  # INCREASED from 0.5-1.0
                "food_priority": rng.uniform(1.0, 1.4),  # INCREASED from 0.6-1.0
            },
        )
        self.rng = rng
        self.patrol_center = None
        self.patrol_angle = rng.uniform(0, 2 * math.pi)

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy and predators
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # IMPROVEMENT: Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < PREDATOR_FLEE_DISTANCE_NORMAL:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        # Check for nearby food first - EXPANDED detection
        nearest_food = self._find_nearest_food(fish)
        detection_range = FOOD_PURSUIT_RANGE_DESPERATE if is_desperate else FOOD_PURSUIT_RANGE_NORMAL
        if nearest_food and (nearest_food.pos - fish.pos).length() < detection_range:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            # IMPROVEMENT: Faster when desperate
            speed = self.parameters["food_priority"] * (1.3 if is_desperate else 1.0)

            # Hunting traits
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed *= (1.0 + pursuit_aggression * 0.25)

            return direction.x * speed, direction.y * speed

        # Otherwise patrol - FASTER rotation
        if self.patrol_center is None:
            self.patrol_center = Vector2(fish.pos.x, fish.pos.y)

        self.patrol_angle += 0.15  # INCREASED from 0.05 for faster patrol
        target_x = (
            self.patrol_center.x + math.cos(self.patrol_angle) * self.parameters["patrol_radius"]
        )
        target_y = (
            self.patrol_center.y + math.sin(self.patrol_angle) * self.parameters["patrol_radius"]
        )
        direction = self._safe_normalize(Vector2(target_x, target_y) - fish.pos)
        # IMPROVEMENT: Patrol faster to cover more ground
        speed = self.parameters["patrol_speed"] * (1.3 if is_desperate else 1.0)
        return direction.x * speed, direction.y * speed


@dataclass
class SurfaceSkimmer(BehaviorAlgorithm):
    """Stay near surface to catch falling food - IMPROVED for better survival."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="surface_skimmer",
            parameters={
                "preferred_depth": rng.uniform(0.1, 0.25),  # 10-25% from top
                "horizontal_speed": rng.uniform(0.8, 1.3),  # INCREASED from 0.5-1.0
                "dive_for_food_threshold": rng.uniform(150, 250),  # NEW: will dive for food
            },
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy and threats
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # IMPROVEMENT: Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < PREDATOR_FLEE_DISTANCE_CONSERVATIVE:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]

        # Look for food - IMPROVED to actively pursue
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            food_dist = (nearest_food.pos - fish.pos).length()
            # IMPROVEMENT: Dive for food if desperate or food is reasonably close
            if is_desperate or food_dist < self.parameters["dive_for_food_threshold"]:
                # Go directly for food, abandoning surface position

                # Use prediction for diving
                prediction_skill = fish.genome.behavioral.prediction_skill.value
                target_pos = nearest_food.pos
                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0:
                     # Using acceleration-aware prediction for better diving
                     is_accelerating = False
                     acceleration = 0.0
                     if hasattr(nearest_food, "food_properties"):
                         from core.constants import FOOD_SINK_ACCELERATION
                         sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                         acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                         if acceleration > 0 and nearest_food.vel.y >= 0:
                             is_accelerating = True
                     
                     if is_accelerating:
                         intercept_point, _ = predict_falling_intercept(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                         )
                         # High commitment to intercept for skimmers diving
                         target_pos = intercept_point
                     else:
                         target_pos = nearest_food.pos + nearest_food.vel * (prediction_skill * 10)

                direction = self._safe_normalize(target_pos - fish.pos)
                speed = 1.2 if is_desperate else 1.0

                # Aggression boosts dive speed
                pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
                speed *= (1.0 + pursuit_aggression * 0.3)

                return direction.x * speed, direction.y * speed
            else:
                # Move horizontally toward food while maintaining depth
                vx = (nearest_food.pos.x - fish.pos.x) / 80  # FASTER horizontal tracking
                vy = (target_y - fish.pos.y) / 100
                # IMPROVEMENT: Speed up horizontal movement
                vx *= 1.5
                return vx, vy
        else:
            # No food visible - patrol surface actively
            vy = (target_y - fish.pos.y) / 100
            # IMPROVEMENT: Active patrol instead of random flip
            vx = self.parameters["horizontal_speed"]
            # Change direction periodically
            rng = getattr(self, "rng", None) or random
            if rng.random() < 0.02:  # 2% chance per frame to reverse
                self.parameters["horizontal_speed"] *= -1
            return vx, vy


@dataclass
class BottomFeeder(BehaviorAlgorithm):
    """Stay near bottom to catch sinking food."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="bottom_feeder",
            parameters={
                "preferred_depth": rng.uniform(0.7, 0.9),  # 70-90% from top
                "search_speed": rng.uniform(0.4, 0.8),
            },
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        target_y = SCREEN_HEIGHT * self.parameters["preferred_depth"]
        vy = (target_y - fish.pos.y) / 100

        nearest_food = self._find_nearest_food(fish)
        vx = 0
        if nearest_food:
            # Prediction helps catch sinking food
            prediction_skill = fish.genome.behavioral.prediction_skill.value
            target_x = nearest_food.pos.x
            if hasattr(nearest_food, "vel"):
                 target_x += nearest_food.vel.x * (prediction_skill * 20)

            vx = (target_x - fish.pos.x) / 100

            # Aggression boosts tracking speed
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            vx *= (1.0 + pursuit_aggression * 0.5)
        else:
            rng = getattr(self, "rng", None) or random
            vx = (
                self.parameters["search_speed"]
                if rng.random() > 0.5
                else -self.parameters["search_speed"]
            )

        return vx, vy


@dataclass
class ZigZagForager(BehaviorAlgorithm):
    """Move in zigzag pattern to maximize food discovery."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="zigzag_forager",
            parameters={
                "zigzag_frequency": rng.uniform(0.02, 0.08),
                "zigzag_amplitude": rng.uniform(0.5, 1.2),
                "forward_speed": rng.uniform(0.6, 1.0),
            },
        )
        self.zigzag_phase = rng.uniform(0, 2 * math.pi)
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check for nearby food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food and (nearest_food.pos - fish.pos).length() < FOOD_PURSUIT_RANGE_CLOSE:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)

            # Aggression boosts chase speed
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed_boost = 1.0 + pursuit_aggression * 0.3

            return direction.x * speed_boost, direction.y * speed_boost

        # Zigzag movement
        self.zigzag_phase += self.parameters["zigzag_frequency"]
        vx = self.parameters["forward_speed"]
        vy = math.sin(self.zigzag_phase) * self.parameters["zigzag_amplitude"]

        return vx, vy


@dataclass
class CircularHunter(BehaviorAlgorithm):
    """Circle around food before striking - IMPROVED for better survival."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="circular_hunter",
            parameters={
                "circle_radius": rng.uniform(50, 80),
                "approach_speed": rng.uniform(0.9, 1.2),
                "strike_distance": rng.uniform(60, 100),
                "exploration_speed": rng.uniform(0.6, 0.9),
            },
        )
        self.circle_angle = 0
        self.exploration_direction = rng.uniform(0, 2 * math.pi)
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Check energy status for smarter decisions
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3
        is_low_energy = energy_ratio < 0.5

        # Predator check - flee distance based on energy
        nearest_predator = self._find_nearest(fish, Crab)
        flee_distance = PREDATOR_FLEE_DISTANCE_DESPERATE if is_desperate else PREDATOR_FLEE_DISTANCE_NORMAL
        if nearest_predator and (nearest_predator.pos - fish.pos).length() < flee_distance:
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            # Conserve energy when desperate
            flee_speed = 1.2 if is_desperate else 1.4
            return direction.x * flee_speed, direction.y * flee_speed

        nearest_food = self._find_nearest_food(fish)
        if not nearest_food:
            # CRITICAL FIX: Actively explore instead of stopping!
            # Slowly change direction for more exploration coverage
            rng = getattr(self, "rng", None) or random
            self.exploration_direction += rng.uniform(-0.3, 0.3)
            exploration_vec = Vector2(
                math.cos(self.exploration_direction), math.sin(self.exploration_direction)
            )
            speed = self.parameters["exploration_speed"]
            return exploration_vec.x * speed, exploration_vec.y * speed

        distance = (nearest_food.pos - fish.pos).length()

        # If food is moving (has velocity), predict its position
        food_future_pos = nearest_food.pos
        if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0.01:
             is_accelerating = False
             acceleration = 0.0
             if hasattr(nearest_food, "food_properties"):
                 from core.constants import FOOD_SINK_ACCELERATION
                 sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                 acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                 if acceleration > 0 and nearest_food.vel.y >= 0:
                     is_accelerating = True

             if is_accelerating:
                 food_future_pos, _ = predict_falling_intercept(
                    fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                 )
             else:
                 intercept_point, _ = predict_intercept_point(
                     fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                 )
                 if intercept_point:
                     food_future_pos = intercept_point
                 else:
                     food_future_pos = nearest_food.pos + nearest_food.vel * 10

        # IMPROVEMENT: Skip circling when desperate or very hungry
        # Go straight for food when energy is low!
        if is_desperate or is_low_energy:
            direction = self._safe_normalize(food_future_pos - fish.pos)
            speed = 1.3  # Fast, direct approach when hungry

            # Hunting traits
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            speed *= (1.0 + pursuit_aggression * 0.3)

            return direction.x * speed, direction.y * speed

        # IMPROVEMENT: Larger strike distance to actually catch food
        if distance < self.parameters["strike_distance"]:
            direction = self._safe_normalize(food_future_pos - fish.pos)
            # Fast strike
            strike_speed = 1.5

            # Aggression boosts strike speed
            pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
            strike_speed *= (1.0 + pursuit_aggression * 0.4)

            return direction.x * strike_speed, direction.y * strike_speed

        # Only circle when well-fed (this is the "hunting" behavior)
        # IMPROVEMENT: Much faster circling to not waste time
        if distance < FOOD_CIRCLING_APPROACH_DISTANCE:
            self.circle_angle += 0.25  # Much faster than old 0.05-0.15!

            target_x = (
                nearest_food.pos.x + math.cos(self.circle_angle) * self.parameters["circle_radius"]
            )
            target_y = (
                nearest_food.pos.y + math.sin(self.circle_angle) * self.parameters["circle_radius"]
            )
            target_vector = Vector2(target_x, target_y) - fish.pos
            direction = self._safe_normalize(target_vector)
            # Faster circling movement
            speed = self.parameters["approach_speed"]
            return direction.x * speed, direction.y * speed
        else:
            # Food is far - approach directly
            direction = self._safe_normalize(food_future_pos - fish.pos)
            return (
                direction.x * self.parameters["approach_speed"],
                direction.y * self.parameters["approach_speed"],
            )


@dataclass
class FoodMemorySeeker(BehaviorAlgorithm):
    """Remember where food was found before."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="food_memory_seeker",
            parameters={
                "memory_strength": rng.uniform(0.5, 1.0),
                "exploration_rate": rng.uniform(0.2, 0.5),
            },
        )
        self.food_memory_locations: List[Vector2] = []
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:

        # Look for current food
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            # Remember this location
            if len(self.food_memory_locations) < 5:
                self.food_memory_locations.append(Vector2(nearest_food.pos.x, nearest_food.pos.y))
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x, direction.y

        # No food visible, check memory
        if self.food_memory_locations:
            rng = getattr(self, "rng", None) or random
            if rng.random() > self.parameters["exploration_rate"]:
                target = rng.choice(self.food_memory_locations)
            else:
                # If not randomly exploring, head to the closest remembered location
                target = min(
                    self.food_memory_locations,
                    key=lambda pos: (pos - fish.pos).length(),
                )
            direction = self._safe_normalize(target - fish.pos)
            return (
                direction.x * self.parameters["memory_strength"],
                direction.y * self.parameters["memory_strength"],
            )

        return 0, 0


@dataclass
class AggressiveHunter(BehaviorAlgorithm):
    """Aggressively pursue food with high-speed interception.

    This algorithm is especially effective at catching live/moving food.
    Uses genetic hunting traits to affect behavior:
    - pursuit_aggression: How fast to pursue
    - prediction_skill: How well to predict food trajectory
    - hunting_stamina: How long to maintain high-speed pursuit
    """

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="aggressive_hunter",
            parameters={
                "pursuit_speed": rng.uniform(1.3, 1.7),
                "detection_range": rng.uniform(250, 400),
                "strike_speed": rng.uniform(1.5, 2.0),
            },
        )
        self.last_food_pos = None
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy
        is_critical = energy_ratio < 0.3

        # Get hunting traits from genome (with defaults if not present)
        pursuit_aggression = fish.genome.behavioral.pursuit_aggression.value
        prediction_skill = fish.genome.behavioral.prediction_skill.value
        hunting_stamina = fish.genome.behavioral.hunting_stamina.value

        # Predator check - but take more risks when desperate or highly aggressive
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            # Higher aggression = less cautious around predators
            flee_threshold = (
                PREDATOR_FLEE_DISTANCE_DESPERATE if is_critical
                else PREDATOR_FLEE_DISTANCE_CAUTIOUS * (1.0 - pursuit_aggression * 0.3)
            )
            if pred_dist < flee_threshold:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.4, direction.y * 1.4

        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            self.last_food_pos = Vector2(nearest_food.pos.x, nearest_food.pos.y)

            # Detection range boosted by pursuit_aggression
            effective_detection = self.parameters["detection_range"] * (1.0 + pursuit_aggression * 0.3)

            # High-speed pursuit within detection range
            if distance < effective_detection:
                # Predict food movement - skill affects prediction accuracy
                target_pos = nearest_food.pos # Default to current food position
                if hasattr(nearest_food, "vel") and nearest_food.vel.length() > 0.01:
                    is_accelerating = False
                    acceleration = 0.0
                    if hasattr(nearest_food, "food_properties"):
                        from core.constants import FOOD_SINK_ACCELERATION
                        sink_multiplier = nearest_food.food_properties.get("sink_multiplier", 1.0)
                        acceleration = FOOD_SINK_ACCELERATION * sink_multiplier
                        if acceleration > 0 and nearest_food.vel.y >= 0:
                            is_accelerating = True
                    
                    if is_accelerating:
                        target_pos, _ = predict_falling_intercept(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel, acceleration
                        )
                    else:
                        intercept_point, _ = predict_intercept_point(
                            fish.pos, fish.speed, nearest_food.pos, nearest_food.vel
                        )
                        if intercept_point:
                            # Aggressive hunters commit to prediction based on skill
                            skill_factor = 0.5 + (prediction_skill * 0.5)
                            target_pos = Vector2(
                                nearest_food.pos.x * (1 - skill_factor) + intercept_point.x * skill_factor,
                                nearest_food.pos.y * (1 - skill_factor) + intercept_point.y * skill_factor,
                            )

                direction = self._safe_normalize(target_pos - fish.pos)

                # Speed boosted by hunting traits
                pursuit_boost = 1.0 + pursuit_aggression * 0.4  # Up to 40% faster

                # Strike mode when very close
                if distance < FOOD_STRIKE_DISTANCE:
                    strike_speed = self.parameters["strike_speed"] * pursuit_boost
                    return (direction.x * strike_speed, direction.y * strike_speed)
                else:
                    # Stamina affects how long we can maintain top speed
                    # (simplified: higher stamina = faster sustained speed)
                    pursuit_speed = self.parameters["pursuit_speed"] * pursuit_boost * (0.8 + hunting_stamina * 0.2)
                    return (direction.x * pursuit_speed, direction.y * pursuit_speed)

        # No food visible - check last known location
        if self.last_food_pos and is_critical:
            direction = self._safe_normalize(self.last_food_pos - fish.pos)
            return direction.x * 0.9, direction.y * 0.9

        # Active exploration - more aggressive fish explore faster
        angle = fish.age * 0.1  # Use age for varied exploration
        explore_speed = 0.7 + pursuit_aggression * 0.3  # 0.7-1.0 based on aggression
        return math.cos(angle) * explore_speed, math.sin(angle) * explore_speed


@dataclass
class SpiralForager(BehaviorAlgorithm):
    """NEW: Spiral outward from center to systematically cover area - replaces weak algorithms."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="spiral_forager",
            parameters={
                "spiral_speed": rng.uniform(0.8, 1.2),
                "spiral_growth": rng.uniform(0.3, 0.7),
                "food_pursuit_speed": rng.uniform(1.1, 1.5),
            },
        )
        self.spiral_angle = 0
        self.spiral_radius = 10
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # Predator avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            pred_dist = (nearest_predator.pos - fish.pos).length()
            if pred_dist < PREDATOR_FLEE_DISTANCE_SAFE:
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return direction.x * 1.3, direction.y * 1.3

        # Always check for food first
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            distance = (nearest_food.pos - fish.pos).length()
            # Abandon spiral to pursue food
            if distance < FOOD_PURSUIT_RANGE_EXTENDED or is_desperate:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                speed = self.parameters["food_pursuit_speed"] * (1.3 if is_desperate else 1.0)
                return direction.x * speed, direction.y * speed

        # Spiral search pattern
        self.spiral_angle += 0.25  # Fast spiral
        self.spiral_radius += self.parameters["spiral_growth"]

        # Reset spiral if too large
        if self.spiral_radius > 150:
            self.spiral_radius = 10

        # Calculate spiral movement
        import math

        vx = math.cos(self.spiral_angle) * self.parameters["spiral_speed"]
        vy = math.sin(self.spiral_angle) * self.parameters["spiral_speed"]

        return vx, vy


@dataclass
class CooperativeForager(BehaviorAlgorithm):
    """Follow other fish to food sources - HEAVILY IMPROVED."""

    def __init__(self, rng: Optional[random.Random] = None):
        rng = rng or random
        super().__init__(
            algorithm_id="cooperative_forager",
            parameters={
                "follow_strength": rng.uniform(0.8, 1.2),  # INCREASED from 0.5-0.9
                "independence": rng.uniform(0.5, 0.8),  # INCREASED from 0.2-0.5
                "food_pursuit_speed": rng.uniform(1.1, 1.4),  # NEW
            },
        )
        self.rng = rng

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> Tuple[float, float]:
        # IMPROVEMENT: Check energy state
        energy_ratio = fish.energy / fish.max_energy
        is_desperate = energy_ratio < 0.3

        # OPTIMIZATION: Cache fish position
        fish_x = fish.pos.x
        fish_y = fish.pos.y

        # Check for predators - IMPROVED avoidance
        nearest_predator = self._find_nearest(fish, Crab)
        if nearest_predator:
            # OPTIMIZATION: Inline distance calculation
            pred_x = nearest_predator.pos.x
            pred_y = nearest_predator.pos.y
            dx = pred_x - fish_x
            dy = pred_y - fish_y
            pred_dist = (dx * dx + dy * dy) ** 0.5

            if pred_dist < PREDATOR_PROXIMITY_THRESHOLD:
                # NEW: Broadcast danger signal
                if hasattr(fish.environment, "communication_system"):
                    from core.fish_communication import SignalType

                    fish.environment.communication_system.broadcast_signal(
                        SignalType.DANGER_WARNING,
                        fish.pos,
                        target_location=nearest_predator.pos,
                        strength=1.0,
                        urgency=1.0,
                    )

                # OPTIMIZATION: Inline normalization (away from predator)
                if pred_dist > 0.001:
                    norm_x = -dx / pred_dist
                    norm_y = -dy / pred_dist
                else:
                    import math
                    import random as rand_mod
                    angle = rand_mod.random() * 6.283185  # 2*pi
                    norm_x = math.cos(angle)
                    norm_y = math.sin(angle)
                return norm_x * 1.3, norm_y * 1.3

        # Look for food directly first - EXPANDED range
        nearest_food = self._find_nearest_food(fish)
        detection_range = FOOD_PURSUIT_RANGE_DESPERATE if is_desperate else FOOD_PURSUIT_RANGE_NORMAL
        if nearest_food:
            # OPTIMIZATION: Inline distance calculation
            food_x = nearest_food.pos.x
            food_y = nearest_food.pos.y
            dx = food_x - fish_x
            dy = food_y - fish_y
            food_dist = (dx * dx + dy * dy) ** 0.5

            if food_dist < detection_range:
                # NEW: Broadcast food found signal (if social)
                if (
                    hasattr(fish.environment, "communication_system")
                    and fish.genome.behavioral.social_tendency.value > 0.5
                ):
                    from core.fish_communication import SignalType

                    fish.environment.communication_system.broadcast_signal(
                        SignalType.FOOD_FOUND,
                        fish.pos,
                        target_location=nearest_food.pos,
                        strength=fish.genome.behavioral.social_tendency.value,  # More social = stronger signal
                        urgency=0.7,
                    )

                # Food is close, go for it directly - FASTER
                # OPTIMIZATION: Inline normalization
                if food_dist > 0.001:
                    norm_x = dx / food_dist
                    norm_y = dy / food_dist
                else:
                    norm_x, norm_y = 1.0, 0.0
                speed = self.parameters["food_pursuit_speed"] * (1.3 if is_desperate else 1.0)
                return norm_x * speed, norm_y * speed

        # NEW: Listen for food signals from communication system
        best_signal_target = None
        if hasattr(fish.environment, "communication_system"):
            from core.fish_communication import SignalType

            food_signals = fish.environment.communication_system.get_nearby_signals(
                fish.pos, signal_type=SignalType.FOOD_FOUND
            )

            if food_signals:
                # Find best signal
                best_signal = max(food_signals, key=lambda s: s.strength * s.urgency)
                if best_signal.target_location:
                    best_signal_target = best_signal.target_location

        # Check if any nearby fish are near food (social learning)
        # OPTIMIZATION: Skip expensive social learning at high populations
        env = fish.environment

        best_target = None
        best_score = 0

        # Only do social learning if nearby fish count is reasonable
        if hasattr(env, "nearby_evolving_agents") and hasattr(env, "nearby_resources"):
            nearby_fish_list = env.nearby_evolving_agents(fish, SOCIAL_FOLLOW_MAX_DISTANCE)

            # OPTIMIZATION: Skip if too many fish nearby to avoid O(n*k) queries
            if len(nearby_fish_list) <= 8:
                for other_fish in nearby_fish_list:
                    other_x = other_fish.pos.x
                    other_y = other_fish.pos.y
                    dx_fish = other_x - fish_x
                    dy_fish = other_y - fish_y
                    fish_dist = (dx_fish * dx_fish + dy_fish * dy_fish) ** 0.5

                    # Check nearby food around this fish
                    nearby_food = env.nearby_resources(other_fish, SOCIAL_FOOD_PROXIMITY_THRESHOLD)
                    if nearby_food:
                        # Just use first food found
                        food = nearby_food[0]
                        food_x = food.pos.x
                        food_y = food.pos.y
                        dx_food = other_x - food_x
                        dy_food = other_y - food_y
                        food_dist = (dx_food * dx_food + dy_food * dy_food) ** 0.5

                        if food_dist < SOCIAL_FOOD_PROXIMITY_THRESHOLD:
                            score = (100 - food_dist) * (200 - fish_dist) / 100
                            if score > best_score:
                                best_score = score
                                best_target = other_fish.pos

        # NEW: Prefer signal target if it's good
        if best_signal_target:
            signal_dist = (best_signal_target - fish.pos).length()
            if signal_dist < SOCIAL_SIGNAL_DETECTION_RANGE:
                best_target = best_signal_target
                best_score = max(best_score, 50)  # Give it decent priority

        if best_target:
            direction = self._safe_normalize(best_target - fish.pos)
            # Follow with varying intensity
            intensity = min(best_score / 100, 1.0)
            return (
                direction.x * self.parameters["follow_strength"] * intensity,
                direction.y * self.parameters["follow_strength"] * intensity,
            )

        # No one to follow, explore independently
        rng = getattr(self, "rng", None) or random
        if rng.random() < self.parameters["independence"]:
            return rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)

        return 0, 0
