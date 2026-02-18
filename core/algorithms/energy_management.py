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

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.entities import Fish

from core.algorithms.base import BehaviorAlgorithm, Vector2


@dataclass
class EnergyConserver(BehaviorAlgorithm):
    """Minimize movement to conserve energy."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "EnergyConserver.__init__")
        super().__init__(
            algorithm_id="energy_conserver",
            parameters={
                "activity_threshold": _rng.uniform(0.4, 0.7),
                "rest_speed": _rng.uniform(0.1, 0.3),
                "exploration_rate": _rng.uniform(
                    0.0, 0.4
                ),  # 0 = no exploration, 0.4 = moderate wandering
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        # IMPROVEMENT: Use new critical energy methods
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        energy_ratio = fish.get_energy_ratio()

        # Check for immediate threats
        nearest_predator = self._find_nearest(fish, Crab)
        predator_distance = (nearest_predator.pos - fish.pos).length() if nearest_predator else 999

        # IMPROVEMENT: When critical, must act even if conserving
        if is_critical:
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                food_distance = (nearest_food.pos - fish.pos).length()
                # Must pursue food aggressively when critical
                if food_distance < 200 or predator_distance > 60:
                    direction = self._safe_normalize(nearest_food.pos - fish.pos)
                    return direction.x * 1.1, direction.y * 1.1

        # Flee if predator is very close
        if nearest_predator is not None and predator_distance < 80:
            # Must flee even if conserving energy
            direction = self._safe_normalize(fish.pos - nearest_predator.pos)
            # IMPROVEMENT: Smarter flee speed based on energy
            flee_speed = 0.9 if is_critical else (1.0 + energy_ratio * 0.4)
            return direction.x * flee_speed, direction.y * flee_speed

        # Only pursue very close food when in conservation mode
        nearest_food = self._find_nearest_food(fish)
        if nearest_food:
            food_distance = (nearest_food.pos - fish.pos).length()
            # IMPROVEMENT: Expand pursuit range when low energy
            max_pursuit_distance = 80 if is_low else 40

            if food_distance < max_pursuit_distance or energy_ratio < 0.25:
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                # IMPROVEMENT: Faster when food is close to save energy overall
                speed_mult = self.parameters["rest_speed"] * (
                    1.0 + (1.0 - min(food_distance / 50, 1.0)) * 0.5
                )
                return direction.x * speed_mult, direction.y * speed_mult

        # Rest mode - gentle exploration based on exploration_rate parameter
        exploration_rate = self.parameters["exploration_rate"]
        if exploration_rate > 0:
            # Gentle wandering to explore for food when idle
            # Use fish_id as stable phase offset and environment RNG for time variation
            rng = fish.environment.rng
            # Generate a pseudo-time from the RNG seeded by fish_id for consistent per-fish behavior
            phase = fish.fish_id * 0.1  # Stable phase offset per fish
            wander_state = rng.random() * 6.283185307  # Random angle
            vx = math.cos(wander_state + phase) * exploration_rate
            vy = math.sin(wander_state * 0.7 + phase) * exploration_rate * 0.5
            return vx, vy

        return 0, 0


@dataclass
class BurstSwimmer(BehaviorAlgorithm):
    """Alternate between bursts of activity and rest."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "BurstSwimmer.__init__")
        super().__init__(
            algorithm_id="burst_swimmer",
            parameters={
                "burst_duration": _rng.uniform(30, 90),
                "rest_duration": _rng.uniform(60, 120),
                "burst_speed": _rng.uniform(1.2, 1.6),
            },
            rng=_rng,
        )
        self.cycle_timer = 0
        self.is_bursting = True

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        energy_ratio = fish.energy / fish.max_energy

        # Check environment
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest_food(fish)

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
            if nearest_predator is not None and predator_nearby:
                # Burst away from predator
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                return (
                    direction.x * self.parameters["burst_speed"],
                    direction.y * self.parameters["burst_speed"],
                )
            elif nearest_food is not None and food_nearby:
                # Burst toward food
                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                return (
                    direction.x * self.parameters["burst_speed"],
                    direction.y * self.parameters["burst_speed"],
                )
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

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "OpportunisticRester.__init__")
        super().__init__(
            algorithm_id="opportunistic_rester",
            parameters={
                "safe_radius": _rng.uniform(100, 200),
                "active_speed": _rng.uniform(0.5, 0.9),
                "idle_wander_speed": _rng.uniform(
                    0.0, 0.3
                ),  # 0 = stay still, 0.3 = gentle wandering
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab, Food

        # Check for nearby stimuli
        foods = fish.environment.get_agents_of_type(Food)
        predators = fish.environment.get_agents_of_type(Crab)

        has_nearby_food = any(
            (f.pos - fish.pos).length() < self.parameters["safe_radius"] for f in foods
        )
        has_nearby_threat = any(
            (p.pos - fish.pos).length() < self.parameters["safe_radius"] for p in predators
        )

        if has_nearby_food or has_nearby_threat:
            # Move in fish's current direction at active speed
            vel_len_sq = fish.vel.length_squared()
            if vel_len_sq > 0.01:
                vel_len = math.sqrt(vel_len_sq)
                return (
                    fish.vel.x / vel_len * self.parameters["active_speed"],
                    fish.vel.y / vel_len * self.parameters["active_speed"],
                )
            # If stationary, pick a random direction (use environment RNG for determinism)
            rng = fish.environment.rng
            angle = rng.random() * 6.283185307
            return self.parameters["active_speed"] * math.cos(angle), self.parameters[
                "active_speed"
            ] * math.sin(angle)

        # Idle wandering when no stimuli detected
        idle_speed = self.parameters["idle_wander_speed"]
        if idle_speed > 0:
            # Gentle random wandering to explore environment
            # Use fish_id as stable phase offset and environment RNG for variation
            rng = fish.environment.rng
            phase = fish.fish_id * 0.05  # Stable phase offset per fish
            wander_state = rng.random() * 6.283185307  # Random angle
            vx = math.cos(wander_state + phase) * idle_speed
            vy = math.sin(wander_state * 0.6 + phase) * idle_speed * 0.4
            return vx, vy

        return 0, 0


@dataclass
class EnergyBalancer(BehaviorAlgorithm):
    """Balance energy expenditure with reserves."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "EnergyBalancer.__init__")
        super().__init__(
            algorithm_id="energy_balancer",
            parameters={
                "min_energy_ratio": _rng.uniform(0.3, 0.5),
                "max_energy_ratio": _rng.uniform(0.7, 0.9),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        # IMPROVEMENT: Use new energy methods and be more conservative
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        fish.is_safe_energy()
        energy_ratio = fish.get_energy_ratio()

        # IMPROVEMENT: More aggressive food seeking when energy is low
        nearest_food = self._find_nearest_food(fish)

        # Critical energy: must seek food aggressively
        if is_critical and nearest_food:
            direction = self._safe_normalize(nearest_food.pos - fish.pos)
            return direction.x * 1.4, direction.y * 1.4

        # Low energy: prioritize food but conserve energy
        if is_low:
            if nearest_food:
                distance = (nearest_food.pos - fish.pos).length()
                # Only pursue if reasonably close
                if distance < 150:
                    direction = self._safe_normalize(nearest_food.pos - fish.pos)
                    return direction.x * 0.9, direction.y * 0.9
            # Otherwise minimize activity - continue current direction slowly
            vel_len_sq = fish.vel.length_squared()
            if vel_len_sq > 0.01:
                vel_len = math.sqrt(vel_len_sq)
                return fish.vel.x / vel_len * 0.1, fish.vel.y / vel_len * 0.1
            # If stationary, pick a random direction to explore (use environment RNG)
            rng = fish.environment.rng
            angle = rng.random() * 6.283185307
            return 0.1 * math.cos(angle), 0.1 * math.sin(angle)

        # Safe energy: normal activity based on ratio
        if energy_ratio < self.parameters["min_energy_ratio"]:
            activity = 0.3  # Increased from 0.2 to be more active when needed
        elif energy_ratio > self.parameters["max_energy_ratio"]:
            activity = 1.2  # Slightly more active when energy is high
        else:
            # Linear interpolation
            activity = 0.3 + 0.9 * (
                (energy_ratio - self.parameters["min_energy_ratio"])
                / (self.parameters["max_energy_ratio"] - self.parameters["min_energy_ratio"])
            )

        # Move in fish's current direction at calculated activity level
        vel_len_sq = fish.vel.length_squared()
        if vel_len_sq > 0.01:
            vel_len = math.sqrt(vel_len_sq)
            return fish.vel.x / vel_len * activity, fish.vel.y / vel_len * activity
        # If stationary, pick random direction (use environment RNG for determinism)
        rng = fish.environment.rng
        angle = rng.random() * 6.283185307
        return activity * math.cos(angle), activity * math.sin(angle)


@dataclass
class SustainableCruiser(BehaviorAlgorithm):
    """Maintain steady, sustainable pace."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "SustainableCruiser.__init__")
        super().__init__(
            algorithm_id="sustainable_cruiser",
            parameters={
                "cruise_speed": _rng.uniform(0.4, 0.7),
                "consistency": _rng.uniform(0.7, 1.0),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        # Just maintain steady pace in current direction
        cruise = self.parameters["cruise_speed"] * self.parameters["consistency"]
        vel_len_sq = fish.vel.length_squared()
        if vel_len_sq > 0.01:
            vel_len = math.sqrt(vel_len_sq)
            return fish.vel.x / vel_len * cruise, fish.vel.y / vel_len * cruise
        # If stationary, pick random direction (use environment RNG for determinism)
        rng = fish.environment.rng
        angle = rng.random() * 6.283185307
        return cruise * math.cos(angle), cruise * math.sin(angle)


@dataclass
class StarvationPreventer(BehaviorAlgorithm):
    """Prioritize food when energy gets low."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "StarvationPreventer.__init__")
        super().__init__(
            algorithm_id="starvation_preventer",
            parameters={
                "critical_threshold": _rng.uniform(0.2, 0.4),
                "urgency_multiplier": _rng.uniform(1.3, 1.8),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab

        # IMPROVEMENT: Use new critical energy methods
        is_critical = fish.is_critical_energy()
        is_low = fish.is_low_energy()
        energy_ratio = fish.get_energy_ratio()

        # IMPROVEMENT: Multi-level urgency system
        if is_critical:
            # CRITICAL: Maximum urgency, ignore predators unless extremely close
            nearest_food = self._find_nearest_food(fish)

            # Check for remembered food locations if no visible food
            if not nearest_food and hasattr(fish, "get_remembered_food_locations"):
                remembered = fish.get_remembered_food_locations()
                if remembered:
                    # Go to closest remembered location
                    target = min(remembered, key=lambda pos: (pos - fish.pos).length())
                    direction = self._safe_normalize(target - fish.pos)
                    return direction.x * 1.3, direction.y * 1.3

            if nearest_food:
                # Only flee predator if extremely close
                nearest_predator = self._find_nearest(fish, Crab)
                if nearest_predator and (nearest_predator.pos - fish.pos).length() < 40:
                    # Quick evasion but keep trying for food
                    avoid_dir = self._safe_normalize(fish.pos - nearest_predator.pos)
                    food_dir = self._safe_normalize(nearest_food.pos - fish.pos)
                    # Blend: 60% avoid, 40% toward food
                    direction = self._safe_normalize(avoid_dir * 0.6 + food_dir * 0.4)
                    return direction.x * 1.5, direction.y * 1.5
                else:
                    direction = self._safe_normalize(nearest_food.pos - fish.pos)
                    return (
                        direction.x * self.parameters["urgency_multiplier"] * 1.2,
                        direction.y * self.parameters["urgency_multiplier"] * 1.2,
                    )

        elif is_low or energy_ratio < self.parameters["critical_threshold"]:
            # LOW: High urgency, some predator avoidance
            nearest_food = self._find_nearest_food(fish)
            if nearest_food:
                nearest_predator = self._find_nearest(fish, Crab)
                # Flee if predator is close
                if nearest_predator and (nearest_predator.pos - fish.pos).length() < 70:
                    direction = self._safe_normalize(fish.pos - nearest_predator.pos)
                    return direction.x * 1.3, direction.y * 1.3
                else:
                    direction = self._safe_normalize(nearest_food.pos - fish.pos)
                    return (
                        direction.x * self.parameters["urgency_multiplier"],
                        direction.y * self.parameters["urgency_multiplier"],
                    )

        return 0.0, 0.0


@dataclass
class MetabolicOptimizer(BehaviorAlgorithm):
    """Adjust activity based on metabolic efficiency."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "MetabolicOptimizer.__init__")
        super().__init__(
            algorithm_id="metabolic_optimizer",
            parameters={
                "efficiency_threshold": _rng.uniform(0.5, 0.8),
                "low_efficiency_speed": _rng.uniform(0.2, 0.4),
                "high_efficiency_speed": _rng.uniform(0.7, 1.1),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        # Use genome metabolism as efficiency indicator
        efficiency = 1.0 / fish.genome.metabolism_rate if fish.genome.metabolism_rate > 0 else 1.0

        if efficiency > self.parameters["efficiency_threshold"]:
            speed = self.parameters["high_efficiency_speed"]
        else:
            speed = self.parameters["low_efficiency_speed"]

        # Move in fish's current direction at calculated speed
        vel_len_sq = fish.vel.length_squared()
        if vel_len_sq > 0.01:
            vel_len = math.sqrt(vel_len_sq)
            return fish.vel.x / vel_len * speed, fish.vel.y / vel_len * speed
        # If stationary, pick random direction (use environment RNG for determinism)
        rng = fish.environment.rng
        angle = rng.random() * 6.283185307
        return speed * math.cos(angle), speed * math.sin(angle)


@dataclass
class AdaptivePacer(BehaviorAlgorithm):
    """Adapt speed based on current energy and environment."""

    def __init__(self, rng: Optional[random.Random] = None):
        from core.util.rng import require_rng_param

        _rng = require_rng_param(rng, "AdaptivePacer.__init__")
        super().__init__(
            algorithm_id="adaptive_pacer",
            parameters={
                "base_speed": _rng.uniform(0.5, 0.8),
                "energy_influence": _rng.uniform(0.3, 0.7),
            },
            rng=_rng,
        )

    @classmethod
    def random_instance(cls, rng: Optional[random.Random] = None):
        return cls(rng=rng)

    def execute(self, fish: "Fish") -> tuple[float, float]:
        from core.entities import Crab, Fish

        energy_ratio = fish.energy / fish.max_energy

        # Base speed influenced by energy
        base_speed = self.parameters["base_speed"] * (
            1 + (energy_ratio - 0.5) * self.parameters["energy_influence"]
        )

        # Check environment for context
        nearest_predator = self._find_nearest(fish, Crab)
        nearest_food = self._find_nearest_food(fish)

        vx, vy = 0.0, 0.0

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
                direction = self._safe_normalize(fish.pos - nearest_predator.pos)
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

                direction = self._safe_normalize(nearest_food.pos - fish.pos)
                vx = direction.x * pursuit_speed
                vy = direction.y * pursuit_speed

        # Social pacing - match nearby fish speeds
        if vx == 0 and vy == 0:
            allies = [
                f
                for f in fish.environment.get_agents_of_type(Fish)
                if f != fish and (f.pos - fish.pos).length() < 100
            ]
            if allies:
                avg_vel = sum((f.vel for f in allies), Vector2()) / len(allies)
                if avg_vel.length() > 0:
                    avg_vel_normalized = self._safe_normalize(avg_vel)
                    # Match their pace but adjusted by our energy
                    social_pace = base_speed * 0.8
                    vx = avg_vel_normalized.x * social_pace
                    vy = avg_vel_normalized.y * social_pace

        # Default gentle cruising if nothing else to do
        if vx == 0 and vy == 0:
            # Cruise in a gentle pattern using environment RNG for determinism
            rng = fish.environment.rng
            wander_angle = rng.random() * 6.283185307
            vx = math.cos(wander_angle) * base_speed * 0.6
            vy = math.sin(wander_angle * 0.5) * base_speed * 0.3

        return vx, vy
